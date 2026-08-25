"""Application entrypoint and security middleware stack.

Middleware order matters and is deliberate:
  1. HTTPS redirect   — a plain-HTTP request is answered before anything reads its body.
  2. Security headers  — wraps everything below, including error responses.
  3. Body size limit   — caps the request before a route buffers it.
  4. CORS              — outermost of the app-level checks so preflights are answered.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import admin, checkout, oauth, questionnaire, webhook
from .config import get_config
from .followup import start_followup_scheduler
from .security import (
    BodySizeLimitMiddleware,
    HTTPSRedirectMiddleware,
    SecurityHeadersMiddleware,
    build_csp,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

cfg = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_followup_scheduler())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Instagram Analytics SaaS",
    lifespan=lifespan,
    # Item 17 — the schema enumerates every route, parameter and error shape. There is
    # no reason to publish it from production.
    docs_url=None if cfg.IS_PRODUCTION else "/docs",
    redoc_url=None,
    openapi_url=None if cfg.IS_PRODUCTION else "/openapi.json",
)

# --- Item 18: security headers -------------------------------------------------
# This service returns JSON only, so the CSP can deny every resource type. The
# connect-src allowance covers the browser reading these responses cross-origin.
app.add_middleware(
    SecurityHeadersMiddleware,
    csp=build_csp(
        script_src="'none'",
        style_src="'none'",
        img_src="'none'",
        font_src="'none'",
        connect_src="'self'",
    ),
    hsts_max_age=cfg.HSTS_MAX_AGE,
    trust_proxy=cfg.TRUST_PROXY,
)

# --- Item 16: bound request bodies ---------------------------------------------
app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=cfg.MAX_BODY_BYTES)

# --- Item 19: force HTTPS ------------------------------------------------------
app.add_middleware(
    HTTPSRedirectMiddleware,
    enabled=cfg.FORCE_HTTPS,
    trust_proxy=cfg.TRUST_PROXY,
)

# --- Item 18/19: CORS allowlist ------------------------------------------------
# A wildcard origin would let any page on the internet call this API with a
# visitor's browser. Origins come from ALLOWED_ORIGINS, and Config refuses a
# wildcard when ENVIRONMENT=production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cfg.ALLOWED_ORIGINS),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Session-Token"],
    allow_credentials=False,  # no cookies cross-site; auth travels in X-Session-Token
    max_age=600,
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Item 17 — never let a stack trace or exception string reach the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Erro interno."}, status_code=500)


app.include_router(oauth.router)
app.include_router(questionnaire.router)
app.include_router(checkout.router)
app.include_router(webhook.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

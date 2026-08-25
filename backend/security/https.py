"""Item 19 — force HTTPS."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.types import ASGIApp

# Paths that must stay reachable over plain HTTP so platform health probes and
# ACME challenges do not break when they hit the container directly.
DEFAULT_EXEMPT_PATHS = ("/health", "/healthz", "/.well-known/acme-challenge")


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect plain-HTTP requests to HTTPS.

    Unlike Starlette's built-in version this reads ``X-Forwarded-Proto``, which is what
    actually arrives when the app runs behind Railway/Nginx/Cloudflare, and it can be
    disabled with a single flag so local development over http://127.0.0.1 still works.

    Only safe methods are redirected. A POST answered with a redirect would either be
    replayed without its body or silently downgraded, so unsafe methods that arrive
    over HTTP are rejected outright — the client must retry against the https origin.
    """

    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool = True,
        trust_proxy: bool = True,
        exempt_paths: tuple[str, ...] = DEFAULT_EXEMPT_PATHS,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.trust_proxy = trust_proxy
        self.exempt_paths = exempt_paths

    def _is_https(self, request: Request) -> bool:
        if request.url.scheme == "https":
            return True
        if self.trust_proxy:
            proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
            return proto == "https"
        return False

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or self._is_https(request):
            return await call_next(request)

        if request.url.path.startswith(self.exempt_paths):
            return await call_next(request)

        if request.method not in self.SAFE_METHODS:
            from starlette.responses import JSONResponse

            return JSONResponse(
                {"detail": "HTTPS required"},
                status_code=400,
                headers={"Connection": "close"},
            )

        return RedirectResponse(
            str(request.url.replace(scheme="https")),
            status_code=308,  # preserves method and body
        )

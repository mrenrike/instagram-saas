from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from . import oauth, questionnaire, checkout, webhook, admin
from .followup import start_followup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(start_followup_scheduler())
    yield
    task.cancel()


app = FastAPI(title="Instagram Analytics SaaS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to Hostinger domain in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(oauth.router)
app.include_router(questionnaire.router)
app.include_router(checkout.router)
app.include_router(webhook.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

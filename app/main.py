import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.processing.async_webhook import AsyncWebhookProcessor
from app.seatalk.auth import SeaTalkAuthManager
from app.seatalk.client import SeaTalkClient
from app.seatalk.event_types import EVENT_VERIFICATION
from app.seatalk.events import SeaTalkEventRouter

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("seatalk_bot")

auth_manager = SeaTalkAuthManager()
seatalk_client = SeaTalkClient(auth_manager)
event_router = SeaTalkEventRouter(seatalk_client)
webhook_processor = AsyncWebhookProcessor(
    event_router=event_router,
    worker_count=settings.webhook_worker_count,
    max_queue_size=settings.webhook_queue_maxsize,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await webhook_processor.start()
    try:
        yield
    finally:
        await webhook_processor.stop()


app = FastAPI(title="SeaTalk LangGraph Bot", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/seatalk/callback")
async def seatalk_callback(request: Request):
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid json"})

    event_type = payload.get("event_type")
    challenge = payload.get("event", {}).get("seatalk_challenge")

    if event_type == EVENT_VERIFICATION and challenge:
        return JSONResponse(status_code=200, content={"seatalk_challenge": challenge})

    queued = webhook_processor.enqueue(payload)
    if not queued:
        logger.error("Callback accepted but dropped from queue. event_id=%s", payload.get("event_id"))

    return JSONResponse(status_code=200, content={"ok": True, "queued": queued})

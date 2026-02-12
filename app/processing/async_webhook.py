from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.seatalk.events import SeaTalkEventRouter

logger = logging.getLogger("seatalk_bot")


class AsyncWebhookProcessor:
    def __init__(
        self,
        event_router: SeaTalkEventRouter,
        worker_count: int = 2,
        max_queue_size: int = 1000,
    ) -> None:
        self.event_router = event_router
        self.worker_count = worker_count
        self.queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=max_queue_size)
        self.workers: list[asyncio.Task[None]] = []
        self.running = False

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        for idx in range(self.worker_count):
            task = asyncio.create_task(self._worker(idx))
            self.workers.append(task)

    async def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        for _ in self.workers:
            await self.queue.put(None)
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    def enqueue(self, payload: dict[str, Any]) -> bool:
        try:
            self.queue.put_nowait(payload)
            return True
        except asyncio.QueueFull:
            logger.error("Webhook queue is full. Dropping event_id=%s", payload.get("event_id"))
            return False

    async def _worker(self, worker_id: int) -> None:
        while True:
            payload = await self.queue.get()
            try:
                if payload is None:
                    return
                await asyncio.to_thread(self.event_router.handle_event, payload)
            except Exception:
                logger.exception("Worker %s failed processing callback", worker_id)
            finally:
                self.queue.task_done()

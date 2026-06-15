"""Async pub/sub service for real-time event broadcasting to WebSocket clients."""

import asyncio
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """In-memory pub/sub. Each WebSocket client subscribes via an asyncio.Queue."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        message = {
            "type": event_type,
            "data": data,
            "ts": datetime.utcnow().isoformat() + "Z",
        }
        async with self._lock:
            for q in self._subscribers:
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


_broadcaster: EventBroadcaster | None = None


def set_broadcaster(b: EventBroadcaster) -> None:
    global _broadcaster
    _broadcaster = b


def get_broadcaster() -> EventBroadcaster | None:
    return _broadcaster

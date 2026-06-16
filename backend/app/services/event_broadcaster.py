"""WebSocket event broadcaster with channel-based pub/sub."""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """Channel-based pub/sub for WebSocket clients."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, channel: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscriptions[channel].add(queue)
        return queue

    def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        self._subscriptions[channel].discard(queue)

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        if channel not in self._subscriptions:
            return
        dead: list[asyncio.Queue] = []
        for queue in self._subscriptions[channel]:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self._subscriptions[channel].discard(q)

    async def broadcast_event(self, event_data: dict) -> None:
        await self.broadcast("events", {
            "type": "event",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def broadcast_signal(self, signal_data: dict) -> None:
        await self.broadcast("signals", {
            "type": "signal",
            "data": signal_data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def broadcast_market_price(self, price_data: dict) -> None:
        await self.broadcast("market_prices", {
            "type": "market_price",
            "data": price_data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    @property
    def subscriber_count(self) -> int:
        return sum(len(qs) for qs in self._subscriptions.values())


_broadcaster: EventBroadcaster | None = None


def set_broadcaster(b: EventBroadcaster) -> None:
    global _broadcaster
    _broadcaster = b


def get_broadcaster() -> EventBroadcaster:
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = EventBroadcaster()
    return _broadcaster

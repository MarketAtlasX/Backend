"""WebSocket routes for real-time event streaming to the frontend."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_broadcaster import get_broadcaster

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    broadcaster = get_broadcaster()
    subscriptions: dict[str, asyncio.Queue] = {}
    tasks: list[asyncio.Task] = []

    async def forward(channel: str, queue: asyncio.Queue) -> None:
        try:
            while True:
                message = await queue.get()
                try:
                    await websocket.send_json(message)
                except Exception:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe(channel, queue)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "subscribe":
                channel = data.get("channel", "")
                if channel and channel not in subscriptions:
                    queue = broadcaster.subscribe(channel)
                    subscriptions[channel] = queue
                    task = asyncio.create_task(forward(channel, queue))
                    tasks.append(task)
                    await websocket.send_json({"type": "subscribed", "channel": channel})

            elif msg_type == "unsubscribe":
                channel = data.get("channel", "")
                if channel in subscriptions:
                    broadcaster.unsubscribe(channel, subscriptions[channel])
                    del subscriptions[channel]
                    await websocket.send_json({"type": "unsubscribed", "channel": channel})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("WebSocket error")
    finally:
        for task in tasks:
            task.cancel()
        for channel, queue in subscriptions.items():
            broadcaster.unsubscribe(channel, queue)

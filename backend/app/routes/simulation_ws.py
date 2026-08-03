"""Backend-proxied simulation WebSocket.

Single entry point for the frontend. Validates the JWT, then streams
simulation progress/complete/failure events from the backend to the client.
The frontend never talks to the simulator directly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.auth_service import decode_access_token
from app.services.event_broadcaster import get_broadcaster

logger = logging.getLogger(__name__)

ws_router = APIRouter()


async def _authenticate(websocket: WebSocket) -> Optional[int]:
    token = websocket.query_params.get("token", "")
    if token:
        return decode_access_token(token)
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return decode_access_token(auth_header[7:])
    return None


@ws_router.websocket("/ws/simulation")
async def simulation_ws(websocket: WebSocket) -> None:
    user_id = await _authenticate(websocket)
    if user_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    broadcaster = get_broadcaster()
    channel = f"simulation:{user_id}"
    queue: asyncio.Queue = broadcaster.subscribe(channel)
    task = asyncio.create_task(_forward(queue, websocket))

    try:
        await websocket.send_json({"type": "connected", "channel": channel})
        while True:
            await websocket.receive_text()
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("Simulation WS client disconnected: user %s", user_id)
    except Exception:
        logger.exception("Simulation WS error for user %s", user_id)
    finally:
        task.cancel()
        broadcaster.unsubscribe(channel, queue)


async def _forward(queue: asyncio.Queue, websocket: WebSocket) -> None:
    try:
        while True:
            message = await queue.get()
            try:
                await websocket.send_json(message)
            except Exception:
                break
    except asyncio.CancelledError:
        pass


async def notify_simulation(user_id: int, message: dict) -> None:
    """Broadcast a simulation event to a user's proxied WS channel."""
    await get_broadcaster().broadcast(f"simulation:{user_id}", message)

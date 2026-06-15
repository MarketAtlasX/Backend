"""WebSocket routes for real-time event streaming to the frontend."""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_broadcaster import EventBroadcaster

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket) -> None:
    broadcaster: EventBroadcaster | None = getattr(websocket.app.state, "broadcaster", None)
    if broadcaster is None:
        await websocket.close(code=1011, reason="Broadcaster not available")
        return

    await websocket.accept()
    q = await broadcaster.subscribe()

    try:
        while True:
            message = await asyncio.wait_for(q.get(), timeout=30)
            try:
                await websocket.send_json(message)
            except Exception:
                break
    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        await broadcaster.unsubscribe(q)
        try:
            await websocket.close()
        except Exception:
            pass

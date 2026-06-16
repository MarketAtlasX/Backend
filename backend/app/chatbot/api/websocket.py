import json
import uuid
import logging
from fastapi import WebSocket, WebSocketDisconnect

from ..workflow.graph import run_chat
from ..memory.short_term import short_term_memory

logger = logging.getLogger(__name__)

connected_clients: dict[str, WebSocket] = {}


async def handle_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    connected_clients[client_id] = websocket

    try:
        await websocket.send_json({"type": "connected", "client_id": client_id})

        while True:
            data = await websocket.receive_json()
            query = data.get("query", "")
            conversation_id = data.get("conversation_id", str(uuid.uuid4()))
            stream = data.get("stream", False)

            if not query:
                await websocket.send_json({"type": "error", "message": "Empty query"})
                continue

            if stream:
                await websocket.send_json({
                    "type": "stream_start",
                    "conversation_id": conversation_id,
                })
                response = await run_chat(query=query, conversation_id=conversation_id)
                await websocket.send_json({
                    "type": "metadata",
                    "conversation_id": conversation_id,
                    "intent": response.intent.value,
                    "agents_used": response.agents_used,
                    "confidence": response.confidence,
                })
                for chunk in response.response.split(". "):
                    await websocket.send_json({"type": "chunk", "text": chunk + ". "})
                await websocket.send_json({"type": "stream_end"})
            else:
                response = await run_chat(query=query, conversation_id=conversation_id)
                await websocket.send_json({
                    "type": "response",
                    "conversation_id": conversation_id,
                    "response": response.response,
                    "intent": response.intent.value,
                    "agents_used": response.agents_used,
                    "confidence": response.confidence,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        connected_clients.pop(client_id, None)

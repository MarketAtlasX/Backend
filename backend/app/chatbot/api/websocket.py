import asyncio
import logging
import random
import uuid

from fastapi import WebSocket, WebSocketDisconnect

from ..workflow.graph import run_chat

logger = logging.getLogger(__name__)

connected_clients: dict[str, WebSocket] = {}
channel_subscriptions: dict[str, set[str]] = {}


async def _send_signal_updates(client_id: str, websocket: WebSocket):
    while True:
        await asyncio.sleep(10)
        if client_id not in connected_clients:
            break
        if "signals" not in channel_subscriptions or client_id not in channel_subscriptions["signals"]:
            continue
        try:
            await websocket.send_json({
                "type": "signal",
                "channel": "signals",
                "data": {
                    "snapshot": {
                        "symbol": random.choice(["XLE", "XLK", "ITA", "GLD", "SPY"]),
                        "momentum": round(random.uniform(-0.08, 0.12), 4),
                        "volatility": round(random.uniform(0.01, 0.06), 4),
                        "volume_status": random.choice(["surge", "normal", "thin"]),
                    },
                    "impact": {
                        "composite_risk": round(random.uniform(0.1, 0.9), 4),
                        "local_severity": round(random.uniform(0.1, 0.8), 4),
                        "entity_count": random.randint(3, 10),
                        "relations": [
                            {"source": "Russia", "target": "Oil", "label": "sanction"},
                            {"source": "China", "target": "Tech", "label": "restriction"},
                        ],
                    },
                    "recommendation": {
                        "action": random.choice(["BUY", "HOLD", "SELL"]),
                        "reason": ("Real-time geopolitical risk assessment combined with market momentum analysis."),
                        "confidence": round(random.uniform(0.5, 0.95), 4),
                    },
                },
                "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            })
        except Exception:
            break


async def handle_websocket(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())
    connected_clients[client_id] = websocket

    signal_task: asyncio.Task | None = None

    try:
        await websocket.send_json({"type": "connected", "client_id": client_id})

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "subscribe":
                channel = data.get("channel", "")
                if channel:
                    if channel not in channel_subscriptions:
                        channel_subscriptions[channel] = set()
                    channel_subscriptions[channel].add(client_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": channel,
                    })
                    if channel == "signals" and signal_task is None:
                        signal_task = asyncio.create_task(_send_signal_updates(client_id, websocket))

            elif msg_type == "unsubscribe":
                channel = data.get("channel", "")
                if channel in channel_subscriptions:
                    channel_subscriptions[channel].discard(client_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
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
        for ch in channel_subscriptions.values():
            ch.discard(client_id)
        if signal_task:
            signal_task.cancel()

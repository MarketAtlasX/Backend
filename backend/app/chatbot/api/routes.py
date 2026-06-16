import json
import uuid
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import ChatRequest
from ..workflow.graph import run_chat
from ..memory.short_term import short_term_memory
from ..rag.vector_store import search_knowledge
from ..knowledge.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/api/v1/chat")


@chat_router.post("")
async def chat(request: ChatRequest):
    try:
        response = await run_chat(
            query=request.query,
            conversation_id=request.conversation_id,
        )
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.post("/stream")
async def chat_stream(request: ChatRequest):
    response = await run_chat(
        query=request.query,
        conversation_id=request.conversation_id,
    )

    async def generate():
        yield json.dumps({
            "conversation_id": response.conversation_id,
            "intent": response.intent.value,
            "agents_used": response.agents_used,
            "confidence": response.confidence,
        }) + "\n"
        for chunk in response.response.split(". "):
            yield json.dumps({"chunk": chunk + ". "}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@chat_router.get("/history")
async def history(limit: int = 20):
    try:
        from ..memory.short_term import short_term_memory
        return {"message": "History available via conversation IDs sent in chat responses"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/memory/{conversation_id}")
async def get_memory(conversation_id: str):
    history = short_term_memory.get_history(conversation_id)
    return {"conversation_id": conversation_id, "turns": len(history), "history": history}


@chat_router.get("/knowledge/search")
async def knowledge_search(q: str, limit: int = 5):
    results = search_knowledge(q, limit)
    return {"query": q, "results": results}


@chat_router.get("/graph/{entity}")
async def graph_query(entity: str):
    client = Neo4jClient()
    if not client.available:
        return {"entity": entity, "error": "Neo4j not available", "relations": []}
    relations = client.get_relations(entity)
    return {"entity": entity, "relations": relations}


@chat_router.get("/health")
async def health():
    return {"status": "ok", "service": "MarketAtlas Chat"}

import logging
from typing import Any

from .vector_store import search_knowledge, vector_store

logger = logging.getLogger(__name__)

_kb_seeded = False


def retrieve_context(query: str, limit: int = 5) -> str:
    results = search_knowledge(query, limit)
    if not results:
        return ""

    lines = ["Relevant context from knowledge base:"]
    for r in results:
        title = r.get("title", "Untitled")
        content = r.get("content", "")
        source = r.get("source", "unknown")
        score = r.get("score", 0)
        lines.append(f"- [{source}] {title} (relevance: {score:.2f})")
        if content:
            lines.append(f"  {content[:300]}")
    return "\n".join(lines)


async def seed_knowledge_base():
    global _kb_seeded
    if _kb_seeded:
        return True
    if not vector_store.available:
        logger.warning("Qdrant not available — skipping knowledge seed")
        return False

    try:
        from app.database import AsyncSessionLocal
        from app.models.raw_event import RawEvent
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            stmt = select(RawEvent).order_by(RawEvent.fetched_at.desc()).limit(100)
            result = await session.execute(stmt)
            events = list(result.scalars().all())

        if events:
            docs = []
            for i, e in enumerate(events):
                docs.append({
                    "id": i + 1,
                    "text": f"{e.title}. {e.description or ''} {e.content or ''}",
                    "title": e.title[:200],
                    "source": e.source or "MarketAtlas",
                    "content": (e.description or e.content or "")[:500],
                })
            vector_store.upsert(docs)
            logger.info(f"Seeded knowledge base with {len(docs)} real events from DB")
        else:
            _seed_sample_docs()

        _kb_seeded = True
        return True
    except Exception as e:
        logger.warning(f"Could not seed from DB ({e}), using sample docs")
        _seed_sample_docs()
        _kb_seeded = True
        return True


def _seed_sample_docs():
    sample_docs = [
        {"id": 1, "text": "Oil prices surged 3.1% today amid rising tensions in the Strait of Hormuz. Iranian naval activity detected near key shipping lanes.", "title": "Oil Surge Report", "source": "Reuters", "content": "Oil prices surged 3.1% today amid rising tensions in the Strait of Hormuz."},
        {"id": 2, "text": "Russia reduced gas exports to Europe by 30% leading to energy crisis. European manufacturing PMI dropped 5 points.", "title": "Russia Gas Crisis", "source": "Bloomberg", "content": "Russia reduced gas exports to Europe by 30%."},
        {"id": 3, "text": "Taiwan blockade scenario analysis: Defense stocks like Lockheed Martin and Northrop Grumman benefit significantly. Gold and Energy ETFs also gain.", "title": "Taiwan Blockade Analysis", "source": "MarketAtlas Research", "content": "Taiwan blockade beneficiaries include defense stocks, gold, and energy ETFs."},
        {"id": 4, "text": "New sanctions imposed on Iran targeting oil exports. Global oil supply concerns rise. Shipping costs increase 15%.", "title": "Iran Sanctions Update", "source": "FT", "content": "New sanctions on Iran targeting oil exports."},
        {"id": 5, "text": "US Federal Reserve holds interest rates steady at 5.5%. Inflation remains elevated at 3.2%. Market expects cut in Q3.", "title": "Fed Decision", "source": "WSJ", "content": "Fed holds rates at 5.5%, inflation at 3.2%."},
        {"id": 6, "text": "Gold prices hit all-time high amid geopolitical uncertainty. Safe-haven demand surges. Central banks increase gold reserves.", "title": "Gold Rally", "source": "CNBC", "content": "Gold at all-time high amid geopolitical uncertainty."},
    ]
    vector_store.upsert(sample_docs)
    logger.info("Seeded knowledge base with 6 sample documents (DB was empty)")

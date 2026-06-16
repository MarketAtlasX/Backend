import json
import logging
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class GraphAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self._session = db_session
        self._relationships = []
        self._entities = []

    async def _load_entity_relationships(self, query_entities: list[str]):
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                from app.models.entity_relationship import EntityRelationship
                from app.models.entity import Entity as EntityModel
                from sqlalchemy import select
                for ent_name in query_entities[:5]:
                    entity_stmt = select(EntityModel).where(EntityModel.name.ilike(f"%{ent_name}%"))
                    result = await session.execute(entity_stmt)
                    entity = result.scalar_one_or_none()
                    if entity:
                        rel_stmt = select(EntityRelationship).where(
                            (EntityRelationship.source_entity_id == entity.id) |
                            (EntityRelationship.target_entity_id == entity.id)
                        ).limit(20)
                        rel_result = await session.execute(rel_stmt)
                        for rel in rel_result.scalars().all():
                            self._relationships.append(rel)
                        self._entities.append(entity.name)
        except Exception as e:
            logger.warning(f"Could not load entity relationships: {e}")

    def _format_relationships(self) -> str:
        if not self._relationships:
            return ""
        lines = ["Entity relationships from knowledge graph:"]
        for r in self._relationships[:15]:
            lines.append(f"- Entity #{r.source_entity_id} -[{r.relation_type}]-> Entity #{r.target_entity_id} (weight: {r.weight})")
        return "\n".join(lines)

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        entities = self._extract_entities(query)
        await self._load_entity_relationships(entities)
        knowledge = retrieve_context(query, limit=3)
        relations_text = self._format_relationships()

        system_prompt = """You are a knowledge graph analyst at MarketAtlas. Use entity relationships to explain connections
between geopolitical events, entities, and market impacts. Think of the world as an interconnected network.
Use the live entity relationship data provided below."""

        prompt = f"""Query: {query}

{'Live Entity Relationships (from knowledge graph):' + relations_text if relations_text else 'Entities identified: ' + ', '.join(entities) if entities else 'No specific entities found.'}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Explain the relationships and connections relevant to this query:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)

        return {
            "agent": "GraphAgent",
            "response": response,
            "entities": entities,
            "relations_found": len(self._relationships),
        }

    def _extract_entities(self, text: str) -> list[str]:
        prompt = f"""Extract all named entities (countries, companies, organizations, people, sectors, commodities) from this query.
Return ONLY a JSON array of strings, nothing else.
Query: {text}"""
        try:
            result = self.llm.generate(prompt, temperature=0.1)
            result = result.strip().strip("```json").strip("```").strip()
            return json.loads(result) if result.startswith("[") else []
        except Exception:
            return []

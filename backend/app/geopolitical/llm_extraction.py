"""LLM-powered geopolitical event extraction."""

import json
import logging
import os
from typing import Optional

from app.geopolitical.models import NewsArticle, ExtractedEntity

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

EXTRACTION_PROMPT = """You are a geopolitical intelligence analyst. Extract structured geopolitical events from the following news article.

For each event found, extract:
1. event_type: One of: sanction, trade_policy, military_conflict, diplomatic, election, economic_data, regulatory, natural_disaster, corporate, other
2. entities: List of entities involved, each with:
   - name: Entity name
   - entity_type: One of: COUNTRY, COMPANY, PERSON, PRODUCT, ORGANIZATION, LOCATION, EVENT
3. sentiment: Overall sentiment toward the primary entity - "positive", "negative", or "neutral"
4. severity: 0.0 (minimal impact) to 1.0 (critical)
5. relevance_ticker: If this article is relevant to a specific stock ticker, mention it (or null)

Return ONLY valid JSON in this format:
{
  "events": [
    {
      "event_type": "sanction",
      "entities": [{"name": "China", "entity_type": "COUNTRY"}, {"name": "NVIDIA", "entity_type": "COMPANY"}],
      "sentiment": "negative",
      "severity": 0.7,
      "relevance_ticker": "NVDA"
    }
  ]
}

If no geopolitical events are found, return {"events": []}

Article:
Title: {title}
Content: {content}
"""


def extract_with_llm(articles: list[NewsArticle]) -> list[ExtractedEntity]:
    """Extract entities using LLM (OpenAI or Claude). Falls back to empty if no API key."""

    if not OPENAI_API_KEY and not CLAUDE_API_KEY:
        logger.warning("No LLM API key set (OPENAI_API_KEY or CLAUDE_API_KEY) — skipping LLM extraction")
        return []

    seen: set[tuple[str, str]] = set()
    entities: list[ExtractedEntity] = []

    for article in articles[:5]:  # Limit to 5 articles per call for cost/speed
        try:
            prompt = EXTRACTION_PROMPT.format(
                title=article.title[:500],
                content=article.content[:2000],
            )

            result = None
            if OPENAI_API_KEY:
                result = _call_openai(prompt)
            elif CLAUDE_API_KEY:
                result = _call_claude(prompt)

            if result and "events" in result:
                for event in result["events"]:
                    for ent in event.get("entities", []):
                        key = (ent["name"].lower(), ent["entity_type"])
                        if key not in seen:
                            seen.add(key)
                            entities.append(ExtractedEntity(
                                name=ent["name"],
                                entity_type=ent["entity_type"],
                                sentiment=event.get("sentiment", "neutral"),
                                confidence=min(event.get("severity", 0.5) + 0.2, 1.0),
                            ))
        except Exception as e:
            logger.warning(f"LLM extraction failed for article '{article.title[:50]}': {e}")
            continue

    logger.info(f"llm_extraction: {len(entities)} entities from {len(articles)} articles")
    return entities


def _call_openai(prompt: str) -> Optional[dict]:
    import httpx
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Extract JSON from potential markdown fences
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning(f"OpenAI call failed: {e}")
        return None


def _call_claude(prompt: str) -> Optional[dict]:
    import httpx
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except Exception as e:
        logger.warning(f"Claude call failed: {e}")
        return None

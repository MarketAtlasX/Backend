"""Knowledge Graph agent HTTP client — fetches news, entities, and relationships.

Calls the external knowledge-graph-agent microservice (port 8005) to perform
entity extraction, news retrieval, and knowledge graph construction for
stocks and countries.
"""

import logging

import httpx

from app.config import settings
from app.schemas.knowledge_graph import KGResponse

logger = logging.getLogger(__name__)

KG_AGENT_URL = settings.kg_agent_url


async def analyze_stock_knowledge_graph(stock: str, timeout: float = 30.0) -> KGResponse:
    """Call the KG agent service to fetch news, extract entities, and build a graph.

    Returns an empty KGResponse if the service is unreachable or times out.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{KG_AGENT_URL}/analyze", json={"stock": stock})
        resp.raise_for_status()
        return KGResponse.from_raw(resp.json())
    except httpx.TimeoutException:
        logger.warning("KG agent service timed out for stock=%s", stock)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "KG agent service returned %s for stock=%s: %s",
            e.response.status_code,
            stock,
            e.response.text,
        )
    except httpx.RequestError as e:
        logger.warning("KG agent service unreachable for stock=%s: %s", stock, e)
    return KGResponse()


async def analyze_country_knowledge_graph(country: str, timeout: float = 12.0) -> KGResponse:
    """Call the KG agent service to fetch news about a country.

    Uses the /analyze-country endpoint which searches by country name.
    Returns an empty KGResponse if the service is unreachable or times out.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{KG_AGENT_URL}/analyze-country", json={"country": country})
        resp.raise_for_status()
        return KGResponse.from_raw(resp.json())
    except httpx.TimeoutException:
        logger.warning("KG agent service timed out for country=%s", country)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "KG agent service returned %s for country=%s: %s",
            e.response.status_code,
            country,
            e.response.text,
        )
    except httpx.RequestError as e:
        logger.warning("KG agent service unreachable for country=%s: %s", country, e)
    return KGResponse()

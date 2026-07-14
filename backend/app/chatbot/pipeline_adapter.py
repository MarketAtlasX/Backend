"""Adapter between chatbot agents and the pipelines/data-factory system.

Wraps pipelines.Event, pipelines.Context, and pipeline execution into
simple async functions that chatbot agents can call directly.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pipelines.core.types import Context as PipelineContext
from pipelines.core.types import Event as PipelineEvent
from pipelines.core.types import PipelineType

logger = logging.getLogger(__name__)

_factory = None


async def _get_factory():
    global _factory
    if _factory is None:
        from pipelines import build_pipelines

        _factory = build_pipelines()
    return _factory


async def run_similarity_pipeline(
    query: str,
    title: str = "",
    content: str = "",
    top_k: int = 20,
) -> dict[str, Any]:
    """Run event similarity search via pipelines.similarity.

    Returns matched events with similarity scores and market outcomes.
    """
    factory = await _get_factory()
    event = PipelineEvent(
        source="chatbot",
        type="similarity",
        data={
            "title": title or query,
            "content": content or query,
        },
    )
    ctx = PipelineContext(
        pipeline="event_similarity",
        pipeline_type=PipelineType.SIMILARITY,
        params={"similarity_threshold": 0.3, "source": "chatbot_query"},
    )
    outcome = await factory.run("event_similarity", event, **ctx.params)
    if outcome.status.value != "success":
        logger.warning("Similarity pipeline failed: %s", outcome.error)
        return {"similar_events": [], "aggregated_outcomes": {}, "confidence": 0.0}
    result = outcome.events[0].data if outcome.events else {}
    return {
        "similar_events": result.get("matched_events_with_outcomes", [])
        or result.get("matched_events", []),
        "aggregated_outcomes": result.get("market_outcomes", {}),
        "confidence": max(
            (m.get("similarity_score", 0) for m in result.get("matched_events", [])),
            default=0.0,
        ),
    }


async def run_shap_pipeline(
    query: str,
    features: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run SHAP explainability via pipelines.explainability."""
    factory = await _get_factory()
    event = PipelineEvent(
        source="chatbot",
        type="explainability",
        data={
            "features": features or [],
            "query": query,
        },
    )
    ctx = PipelineContext(
        pipeline="explainability_shap",
        pipeline_type=PipelineType.EXPLAINABILITY,
    )
    outcome = await factory.run("explainability_shap", event)
    if outcome.status.value != "success":
        return {"features": [], "top_feature": {"feature": "unknown", "shap_value": 0.0}}
    return outcome.events[0].data.get("shap_explanation", {}) if outcome.events else {}


async def run_graph_path_pipeline(
    entities: list[str],
    sectors: list[str],
) -> dict[str, Any]:
    """Run graph path extraction via pipelines.explainability."""
    import networkx as nx

    factory = await _get_factory()
    G = nx.DiGraph()
    for e in entities:
        G.add_node(e, type="entity")
    for s in sectors:
        G.add_node(s, type="sector", ticker={"Energy": "XLE", "Defense": "ITA", "Technology": "XLK", "Financials": "XLF", "Healthcare": "XLV", "Cybersecurity": "CIBR", "Shipping": "SEA", "Agriculture": "DBA", "Manufacturing": "XLI", "Real Estate": "XLRE", "Utilities": "XLU", "Airlines": "JETS"}.get(s, f"{s} ETF"))
    for e in entities:
        for s in sectors:
            G.add_edge(e, s, relation="impacts", weight=1.0)
    for s in sectors:
        ticker = {"Energy": "XLE", "Defense": "ITA", "Technology": "XLK", "Financials": "XLF", "Healthcare": "XLV", "Cybersecurity": "CIBR", "Shipping": "SEA", "Agriculture": "DBA", "Manufacturing": "XLI", "Real Estate": "XLRE", "Utilities": "XLU", "Airlines": "JETS"}.get(s, f"{s} ETF")
        G.add_edge(s, ticker, relation="prices", weight=1.0)

    if not sectors and entities:
        default_sectors = ["Energy", "Defense"]
        for e in entities:
            for s in default_sectors:
                G.add_edge(e, s, relation="impacts", weight=1.0)
                ticker = {"Energy": "XLE", "Defense": "ITA"}.get(s, f"{s} ETF")
                G.add_edge(s, ticker, relation="prices", weight=1.0)

    event = PipelineEvent(
        source="chatbot",
        type="graph_paths",
        data={"graph": G},
    )
    ctx = PipelineContext(
        pipeline="explainability_graph_paths",
        pipeline_type=PipelineType.EXPLAINABILITY,
        params={
            "source_nodes": entities if entities else None,
            "target_node": sectors[0] if sectors else None,
        },
    )
    outcome = await factory.run("explainability_graph_paths", event)
    if outcome.status.value != "success":
        return {"graph_paths": [], "path_count": 0}
    result = outcome.events[0].data if outcome.events else {}
    return {
        "graph_paths": result.get("graph_paths", []),
        "path_count": result.get("path_count", 0),
    }


async def run_historical_analogs_pipeline(
    sentiment: float = 0.0,
    event_type: str = "economic",
) -> list[dict[str, Any]]:
    """Run historical analogs matching via pipelines.explainability."""
    factory = await _get_factory()
    event = PipelineEvent(
        source="chatbot",
        type="historical_analogs",
        data={"feature_aggregates": {"avg_sentiment": sentiment}},
    )
    ctx = PipelineContext(
        pipeline="explainability_analogs",
        pipeline_type=PipelineType.EXPLAINABILITY,
        params={"event_type": event_type},
    )
    outcome = await factory.run("explainability_analogs", event)
    if outcome.status.value != "success":
        return []
    return outcome.events[0].data.get("historical_analogs", []) if outcome.events else []


async def run_entity_extraction_pipeline(
    text: str,
) -> dict[str, list[str]]:
    """Extract countries and organizations via pipelines.nlp."""
    factory = await _get_factory()
    event = PipelineEvent(
        source="chatbot",
        type="entity_extraction",
        data={
            "cleaned_events": [{"title": text[:200], "content": text}],
        },
    )
    ctx = PipelineContext(
        pipeline="nlp_entities",
        pipeline_type=PipelineType.NLP,
    )
    outcome = await factory.run("nlp_entities", event)
    if outcome.status.value != "success":
        return {"countries": [], "organizations": []}
    extracted = outcome.events[0].data.get("entity_extracted_events", []) if outcome.events else []
    if extracted and isinstance(extracted[0], dict):
        return extracted[0].get("entities", {"countries": [], "organizations": []})
    return {"countries": [], "organizations": []}


async def run_embedding_pipeline(
    texts: list[str],
) -> dict[str, list[list[float]]]:
    """Generate text embeddings via pipelines.nlp."""
    factory = await _get_factory()
    events_data = [{"title": t[:200], "content": t} for t in texts]
    event = PipelineEvent(
        source="chatbot",
        type="embedding",
        data={"cleaned_events": events_data},
    )
    ctx = PipelineContext(
        pipeline="nlp_embedding",
        pipeline_type=PipelineType.NLP,
    )
    outcome = await factory.run("nlp_embedding", event)
    if outcome.status.value != "success":
        return {"embeddings": []}
    embedded = outcome.events[0].data.get("embedded_events", []) if outcome.events else []
    return {"embeddings": [e.get("embedding", []) for e in embedded if isinstance(e, dict)]}


async def run_daily_pipeline() -> dict[str, Any]:
    """Run the daily end-to-end pipeline (GDELT → signals)."""
    factory = await _get_factory()
    event = PipelineEvent(source="scheduler", type="daily", data={})
    ctx = PipelineContext(
        pipeline="daily_pipeline",
        pipeline_type=PipelineType.DAILY,
        params={"trigger": "manual"},
    )
    outcome = await factory.run("daily", event)
    if outcome.status.value != "success":
        logger.error("Daily pipeline failed: %s", outcome.error)
        return {"status": "failed", "error": outcome.error}
    return {
        "status": "success",
        "metrics": outcome.metrics,
    }


async def run_realtime_pipeline(
    title: str = "",
    content: str = "",
) -> dict[str, Any]:
    """Run the real-time pipeline (Kafka → embedding → similarity → impact)."""
    factory = await _get_factory()
    event = PipelineEvent(
        source="chatbot",
        type="realtime",
        data={"title": title, "content": content},
    )
    ctx = PipelineContext(
        pipeline="realtime_pipeline",
        pipeline_type=PipelineType.REALTIME,
    )
    outcome = await factory.run("realtime", event)
    if outcome.status.value != "success":
        return {"status": "failed", "error": outcome.error}
    return {
        "status": "success",
        "data": outcome.events[0].data if outcome.events else {},
    }

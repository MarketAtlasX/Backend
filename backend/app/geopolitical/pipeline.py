"""Unified geopolitical intelligence pipeline."""

import logging
from typing import Optional

from app.geopolitical.extraction import extract_entities
from app.geopolitical.graph_builder import analyze_graph_impact, build_knowledge_graph
from app.geopolitical.ingestion import fetch_news
from app.geopolitical.llm_extraction import extract_with_llm
from app.geopolitical.models import (
    AnalysisResult,
    ImpactResult,
    MarketSnapshot,
)
from app.geopolitical.signals import generate_signal

logger = logging.getLogger(__name__)


async def run_pipeline(
    query: str,
    ticker: Optional[str] = None,
    price_history: Optional[list[float]] = None,
) -> AnalysisResult:
    messages: list[str] = []

    news = fetch_news(query)
    messages.append(f"Fetched {len(news)} news articles")

    entities = extract_entities(news)
    messages.append(f"Extracted {len(entities)} entities (spaCy)")

    # 2a. LLM-powered extraction (augments spaCy extraction)
    llm_entities = extract_with_llm(news)
    all_entity_names = {e.name.lower() for e in entities}
    for llm_e in llm_entities:
        if llm_e.name.lower() not in all_entity_names:
            entities.append(llm_e)
            all_entity_names.add(llm_e.name.lower())
    if llm_entities:
        messages.append(f"LLM extraction added {len(llm_entities)} entities")

    nodes, edges = build_knowledge_graph(query, entities)
    messages.append(f"Built graph: {len(nodes)} nodes, {len(edges)} edges")

    composite_risk, impact_messages = analyze_graph_impact(query, nodes, edges)
    messages.extend(impact_messages)
    impact = ImpactResult(
        composite_risk=composite_risk,
        local_severity=composite_risk,
        entity_count=len(entities),
    )

    market = None
    if ticker:
        from yfinance import Ticker
        try:
            tk = Ticker(ticker)
            hist = tk.history(period="1mo")
            if not hist.empty:
                prices = hist["Close"].tolist()
                if price_history is None:
                    price_history = prices
                momentum = (prices[-1] - prices[0]) / prices[0] if prices else 0.0
                volatility = float(hist["Close"].pct_change().std())
                volume_status = "normal"
                market = MarketSnapshot(
                    symbol=ticker,
                    momentum=float(momentum),
                    volatility=volatility,
                    volume_status=volume_status,
                )
        except Exception as e:
            logger.warning(f"yfinance failed for {ticker}: {e}")

    signal = generate_signal(impact=impact, market=market)
    messages.append(f"Signal: {signal.action} ({signal.confidence:.0%} confidence)")

    return AnalysisResult(
        news=news,
        entities=entities,
        graph_nodes=nodes,
        graph_edges=edges,
        market=market,
        impact=impact,
        signal=signal,
        messages=messages,
    )

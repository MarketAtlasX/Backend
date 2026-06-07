# market_agents

MarketAtlas `market_agents` is a lightweight Python prototype that combines market signals with simple geopolitical impact analysis and basic trade recommendations. It's designed to be fast to iterate on and resilient when external services (APIs, Neo4j) are unavailable.

## Core agents

- **Impact Analysis Agent**: extracts simple entity relations from text, builds an in-memory graph, and computes local/composite risk scores.
- **Market Data Agent**: computes momentum, rolling volatility, and volume status from a price series.
- **Recommendation Agent**: synthesizes market snapshot + impact score to produce BUY / HOLD / SELL guidance.

## What works today

- Runnable demo entrypoint: `main.py`.
- Best-effort ingest helpers for Alpha Vantage, FRED, EIA, GDELT, and ACLED with deterministic fallbacks.
- A focused pytest suite covering demo flows, market-data signals, impact processing, recommendation logic, and ingest helper behavior.
- Optional Neo4j persistence for Impact graphs (best-effort — does not break runtime if Neo4j is unreachable).

## Repository layout

```text
market_agents/
  main.py
  graph/
  impact/
  ingest/
  market_data/
  persistence/
  recommendation/
  tests/
  requirements.txt
  README.md
  docker-compose.neo4j.yml
```

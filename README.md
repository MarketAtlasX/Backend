# MarketAtlas

**Geopolitically-aware trading signals powered by AI**

MarketAtlas ingests geopolitical and market events, links them to real-world entities (countries, companies, people), fetches market data from Yahoo Finance, and runs a multi-agent AI pipeline to generate actionable trading signals — **Buy, Sell, Hold, or Short**. Optionally enriches signals with knowledge-graph data for deeper context.

## Features

- **Event Management** — CRUD and filter geopolitical/market events by type, severity, status, or recency
- **Entity Registry** — Manage countries, companies, people, indices, and commodities with geo-coordinates for globe visualization
- **Market Data Ingestion** — Fetch historical OHLCV data from Yahoo Finance per entity
- **AI Trading Signals** — Multi-agent pipeline: `ImpactAgent` → `MarketDataAgent` → `RecommendationAgent` generates signals with confidence scores, reasoning, and price targets
- **Knowledge Graph Enrichment** — Integrate with an external KG agent for entity extraction, news, and relationship graphs
- **Country Overview** — Combined dashboard view of country data, events, companies, prices, and KG-derived news
- **Free-text Analysis** — Ad-hoc market sentiment analysis with automatic ticker extraction
- **Pagination & Filtering** — All list endpoints support `skip`/`limit` pagination and rich filtering
- **DB-Level Integrity** — CHECK constraints on all categorical fields, unique constraints, and cascade deletes

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| Database | PostgreSQL (async via `asyncpg`) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Market Data | `yfinance` (Yahoo Finance) |
| AI Agents | `market_agents` (ImpactAgent, MarketDataAgent, RecommendationAgent) |
| Task Queue | Celery (Redis broker) |
| Caching | Redis |
| HTTP Client | `httpx` |
| Testing | pytest + pytest-asyncio |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   FastAPI App                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  Routes   │→ │ Services │→ │ Repositories  │  │
│  │ (handlers)│  │(business)│  │  (data access)│  │
│  └──────────┘  └──────────┘  └──────┬───────┘  │
│                                     │           │
│  ┌──────────────────────────────────┘           │
│  │  ┌──────────────┐  ┌──────────────────┐     │
│  │  │ AI Service   │  │  KG Service      │     │
│  │  │(market_agents│  │(knowledge-graph) │     │
│  │  │  gateway)    │  │  agent service   │     │
│  │  └──────────────┘  └──────────────────┘     │
│  └─────────────────────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
         PostgreSQL           Redis
       (5 tables)         (Celery broker)
```

## API Overview

| Route Group | Prefix | Key Endpoints |
|------------|--------|---------------|
| Events | `/events` | CRUD, filter, link/unlink entities |
| Entities | `/entities` | CRUD, filter by type/country, search |
| Market Prices | `/market-prices` | CRUD, yfinance fetch, latest/range queries |
| Signals | `/signals` | CRUD, filter by type/status/confidence |
| AI Analysis | `/events/{id}/analyze` | Run AI pipeline → generate signals |
| Free-text | `/analyze` | Ad-hoc sentiment analysis |
| Knowledge Graph | `/events/{id}/knowledge-graph` | KG enrichment |
| Countries | `/countries/{id}` | Overview + news dashboard |
| Health | `/health` | Health check |

Full API documentation at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc).

## Database Schema

| Table | Description |
|-------|-------------|
| `entities` | Countries, companies, people, regions, indices, commodities (with lat/lng for globe viz) |
| `events` | Geopolitical/market events with type, severity, status, and source |
| `event_entities` | Many-to-many link between events and entities |
| `market_prices` | OHLCV price data per entity per date |
| `signals` | AI-generated trading signals with confidence, reasoning, targets, and PnL |

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis (optional, for Celery)

### Setup

```bash
# Clone the repository
git clone https://github.com/MarketAtlasX/Backend.git
cd MarketAtlas/backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run migrations
alembic upgrade head

# (Optional) Seed with 32 real-world entities
python seed_real.py

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | *(required)* | PostgreSQL password |
| `DB_NAME` | `marketatlas` | Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `MARKET_AGENTS_URL` | `http://localhost:8004` | AI agents gateway |
| `KG_AGENT_URL` | `http://localhost:8005` | Knowledge graph agent |
| `ENABLE_WORKERS` | `False` | Feature flag for Celery |

See `backend/.env.example` for all options.

## External Dependencies

- **[market_agents](https://github.com/MarketAtlasX/market_agents)** — AI agent gateway (ImpactAgent, MarketDataAgent, RecommendationAgent). Runs on port 8004.
- **[knowledge-graph-agent](https://github.com/MarketAtlasX/knowledge-graph-agent)** — News scraping, entity extraction, and relationship graphs. Runs on port 8005.

## Deployment

```bash
# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Docker support is planned (Dockerfile and docker-compose.yml stubs are in place).

## Development

```bash
# Run tests (once written)
pytest

# Clean test data
python scripts/clean_test_data.py
```



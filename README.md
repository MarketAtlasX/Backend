# MarketAtlas

**Geopolitically-aware trading signals powered by AI**

MarketAtlas ingests geopolitical and market events, links them to real-world entities (countries, companies, people), fetches market data from Yahoo Finance, and runs a multi-agent AI pipeline to generate actionable trading signals — **Buy, Sell, Hold, or Short**. Optionally enriches signals with knowledge-graph data for deeper context.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       FastAPI App (port 8000)                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐               │
│  │  Routes   │→ │ Services │→ │ Repositories  │→ PostgreSQL  │
│  │ (10 rtrs) │  │(10 svcs) │  │   (6 repos)   │             │
│  └──────────┘  └──────────┘  └──────┬───────┘               │
│                                     │                        │
│  ┌──────────────────────────────────┘                        │
│  │  ┌──────────────────┐  ┌──────────────────┐              │
│  │  │ Market Agents    │  │  KG Service      │  ← Redis     │
│  │  │ Client (HTTP)    │  │  (HTTP + models) │    Cache     │
│  │  └────────┬─────────┘  └────────┬─────────┘              │
│  └───────────┼──────────────────────┼────────────────────────┘
│              │                      │                        │
│  Middleware: │ Logging │ Metrics │ Rate Limit │              │
└──────────────┼──────────────────────┼────────────────────────┘
               │                      │
               ▼                      ▼
      market_agents (8004)    knowledge-graph-agent (8005)
      (HTTP gateway)         (news, entities, relationships)
```

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
| AI Agents | `market_agents` (HTTP gateway on port 8004) |
| Knowledge Graph | `knowledge-graph-agent` (HTTP gateway on port 8005) |
| Task Queue | Celery (Redis broker) |
| Caching | Redis (async via `redis-py`) |
| HTTP Client | `httpx` |
| Observability | Prometheus metrics, structured logging |
| Rate Limiting | In-memory token bucket |
| Testing | pytest + pytest-asyncio + httpx |

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
| Dashboard | `/dashboard/summary` | Aggregated platform statistics |
| Health | `/health` | Deep health check (DB, Redis) |
| Metrics | `/metrics` | Prometheus metrics endpoint |

Full API documentation at `http://localhost:8000/docs` (Swagger UI).

## Database Schema

| Table | Description |
|-------|-------------|
| `entities` | Countries, companies, people, regions, indices, commodities (with lat/lng for globe viz) |
| `events` | Geopolitical/market events with type, severity, status, and source |
| `event_entities` | Many-to-many link between events and entities |
| `market_prices` | OHLCV price data per entity per date |
| `signals` | AI-generated trading signals with confidence, reasoning, targets, and PnL |

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app with middleware + lifespan
│   ├── config.py                  # Pydantic settings (env-based)
│   ├── database.py                # Async SQLAlchemy engine + session
│   ├── cache.py                   # Redis caching layer
│   ├── core/
│   │   └── enums.py               # StrEnum for all categorical fields
│   ├── models/                    # SQLAlchemy ORM models (5 tables)
│   ├── schemas/                   # Pydantic request/response models
│   │   └── knowledge_graph.py     # Typed KG response models
│   ├── repositories/              # Data access layer (6 repos)
│   │   └── event_entity.py        # Junction table repository
│   ├── services/                  # Business logic layer
│   │   ├── ai_service.py          # AI analysis (uses HTTP client)
│   │   ├── market_agents_client.py # HTTP client for market_agents
│   │   ├── kg_service.py          # Typed KG agent HTTP client
│   │   └── ...
│   ├── routes/                    # API route handlers (10 routers)
│   │   └── dashboard.py           # Aggregated stats endpoint
│   ├── middleware/                 # Observability middleware
│   │   ├── logging.py             # Structured request logging
│   │   ├── metrics.py             # Prometheus metrics
│   │   └── ratelimit.py           # In-memory rate limiting
│   └── workers/                   # Celery background tasks
│       ├── celery_app.py          # Celery app configuration
│       ├── analysis_tasks.py      # Async AI analysis tasks
│       └── market_data_tasks.py   # Async yfinance fetch tasks
├── alembic/                       # Database migrations
├── tests/                         # Test suite (pytest)
│   ├── conftest.py                # Async fixtures with test DB
│   ├── test_routes/               # Route tests
│   ├── test_services/             # Service tests
│   └── test_repositories/         # Repository tests
├── scripts/                       # Utility scripts
├── Dockerfile                     # Production Docker image
├── docker-compose.yml             # Multi-service orchestration
└── requirements.txt
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis (optional, for caching + Celery)

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

### Background Workers

```bash
# Start Celery worker (in a separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# Trigger async analysis
# (task is available but requires ENABLE_WORKERS=True)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | PostgreSQL user |
| `DB_PASSWORD` | *(required)* | PostgreSQL password |
| `DB_NAME` | `marketatlas` | Database name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery results |
| `MARKET_AGENTS_URL` | `http://localhost:8004` | AI agents gateway |
| `KG_AGENT_URL` | `http://localhost:8005` | Knowledge graph agent |
| `ENABLE_WORKERS` | `False` | Feature flag for Celery |

## External Dependencies

- **[market_agents](https://github.com/MarketAtlasX/market_agents)** — AI agent gateway (ImpactAgent, MarketDataAgent, RecommendationAgent). Runs on port 8004. Called via HTTP.
- **[knowledge-graph-agent](https://github.com/MarketAtlasX/knowledge-graph-agent)** — News scraping, entity extraction, and relationship graphs. Runs on port 8005. Called via HTTP.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_routes/test_events.py
```

## Observability

- **Metrics**: `GET /metrics` exposes Prometheus metrics
- **Logging**: Structured JSON request logs with request IDs
- **Health**: `GET /health` deep-checks DB and Redis connectivity
- **Rate Limiting**: 200 requests/minute per IP (configurable)

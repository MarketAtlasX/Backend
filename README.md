# MarketAtlas

**Geopolitically-aware trading signals powered by AI**

MarketAtlas ingests geopolitical and market events, links them to real-world entities (countries, companies, people, commodities, indices), fetches market data from Yahoo Finance, and runs a multi-agent AI pipeline to generate actionable trading signals — **Buy, Sell, Hold, or Short**. Signals can be enriched with knowledge-graph data for deeper geopolitical context.

This repository is the **workspace root** for the MarketAtlas ecosystem. It contains the primary backend service plus workspace configuration for the full multi-repo system.

---

## Repository Map

| Directory | Purpose |
|-----------|---------|
| `backend/` | **Primary service** — FastAPI + Celery backend with PostgreSQL, Redis, AI agent orchestration |
| `docs/` | Documentation — API contract (`api-contract.md`) with full endpoint specifications |
| `dev.sh` | Development orchestrator — starts Docker services, backend, frontend, and agent microservices in parallel |
| `MarketAtlas.code-workspace` | VS Code multi-root workspace referencing the full ecosystem |

### Sibling Repositories (referenced by workspace & dev.sh)

| Repository | Port | Description |
|-----------|------|-------------|
| `frontend/` | 5173 | Vite-based web frontend |
| `market_agents/` | 8004 | AI agent gateway — ImpactAgent, MarketDataAgent, RecommendationAgent |
| `knowledge-graph-agent/` | 8005 | News scraping, entity extraction, and relationship graph builder |
| `chat-bot/` | — | AI chat interface with multi-agent orchestration |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        VS Code Workspace                          │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │
│  │ backend/ │  │  frontend/   │  │market_agents/│  │kg-agent/│  │
│  │ :8000    │  │ :5173        │  │ :8004        │  │ :8005   │  │
│  └────┬─────┘  └──────────────┘  └──────┬───────┘  └────┬────┘  │
│       │                                  │               │       │
└───────┼──────────────────────────────────┼───────────────┼───────┘
        │                                  │               │
        ▼                                  ▼               ▼
┌──────────────────┐              ┌──────────────┐  ┌──────────────┐
│   FastAPI App    │              │  AI Agent    │  │  Knowledge   │
│   (backend/)     │◄── HTTP ────│  Gateway     │  │  Graph Agent │
│                   │              │              │  │              │
│  ┌──────┐ ┌──────┐│              └──────────────┘  └──────────────┘
│  │Routes│→│Services││
│  └──┬───┘ └──┬───┘│
│     │        │     │
│     ▼        ▼     │
│  ┌──────┐ ┌──────┐│
│  │Repos │ │Cache ││
│  └──┬───┘ └──────┘│
│     │     Redis    │
│     ▼              │
│  PostgreSQL        │
│                    │
│  Middleware:        │
│  Logging │ Metrics │ Rate Limit
└──────────────────────┘
```

---

## Tech Stack

### Backend (`backend/`)
| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| Database | PostgreSQL 16 (async via `asyncpg`) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 + Pydantic Settings |
| Market Data | `yfinance` (Yahoo Finance) with `pandas`/`numpy` |
| AI/ML | LangGraph, LangChain, spaCy, sentence-transformers, Qdrant |
| Task Queue | Celery (Redis broker) |
| Caching | Redis (async via `redis-py`) |
| Knowledge Graph | Neo4j client |
| HTTP Client | `httpx` |
| Observability | Prometheus metrics, structured logging (Loguru) |
| Rate Limiting | In-memory token bucket (200 req/min) |
| Testing | pytest + pytest-asyncio + httpx |
| Containerization | Docker multi-stage build (Python 3.12-slim) |
| Code Quality | Ruff (lint + format), mypy, pre-commit hooks |

### Frontend (`frontend/`)
- Vite + React/TypeScript (port 5173)

### Agent Services
- **market_agents** — Python FastAPI gateway (port 8004)
- **knowledge-graph-agent** — Python FastAPI news/entity service (port 8005)

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+ (for frontend)
- Docker (for PostgreSQL + Redis)
- PostgreSQL 16
- Redis

### One-Command Dev Startup

```bash
./dev.sh
```

This orchestrates everything:
1. Starts PostgreSQL + Redis via Docker Compose
2. Runs Alembic migrations
3. Seeds sample event data
4. Launches the FastAPI backend on `:8000`
5. Launches the frontend (if `../frontend` exists) on `:5173`
6. Launches `market_agents` (if found) on `:8004`
7. Launches `knowledge-graph-agent` (if found) on `:8005`

Press `Ctrl+C` to gracefully shut down all services.

### Manual Setup (Backend Only)

```bash
# Navigate to backend
cd backend

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

The API will be available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### VS Code Workspace

Open `MarketAtlas.code-workspace` in VS Code for a multi-root workspace that includes all sibling repositories (`backend`, `frontend`, `market_agents`, `knowledge-graph-agent`, `chat-bot`) in a single editor window.

### Seed Data

```bash
# Seed 32 real-world entities (countries, companies, people)
python backend/seed_real.py

# Seed chatbot sample events
python -m backend.app.chatbot.scripts.seed_data
```

---

## Backend

### API Overview

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
| Globe | `/globe` | Entity relations for globe visualization |
| Auth | `/auth` | Authentication endpoints |
| Backtest | `/backtest` | Backtesting engine |
| AI Chat | `/api/chat` | Chatbot + WebSocket streaming |
| WebSocket | `/ws` | Real-time event streaming |
| Health | `/health` | Deep health check (DB, Redis) |
| Metrics | `/metrics` | Prometheus metrics endpoint |

Full API documentation at `http://localhost:8000/docs` (Swagger UI) or see `docs/api-contract.md`.

### Database Schema

| Table | Description |
|-------|-------------|
| `entities` | Countries, companies, people, regions, indices, commodities (with lat/lng for globe viz) |
| `events` | Geopolitical/market events with type, severity, status, and source |
| `event_entities` | Many-to-many link between events and entities |
| `market_prices` | OHLCV price data per entity per date |
| `signals` | AI-generated trading signals with confidence, reasoning, targets, and PnL |
| `users` | User accounts and authentication |
| `countries` | Country-specific data and metadata |
| `entity_relationships` | Relationships between entities |
| `military_relations` | Military alliance/conflict data |
| `ports` | Port and shipping route data |
| `trade_routes` | International trade route data |
| `raw_events` | Raw ingested events before processing |

### Backend Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app with middleware + lifespan
│   ├── config.py                  # Pydantic settings (env-based)
│   ├── database.py                # Async SQLAlchemy engine + session
│   ├── cache.py                   # Redis caching layer
│   ├── serializers.py             # Serialization utilities
│   ├── core/
│   │   └── enums.py               # StrEnum for all categorical fields
│   ├── models/                    # SQLAlchemy ORM models (13 tables)
│   ├── schemas/                   # Pydantic request/response models
│   ├── repositories/              # Data access layer (12 repos)
│   ├── services/                  # Business logic (15 services)
│   │   ├── ai_service.py          # AI analysis pipeline
│   │   ├── market_agents_client.py# HTTP client for market_agents
│   │   ├── kg_service.py          # Knowledge graph agent client
│   │   ├── gdelt_stream_service.py# GDELT event stream ingestion
│   │   ├── signal_service.py      # Trading signal generation
│   │   ├── event_broadcaster.py   # WebSocket event broadcasting
│   │   └── ...
│   ├── routes/                    # API route handlers (15 routers)
│   ├── middleware/                 # Logging, metrics, rate limiting
│   ├── workers/                   # Celery background tasks
│   ├── chatbot/                   # AI chatbot subsystem
│   │   ├── agents/                # 10 specialized AI agents
│   │   ├── api/                   # Chat REST + WebSocket routes
│   │   ├── llm/                   # LLM provider abstraction
│   │   ├── rag/                   # RAG pipeline (embeddings, vector store)
│   │   ├── knowledge/             # Neo4j knowledge graph client
│   │   ├── memory/                # Short/long-term conversation memory
│   │   └── workflow/              # LangGraph workflow orchestration
│   ├── backtesting/               # Backtesting engine
│   └── geopolitical/              # Geopolitical data pipeline
├── alembic/                       # Database migrations (7 versions)
├── tests/                         # pytest test suite
│   ├── conftest.py                # Async fixtures with test DB
│   ├── test_routes/               # Route integration tests
│   ├── test_services/             # Service unit tests
│   └── test_repositories/         # Repository tests
├── scripts/                       # Utility scripts
├── memory_store/                  # Reserved for vector/knowledge storage
├── Dockerfile                     # Production Docker image
├── docker-compose.yml             # Postgres 16 + Redis 7 + app
├── pyproject.toml                 # Build config, ruff, mypy, pytest
└── requirements.txt               # Python dependencies
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

### Background Workers

```bash
# Start Celery worker (in a separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# Trigger async analysis
# (task requires ENABLE_WORKERS=True)
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_routes/test_events.py
```

### Observability

- **Metrics**: `GET /metrics` exposes Prometheus metrics
- **Logging**: Structured JSON request logs with request IDs
- **Health**: `GET /health` deep-checks DB and Redis connectivity
- **Rate Limiting**: 200 requests/minute per IP (configurable)

---

## External Dependencies

- **[market_agents](https://github.com/MarketAtlasX/market_agents)** — AI agent gateway (ImpactAgent, MarketDataAgent, RecommendationAgent). Runs on port 8004. Called via HTTP.
- **[knowledge-graph-agent](https://github.com/MarketAtlasX/knowledge-graph-agent)** — News scraping, entity extraction, and relationship graphs. Runs on port 8005. Called via HTTP.

---

## Development

### Code Quality

```bash
# Lint and format (via pre-commit)
pre-commit run --all-files

# Or directly with ruff
ruff check .
ruff format .
```

### Docker

```bash
# Start infrastructure services only
docker compose -f backend/docker-compose.yml up -d db redis

# Build and run the full backend
docker compose -f backend/docker-compose.yml up --build
```

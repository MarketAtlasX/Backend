#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
PIDS=()
STARTED=false

cleanup() {
  echo ""
  echo "Shutting down all services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait
  echo "All services stopped."
}
trap cleanup EXIT INT TERM

export PYTHONUNBUFFERED=1
# Fix Anaconda sqlite3 conflict: brew's libsqlite3 has the required symbols
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/sqlite/lib

# ── 1. Docker services (Postgres + Redis) ──────────────────────────
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "backend"; then
  echo "[docker] Starting Postgres + Redis..."
  docker compose -f "$ROOT/backend/docker-compose.yml" up -d db redis
  echo "[docker] Waiting for Postgres..."
  until docker exec "$(docker ps --filter name=db -q)" pg_isready -U postgres 2>/dev/null; do
    sleep 1
  done
  echo "[docker] Running DB migrations..."
  (cd "$ROOT/backend" && alembic upgrade head)
  echo "[docker] Seeding sample events..."
  (cd "$ROOT/backend" && python -m app.chatbot.scripts.seed_data)
  STARTED=true
elif [ "$STARTED" = false ]; then
  echo "[docker] Already running."
fi

# ── 1b. Symlink pipelines package (if not already) ───────────────────
PY_VER="$("$ROOT/venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PIPELINES_SYMLINK="$ROOT/venv/lib/python$PY_VER/site-packages/pipelines"
PIPELINES_DIR=""
for d in "$ROOT/../pipelines" "$HOME/pipelines"; do
  [ -d "$d" ] && PIPELINES_DIR="$d" && break
done
if [ -n "$PIPELINES_DIR" ] && [ ! -L "$PIPELINES_SYMLINK" ]; then
  echo "[pipelines] Installing pipelines package..."
  ln -sf "$PIPELINES_DIR" "$PIPELINES_SYMLINK"
fi

# ── 1c. Pre-load Ollama model (so first request doesn't time out) ────
if command -v ollama &>/dev/null; then
  if ollama list 2>/dev/null | grep -q "qwen2.5:7b"; then
    echo "[ollama] Pre-loading qwen2.5:7b model..."
    # Send a trivial warm-up request; background so it doesn't block startup
    (ollama run qwen2.5:7b "Hello" 2>/dev/null || true) &
  fi
fi

# ── 2. Backend (FastAPI) ────────────────────────────────────────────
echo "[backend] Starting on :8000..."
BACKEND_PY="$ROOT/venv/bin/uvicorn"
if [ -f "$BACKEND_PY" ]; then
  (cd "$ROOT/backend" && PYTHONPATH="$ROOT/backend" "$BACKEND_PY" app.main:app --reload --port 8000) &
else
  (cd "$ROOT/backend" && uvicorn app.main:app --reload --port 8000) &
fi
PIDS+=($!)

# ── 3. Frontend (Vite) ──────────────────────────────────────────────
FRONTEND_DIR=""
for d in "$ROOT/frontend" "$HOME/frontend"; do
  [ -d "$d" ] && FRONTEND_DIR="$d" && break
done
if [ -n "$FRONTEND_DIR" ]; then
  echo "[frontend] Starting on :5173 (from $FRONTEND_DIR)..."
  (cd "$FRONTEND_DIR" && npm run dev) &
  PIDS+=($!)
else
  echo "[frontend] Not found, skipping."
fi

# ── 4. Market Agents (optional) ─────────────────────────────────────
MARKET_DIR=""
for d in "$ROOT/../market_agents" "$HOME/market_agents"; do
  [ -d "$d" ] && MARKET_DIR="$d" && break
done
if [ -n "$MARKET_DIR" ]; then
  echo "[market-agents] Starting market, impact, recommendation, and gateway services..."
  MARKET_PY="$MARKET_DIR/venv/bin/uvicorn"
  if [ -f "$MARKET_PY" ]; then
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" "$MARKET_PY" services.market_data.app:app --reload --port 8001) &
    PIDS+=($!)
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" "$MARKET_PY" services.impact.app:app --reload --port 8002) &
    PIDS+=($!)
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" "$MARKET_PY" services.recommendation.app:app --reload --port 8003) &
    PIDS+=($!)
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" "$MARKET_PY" services.gateway:app --reload --port 8004) &
  else
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" uvicorn services.market_data.app:app --reload --port 8001) &
    PIDS+=($!)
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" uvicorn services.impact.app:app --reload --port 8002) &
    PIDS+=($!)
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" uvicorn services.recommendation.app:app --reload --port 8003) &
    PIDS+=($!)
    (cd "$MARKET_DIR" && PYTHONPATH="$(dirname "$MARKET_DIR")" uvicorn services.gateway:app --reload --port 8004) &
  fi
  PIDS+=($!)
else
  echo "[market-agents] Not found, skipping."
fi

# ── 5. World State (optional) ─────────────────────────────────────────
WS_DIR=""
for d in "$ROOT/../world_state" "$HOME/world_state"; do
  [ -d "$d" ] && WS_DIR="$d" && break
done
if [ -n "$WS_DIR" ]; then
  echo "[world-state] Starting on :8006..."
  WORLD_STATE_API_KEY="$(awk -F= '/^WORLD_STATE_API_KEY=/{print substr($0, index($0, "=") + 1); exit}' "$ROOT/backend/.env")"
  if [ -z "$WORLD_STATE_API_KEY" ]; then
    echo "[world-state] WORLD_STATE_API_KEY is required in backend/.env." >&2
    exit 1
  fi
  WS_PY="$WS_DIR/venv/bin/uvicorn"
  if [ -f "$WS_PY" ]; then
    (cd "$WS_DIR" && PYTHONPATH="$WS_DIR" WORLD_STATE_API_KEY="$WORLD_STATE_API_KEY" "$WS_PY" world_state.server:app --reload --port 8006) &
  else
    (cd "$WS_DIR" && PYTHONPATH="$WS_DIR" WORLD_STATE_API_KEY="$WORLD_STATE_API_KEY" uvicorn world_state.server:app --reload --port 8006) &
  fi
  PIDS+=($!)
else
  echo "[world-state] Not found, skipping."
fi

# ── 6. KG Agent (optional) ──────────────────────────────────────────
KG_DIR=""
for d in "$ROOT/../knowledge-graph-agent" "$HOME/knowledge-graph-agent"; do
  [ -d "$d" ] && KG_DIR="$d" && break
done
if [ -n "$KG_DIR" ]; then
  echo "[kg-agent] Starting on :8005..."
  KG_PY="$KG_DIR/venv/bin/uvicorn"
  if [ -f "$KG_PY" ]; then
    (cd "$KG_DIR" && "$KG_PY" service:app --reload --port 8005) &
  else
    (cd "$KG_DIR" && uvicorn service:app --reload --port 8005) &
  fi
  PIDS+=($!)
else
  echo "[kg-agent] Not found, skipping."
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  MarketAtlas — all services starting in parallel"
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:5173"
echo "  Market:    http://localhost:8004  (if found)"
echo "  World St:  http://localhost:8006  (if found)"
echo "  KG Agent:  http://localhost:8005  (if found)"
echo "═══════════════════════════════════════════════════════"
echo "  Press Ctrl+C to stop everything."
echo ""

wait

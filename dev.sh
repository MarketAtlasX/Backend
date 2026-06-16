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

# ── 2. Backend (FastAPI) ────────────────────────────────────────────
echo "[backend] Starting on :8000..."
(cd "$ROOT/backend" && uvicorn app.main:app --reload --port 8000) &
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
  echo "[market-agents] Starting gateway on :8004..."
  MARKET_PY="$MARKET_DIR/venv/bin/uvicorn"
  if [ -f "$MARKET_PY" ]; then
    (cd "$MARKET_DIR" && PYTHONPATH="$MARKET_DIR" "$MARKET_PY" services.gateway:app --reload --port 8004) &
  else
    (cd "$MARKET_DIR" && uvicorn services.gateway:app --reload --port 8004) &
  fi
  PIDS+=($!)
else
  echo "[market-agents] Not found, skipping."
fi

# ── 5. KG Agent (optional) ──────────────────────────────────────────
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
echo "  KG Agent:  http://localhost:8005  (if found)"
echo "═══════════════════════════════════════════════════════"
echo "  Press Ctrl+C to stop everything."
echo ""

wait

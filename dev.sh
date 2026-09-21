#!/usr/bin/env bash
# One-command launcher: sets up the backend venv and frontend node_modules
# on first run, then starts both dev servers together. Ctrl+C stops both.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

port_in_use() {
  (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

if port_in_use "$BACKEND_PORT"; then
  echo "Port $BACKEND_PORT is already in use -- stop whatever's using it (maybe a previous run of this script) and try again." >&2
  exit 1
fi
if port_in_use "$FRONTEND_PORT"; then
  echo "Port $FRONTEND_PORT is already in use -- stop whatever's using it (maybe a previous run of this script) and try again." >&2
  exit 1
fi

command -v python3 >/dev/null || { echo "python3 is required but wasn't found on PATH." >&2; exit 1; }
command -v node >/dev/null || { echo "node is required but wasn't found on PATH." >&2; exit 1; }
command -v npm >/dev/null || { echo "npm is required but wasn't found on PATH." >&2; exit 1; }

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "==> Setting up backend virtual environment (first run only)..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi
echo "==> Checking backend dependencies..."
"$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> Installing frontend dependencies (first run only)..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "==> Starting backend on :$BACKEND_PORT"
(cd "$BACKEND_DIR" && exec .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT") &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "==> Stopping backend..."
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Backend failed to start -- check the output above for the error." >&2
  exit 1
fi

echo ""
echo "  HAR Analyzer starting up:"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo ""
echo "  Ctrl+C to stop both."
echo ""

cd "$FRONTEND_DIR" && npm run dev -- --port "$FRONTEND_PORT" --strictPort

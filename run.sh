#!/usr/bin/env bash
# Start Reviva locally. Builds the frontend (if needed) and serves everything
# — API + UI — from one FastAPI process.
set -e

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# Build the React frontend if it hasn't been built yet.
if [ ! -d "frontend/dist" ]; then
  echo "→ Building frontend (first run)…"
  ( cd frontend && npm install && npm run build )
fi

echo "→ Reviva on http://localhost:${PORT}"
echo "  (first photo is slow: model weights download on first use)"

uvicorn backend.main:app --host "$HOST" --port "$PORT"

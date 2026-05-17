#!/usr/bin/env bash
set -e

cleanup() {
  if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
}

trap cleanup EXIT INT TERM

cd "$(dirname "$0")"

(
  cd taskit-backend
  if [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
  elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
  fi
  python manage.py runserver 127.0.0.1:8000
) &
BACKEND_PID=$!

(
  cd taskit-frontend
  npm run dev -- --host 127.0.0.1
) &
FRONTEND_PID=$!

wait

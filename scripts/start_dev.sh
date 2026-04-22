#!/usr/bin/env bash
# BAMS AI — development startup script
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"
FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
STORAGE_DIR="$(cd "$(dirname "$0")/.." && pwd)/storage"

echo "==> Checking services..."

# PostgreSQL
pg_ctlcluster 16 main status 2>/dev/null | grep -q running || {
    echo "Starting PostgreSQL..."
    pg_ctlcluster 16 main start
}

# Redis
redis-cli ping 2>/dev/null | grep -q PONG || {
    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379
}

mkdir -p "$STORAGE_DIR"

echo "==> Starting backend (uvicorn)..."
cd "$BACKEND_DIR"
source .venv/bin/activate 2>/dev/null || { echo "Run: python -m venv .venv && pip install -e '.[all]'"; exit 1; }
PYTHONPATH="$BACKEND_DIR" nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload \
    > /tmp/bams_uvicorn.log 2>&1 &
echo "  Backend PID: $!"

echo "==> Starting Celery worker..."
CELERY_WORKER_RUNNING=1 PYTHONPATH="$BACKEND_DIR" \
nohup celery -A core.celery_app worker --loglevel=warning --concurrency=2 \
    > /tmp/bams_celery.log 2>&1 &
echo "  Celery PID: $!"

echo "==> Starting frontend (Vite)..."
cd "$FRONTEND_DIR"
nohup npm run dev -- --port 5173 --host 0.0.0.0 \
    > /tmp/bams_vite.log 2>&1 &
echo "  Vite PID: $!"

sleep 5
echo ""
echo "==> BAMS AI running:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:8000"
echo "   API docs:  http://localhost:8000/docs"
echo "   Login:     admin@bams.local / Admin1234!"
echo ""
echo "Logs: /tmp/bams_uvicorn.log  /tmp/bams_celery.log  /tmp/bams_vite.log"

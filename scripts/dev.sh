#!/usr/bin/env bash
# 一键本地开发环境启动（技术方案 5 scripts/）。
# Windows 请改用：python scripts/xian.py dev
#
#   bash scripts/dev.sh [--no-data]
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"
WITH_DATA=1
for arg in "$@"; do
  case "$arg" in
    --no-data) WITH_DATA=0 ;;
  esac
done

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }

say "1/5 启动数据面（PostgreSQL / Redis / ClickHouse / Qdrant / MinIO / litellm）"
if [ "$WITH_DATA" = "1" ] && command -v docker >/dev/null 2>&1; then
  docker compose -f deploy/docker/compose.dev.yml --profile data up -d
else
  say "跳过数据面：回退 SQLite + 内存总线 + mock 沙箱（mock_runtime）"
fi

say "2/5 安装后端依赖"
if command -v uv >/dev/null 2>&1; then
  (cd backend && uv sync --all-packages)
else
  (cd backend && pip install -e libs/xian_core -e services/api -e services/worker -e services/cli)
fi

say "3/5 数据库迁移"
(cd backend && PYTHONPATH=libs/xian_core/src "$PYTHON" -m alembic -c libs/xian_core/migrations/alembic.ini upgrade head) || true

say "4/5 导入种子数据"
(cd backend && PYTHONPATH=libs/xian_core/src:services/cli "$PYTHON" -m xian_cli seed)

say "5/5 启动 API + worker + Web"
(cd backend && PYTHONPATH=libs/xian_core/src:services/api "$PYTHON" -m uvicorn xian_api.main:app --reload --host "${API_HOST:-127.0.0.1}" --port "${API_PORT:-8000}") &
API_PID=$!
(cd backend && PYTHONPATH=libs/xian_core/src:services/worker "$PYTHON" -m celery -A xian_worker.celery_app worker -l info) &
WORKER_PID=$!
trap 'kill $API_PID $WORKER_PID 2>/dev/null || true' EXIT
(cd frontend && pnpm install && pnpm --filter @xian/web dev -- --port "${WEB_PORT:-5173}")
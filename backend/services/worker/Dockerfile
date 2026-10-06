# syntax=docker/dockerfile:1
# XIAN Worker 镜像：Celery worker + beat（技术方案 3.2）
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv==0.4.*"

WORKDIR /build
COPY backend/libs/xian_core/pyproject.toml libs/xian_core/pyproject.toml
COPY backend/libs/xian_core/src libs/xian_core/src
COPY backend/services/worker/pyproject.toml services/worker/pyproject.toml
COPY backend/services/worker/src/xian_worker services/worker/src/xian_worker
COPY pyproject.toml pyproject.toml

RUN uv pip install --system ./libs/xian_core ./services/worker


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    XIAN_ENV=prod

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/xian /usr/local/bin/xian

WORKDIR /app
COPY backend/libs/xian_core/src/xian_core /app/xian_core
COPY backend/services/worker/src/xian_worker /app/xian_worker

RUN useradd --system --create-home --uid 10001 xian \
    && mkdir -p /app/outputs \
    && chown -R xian:xian /app
USER xian

CMD ["celery", "-A", "xian_worker.celery_app", "worker", "-l", "info", "--concurrency", "4"]
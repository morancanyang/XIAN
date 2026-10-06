# syntax=docker/dockerfile:1
# XIAN API 服务镜像（Python 3.12 + uv，技术方案 3.2）
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
COPY backend/services/api/pyproject.toml services/api/pyproject.toml
COPY backend/services/api/src/xian_api services/api/src/xian_api
COPY pyproject.toml pyproject.toml

RUN uv pip install --system ./libs/xian_core ./services/api


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
COPY backend/services/api/src/xian_api /app/xian_api

RUN useradd --system --create-home --uid 10001 xian \
    && mkdir -p /app/outputs \
    && chown -R xian:xian /app
USER xian

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn", "xian_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
# syntax=docker/dockerfile:1
# 自建 egress 代理（技术方案 3.5）：白名单 + 蜜标域名映射，阻断一切出网请求。
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    EGRESS_BIND=0.0.0.0 \
    EGRESS_PORT=8899

WORKDIR /app
COPY server.py /app/server.py

RUN useradd --system --create-home --uid 10002 egress \
    && chown -R egress:egress /app
USER egress

EXPOSE 8899

CMD ["python", "-u", "server.py"]
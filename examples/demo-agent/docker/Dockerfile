# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    XIAN_DEMO_PORT=9001

ARG NONCE=xian-demo-nonce
ENV XIAN_DEMO_NONCE=${NONCE}

COPY xian_demo_agent /app/xian_demo_agent
COPY agent.py healthcheck.py /app/
WORKDIR /app

RUN printf "%s" "${XIAN_DEMO_NONCE}" > /app/nonce.txt \
    && useradd --system --create-home --uid 10002 demoagent \
    && chown -R demoagent:demoagent /app
USER demoagent

EXPOSE 9001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "healthcheck.py"]

CMD ["python", "agent.py", "--host", "0.0.0.0", "--port", "9001"]

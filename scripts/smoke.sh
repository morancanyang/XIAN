#!/usr/bin/env bash
# 端到端冒烟（AC-01：端到端 ≤ 30min）。
# 说明：本仓库的脚本入口以跨平台 Python 实现为准（scripts/xian.py），
# 本文件保留给纯 Linux/macOS 环境直接调用，内容与 xian.py smoke 保持一致。
#
#   bash scripts/smoke.sh
#
# Windows 上请使用：
#   python scripts/xian.py smoke
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mFAIL\033[0m %s\n' "$*"; exit 1; }

say "1/7 后端单元测试"
(cd backend && "$PYTHON" -m pytest -q) || fail "单元测试失败"

say "2/7 种子数据"
(cd backend && PYTHONPATH=libs/xian_core/src:services/cli/src "$PYTHON" -m xian_cli.main seed) || fail "种子导入失败"

say "3/7 CLI 自检"
(cd backend && PYTHONPATH=libs/xian_core/src:services/cli/src "$PYTHON" -m xian_cli.main version) || fail "CLI 自检失败"

say "4/7 API 冒烟（健康检查 → 建 Agent → 归属校验 → 健康探测）"
(cd backend && XIAN_DB_DSN_OVERRIDE=sqlite+aiosqlite:// PYTHONPATH=libs/xian_core/src:services/api/src "$PYTHON" - <<'PY'
from fastapi.testclient import TestClient

from xian_api.main import app

HEADERS = {
    "X-Tenant-Id": "00000000-0000-0000-0000-000000000001",
    "X-User-Id": "00000000-0000-0000-0000-0000000000a1",
    "X-Role": "admin",
}

with TestClient(app) as client:
    health = client.get("/healthz")
    assert health.status_code == 200, health.text
    print("healthz ok:", health.json()["status"])

    created = client.post(
        "/api/v1/agents",
        headers=HEADERS,
        json={"name": "smoke-agent", "access_type": "http", "endpoint": "http://127.0.0.1:9/chat"},
    )
    assert created.status_code == 201, created.text
    agent = created.json()
    print("agent created:", agent["id"])

    blocked = client.post(
        "/api/v1/campaigns",
        headers=HEADERS,
        json={"agent_id": agent["id"], "scope": ["XM-01"]},
    )
    print("campaign before verify ->", blocked.status_code)

    verified = client.post(
        f"/api/v1/agents/{agent['id']}/verify",
        headers=HEADERS,
        json={"method": "dns_txt", "target": "agent.example.com"},
    )
    assert verified.status_code == 200, verified.text
    print("ownership ->", verified.json()["result"])

    healthcheck = client.post(f"/api/v1/agents/{agent['id']}/healthcheck", headers=HEADERS)
    assert healthcheck.status_code == 200, healthcheck.text
    print("healthcheck ->", healthcheck.json()["result"])
PY
) || fail "API 冒烟失败"

say "5/7 前端类型检查"
(cd frontend && pnpm --filter @xian/types typecheck)
(cd frontend && pnpm --filter @xian/ui typecheck)
(cd frontend && pnpm --filter @xian/web typecheck) || fail "前端类型检查失败"

say "6/7 前端单测与构建"
(cd frontend && pnpm --filter @xian/web test) || fail "前端单测失败"
(cd frontend && pnpm --filter @xian/web build) || fail "前端构建失败"

say "7/7 CI 门禁（xian scan）"
(cd backend && PYTHONPATH=libs/xian_core/src:services/cli/src "$PYTHON" -m xian_cli.main scan \
  --agent-id smoke-agent --score 83 --previous 80 --new-high 0 --baseline-rate 1.0) || true

say "全部通过 ✅"
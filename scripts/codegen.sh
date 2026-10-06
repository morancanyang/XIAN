#!/usr/bin/env bash
# 契约同步：后端 OpenAPI → 前端 @xian/types（技术方案 5）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[codegen] 导出 openapi.json"
(cd backend && PYTHONPATH=libs/xian_core/src:services/api python - <<'PY'
import json
from xian_api.main import app

with open("../frontend/packages/types/openapi.json", "w", encoding="utf-8") as fh:
    json.dump(app.openapi(), fh, ensure_ascii=False, indent=2)
print("openapi.json written")
PY
)

echo "[codegen] 生成 TypeScript 客户端"
(cd frontend && pnpm codegen)

echo "[codegen] 完成。请Review diff 后提交。"
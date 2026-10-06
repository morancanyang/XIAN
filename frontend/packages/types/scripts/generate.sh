#!/usr/bin/env bash
# 从后端 FastAPI 应用导出 openapi.json 并生成 TypeScript 类型（技术方案 5：契约同源）。
# 用法：在 frontend/ 下执行 `pnpm codegen`。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TYPES_DIR="$ROOT_DIR/packages/types"
OUT="$TYPES_DIR/openapi.json"

echo "[codegen] 导出 OpenAPI 契约 -> $OUT"
mkdir -p "$TYPES_DIR/src"
(cd "$ROOT_DIR/../backend" && PYTHONPATH="libs/xian_core/src:services/api" python - <<'PY'
import json
from xian_api.main import app
with open("../../frontend/packages/types/openapi.json", "w", encoding="utf-8") as fh:
    json.dump(app.openapi(), fh, ensure_ascii=False, indent=2)
PY
)

echo "[codegen] 生成 TypeScript 类型 -> $TYPES_DIR/src/openapi.generated.ts"
npx --yes openapi-typescript@7 "$OUT" -o "$TYPES_DIR/src/openapi.generated.ts"

echo "[codegen] 完成。其余手写契约（enums.ts / events.ts / models.ts）与 schemas 一一对应。"
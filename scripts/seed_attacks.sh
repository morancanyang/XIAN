#!/usr/bin/env bash
# 导入攻击用例（cases/seed/*.yaml）。向量入库在 Qdrant 可用时异步执行。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
PYTHONPATH=libs/xian_core/src:services/api python - <<'PY'
from xian_core.cases import SEED_DIR, cases_by_category, load_seed_cases
from xian_core.matrix import load_categories

cases = load_seed_cases()
print(f"cases: {len(cases)} from {SEED_DIR}")
for cat in load_categories():
    print(f"  {cat.code} {cat.name}: {len(cases_by_category(cat.code))}")
PY
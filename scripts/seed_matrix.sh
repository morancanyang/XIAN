#!/usr/bin/env bash
# 导入 14 类攻击矩阵与框架映射。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
PYTHONPATH=libs/xian_core/src:services/api python - <<'PY'
from xian_core.matrix import load_categories, framework_names

cats = load_categories()
print(f"categories: {len(cats)}")
print("frameworks:", ", ".join(framework_names()))
print("codes:", ", ".join(c.code for c in cats))
PY
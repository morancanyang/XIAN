#!/usr/bin/env bash
# 导入十关教案与徽章定义。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
PYTHONPATH=libs/xian_core/src:services/api python - <<'PY'
from xian_core.levels import HINT_COST, LEVELS, TOTAL_ENERGY, achievement_catalog

print(f"levels: {len(LEVELS)}")
print(f"achievements: {len(achievement_catalog())}")
print(f"total_energy: {TOTAL_ENERGY}, hint_cost: {HINT_COST}")
PY
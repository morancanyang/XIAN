#!/usr/bin/env bash
# 导入靶场场景模板（S1~S8 六要素）。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
PYTHONPATH=libs/xian_core/src:services/api python - <<'PY'
from xian_core.scenarios import all_templates, available_scenarios, scenario_summary

print(f"scenarios: {len(available_scenarios())}")
for code, summary in scenario_summary().items():
    print(f"scenario {code}: {summary}")
print("templates:", [t["code"] for t in all_templates()])
PY
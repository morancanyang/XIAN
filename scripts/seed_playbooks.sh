#!/usr/bin/env bash
# 导入修复 Playbook 与根因库。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
PYTHONPATH=libs/xian_core/src:services/api python - <<'PY'
from xian_core.remediation import load_playbooks, load_root_causes

causes = load_root_causes()
playbooks = load_playbooks()
print(f"root_causes: {len(causes)}")
print(f"playbooks: {len(playbooks)}")
for cause in causes:
    print(f"  {cause.code}: {cause.name} -> {cause.fix_playbook_ref}")
PY
#!/usr/bin/env python3
"""启动演示 Agent：``python examples/demo-agent/agent.py``。

等价于 ``python -m xian_demo_agent.server``，仅为方便在仓库根目录直接运行。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from xian_demo_agent.server import main

if __name__ == "__main__":
    raise SystemExit(main())

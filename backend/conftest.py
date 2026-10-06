"""backend 测试根夹具：统一 pythonpath、SQLite 内存库与离线 LLM 回放。

无论从仓库根目录还是 backend/ 启动 pytest，都能以相同方式发现用例：

    python -m pytest backend            # 全套
    python -m pytest backend/libs        # xian_core 单测
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 测试一律走确定性离线回放（技术方案 7.2 降级链）。显式清空而不是 setdefault，
# 否则单独跑某个测试文件时会继承开发机上的真实 Key，导致离线断言不确定。
# 空 base_url + 空 api_key 时 LLMSettings 也不会按 DEEPSEEK_API_KEY 反推供应商。
os.environ["XIAN_LLM_BASE_URL"] = ""
os.environ["XIAN_LLM_API_KEY"] = ""
for _env in ("DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "DASHSCOPE_API_KEY",
             "SILICONFLOW_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(_env, None)

BACKEND = Path(__file__).resolve().parent
for extra in ("libs/xian_core/src", "services/api", "services/worker", "services/cli"):
    path = BACKEND / extra
    if not path.is_dir() or str(path) in sys.path:
        continue
    sys.path.insert(0, str(path))

# src 布局：包真实位于 services/<svc>/src/<pkg>
for svc, pkg in (("api", "xian_api"), ("worker", "xian_worker"), ("cli", "xian_cli")):
    for extra in (f"services/{svc}/src", f"services/{svc}/src/{pkg}"):
        path = BACKEND / extra
        if path.is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))

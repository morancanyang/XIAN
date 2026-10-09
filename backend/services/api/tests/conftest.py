"""services/api 测试夹具：统一离线 LLM 回放。

本目录自带 pytest 配置（``services/api/pyproject.toml``），单独跑该目录时
rootdir 是 ``backend/services/api``，仓库根的 ``backend/conftest.py`` 不在加载范围内，
会继承开发机上的真实 Key 把网关误判成在线。因此在这里同样显式清空。
"""

from __future__ import annotations

import os

# 清空整个 XIAN_LLM_* 命名空间：scripts/xian.py 会把根 .env 灌进环境变量，
# 只清 Key 不清 XIAN_LLM_PROVIDER 的话，LLMSettings 仍能按预设反推出端点与模型名，
# 网关依旧被判成在线。官方冒烟入口 python scripts/xian.py smoke
# 会在任何配过 .env 的机器上必红（AC-01 验收无法执行）。
for _env in [k for k in os.environ if k.startswith("XIAN_LLM_")]:
    os.environ.pop(_env, None)
for _key_env in ("DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "DASHSCOPE_API_KEY",
                 "SILICONFLOW_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(_key_env, None)
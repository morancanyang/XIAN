"""services/api 测试夹具：统一离线 LLM 回放。

本目录自带 pytest 配置（``services/api/pyproject.toml``），单独跑该目录时
rootdir 是 ``backend/services/api``，仓库根的 ``backend/conftest.py`` 不在加载范围内，
会继承开发机上的真实 Key 把网关误判成在线。因此在这里同样显式清空。
"""

from __future__ import annotations

import os

os.environ["XIAN_LLM_BASE_URL"] = ""
os.environ["XIAN_LLM_API_KEY"] = ""
for _key_env in ("DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "DASHSCOPE_API_KEY",
                 "SILICONFLOW_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(_key_env, None)
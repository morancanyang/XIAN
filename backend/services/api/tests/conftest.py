"""services/api 测试夹具：统一离线 LLM 回放。

本目录自带 pytest 配置（``services/api/pyproject.toml``），单独跑该目录时
rootdir 是 ``backend/services/api``，仓库根的 ``backend/conftest.py`` 不在加载范围内，
会继承开发机上的真实 Key 把网关误判成在线。因此在这里同样显式清空。
"""

from __future__ import annotations

import os

import pytest

# 清空整个 XIAN_LLM_* 命名空间：scripts/xian.py 会把根 .env 灌进环境变量，
# 只清 Key 不清 XIAN_LLM_PROVIDER 的话，LLMSettings 仍能按预设反推出端点与模型名，
# 网关依旧被判成在线。官方冒烟入口 python scripts/xian.py smoke
# 会在任何配过 .env 的机器上必红（AC-01 验收无法执行）。
for _env in [k for k in os.environ if k.startswith("XIAN_LLM_")]:
    os.environ.pop(_env, None)
for _key_env in ("DEEPSEEK_API_KEY", "MOONSHOT_API_KEY", "DASHSCOPE_API_KEY",
                 "SILICONFLOW_API_KEY", "ZHIPU_API_KEY", "OPENAI_API_KEY"):
    os.environ.pop(_key_env, None)

# 必须在 import xian_api.main 之前落位：main 在导入期就读 DSN 建引擎。此前只有部分测试
# 文件在自己的 client fixture 里 setdefault，谁先 import 谁决定连真库还是连内存库——
# 单跑某个文件时 rootdir 变了，就会去连 PostgreSQL 然后 ConnectionRefused。
os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")


@pytest.fixture(autouse=True)
def _fresh_rate_limit_buckets():
    """每个用例都从空的限流额度开始。

    RateLimitMiddleware 的计数桶挂在 app 单例上（key 是 tenant+IP），测试共用同一个
    app，不清桶的话前面用例耗掉的额度会让后面的用例吃到 429——之前全套 120 条请求正好
    卡在限额边缘，多写几个用例就整片泛红。
    """
    from xian_api.main import app
    from xian_api.middleware.tenant import RateLimitMiddleware

    def _clear() -> None:
        node = getattr(app, "middleware_stack", None)
        while node is not None:
            if isinstance(node, RateLimitMiddleware):
                node.reset()
            node = getattr(node, "app", None)

    _clear()
    yield
    _clear()

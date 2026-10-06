"""XIAN 演示被测 Agent。

本包位于 examples/demo-agent/ 目录下（目录名带连字符），N999 属预期告警。
"""


from .core import CANARY_TOKEN, FAKE_TOOLS, SYSTEM_PROMPT, build_chat_response
from .sdk import DemoAgentSDK, SDKError, SDKHandle, register

__all__ = [
    "CANARY_TOKEN",
    "FAKE_TOOLS",
    "SYSTEM_PROMPT",
    "DemoAgentSDK",
    "SDKError",
    "SDKHandle",
    "build_chat_response",
    "register",
]

__version__ = "1.0.0"

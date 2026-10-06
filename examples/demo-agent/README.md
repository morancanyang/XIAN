# 最小被测 Agent（Purpose-built demo target）

本目录是一个**可被 XIAN 平台真实探测的最小 AI Agent 示例**，用于：

- 演示 PRD 3.2.4「Agent 接入」的三种方式（HTTP / SDK / 容器）；
- 作为 CI 自检的 dogfood 目标：连通性探测、侦察画像、模式一/模式二都能打到它；
- 让演示/答辩时不依赖任何外部 LLM 供应商即可跑通端到端（AC-01 / AC-02）。

> 安全边界：示例 Agent 输出的订单、手机号、优惠券码、`sk-canary-*` **全部是蜜标（Canary）**，
> 绝不读取真实系统；命中高危工具或尝试外联时会显式上报 `canary_hit` 事件，
> 用来验证裁判的黄金信号链路不漏报（AC-03）。

## 运行

```bash
# 零第三方依赖，Python 3.11+ 标准库即可
python examples/demo-agent/agent.py --host 127.0.0.1 --port 9001

# 或等价写法
python -m xian_demo_agent.server --port 9001
```

然后在平台「Agent 接入」页填写：

| 字段 | 值 |
| --- | --- |
| 接入方式 | `http` |
| 端点 | `http://127.0.0.1:9001/chat` |
| 归属校验 | `dns_txt`，target 填 `127.0.0.1` |

平台侧环境变量（示例 Agent 侧同名即可生效）：

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `XIAN_DEMO_NONCE` | `xian-demo-nonce` | 归属校验演示 nonce |
| `XIAN_DEMO_TOKEN` | `demo-canary-token` | 开启鉴权时使用的假 token |
| `XIAN_DEMO_REQUIRE_AUTH` | 关 | 置 `1` 后 `/chat` 要求 `Authorization: Bearer` |
| `XIAN_DEMO_LATENCY_MS` | `40` | 模拟延迟，用于演示 P50/P99 统计 |
| `XIAN_DEMO_FAIL_RATE` | `0.0` | 模拟故障率，用于排障文案演示 |

## 目录

| 路径 | 说明 |
| --- | --- |
| `xian_demo_agent/core.py` | 蜜标数据 + ChatClient 协议响应构造 |
| `xian_demo_agent/server.py` | 零依赖 HTTP 服务（HTTP / 容器接入方式） |
| `xian_demo_agent/sdk.py` | SDK 接入方式（进程内回调） |
| `agent.py` | 便捷启动入口，等价 `python -m xian_demo_agent.server` |
| `docker/` | 容器接入方式（`image_digest` 归属校验）的镜像 |
| `test_demo_agent.py` | 13 条自检测试，无需启动服务 |

## 三种接入方式示例

**HTTP**：直接填端点 `http://127.0.0.1:9001/chat`，平台经 `GatewayChatClient` 访问。

**SDK**：Agent 在内网不暴露端口时，由平台持有进程内回调：

```python
from xian_demo_agent import DemoAgentSDK, register

agent = DemoAgentSDK(endpoint="http://127.0.0.1:9001", token="demo-canary-token")
handle = register(agent, agent_id="demo-agent")
agent.chat("这是一次连通性测试，请回复 pong")   # -> pong
handle.unregister()
```

**容器**：构建镜像后以 `access_type=container` 接入，归属校验走 `image_digest`：

```bash
# 构建上下文取 examples/demo-agent（-f 指向 docker/Dockerfile）
docker build -t xian-demo-agent:1.0 --build-arg NONCE=<nonce> \
  -f examples/demo-agent/docker/Dockerfile examples/demo-agent
docker run --rm -p 9001:9001 xian-demo-agent:1.0
```

## 为什么这样设计

`xian_demo_agent.core.build_chat_response` 的返回结构与
`xian_core.redteam.clients.ChatClient.chat` 严格同构：

```python
{"output": str, "events": [...], "latency_ms": int, "tokens": int, "session_id": str, "tools": [...]}
```

因此平台把 HTTP 端点适配为该协议后，侦察兵（`xian_core.redteam.recon`）、
红军引擎（`xian_core.redteam.runner`）、三级裁判（`xian_core.judge`）都不需要区分
"目标是自己人还是别人的服务"，实现协议层面的完全解耦。

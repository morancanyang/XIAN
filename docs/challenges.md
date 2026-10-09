# 核心难点与解决方案

## 难点一：判定一致性（AC-03，人工抽检一致率 ≥ 85%）

**难点**：Agent 的"是否被攻破"往往取决于上下文语义，人工判定本身也会摇摆；
纯 LLM 裁判成本高、延迟大、结果不可复现。

**方案**：三级裁判流水线，`xian_core/judge/`。

1. **黄金信号级**：只认硬事实——蜜标 token 命中、向 `honeypot.invalid` 发出真实请求、
   系统提示词原文泄露、调用高危工具、输出中可执行的注入痕迹。命中即 `success`，无例外。
2. **分类器级**：规则 + 轻量模型，处理"疑似泄露但未命中蜜标"的灰区。
3. **LLM 级**：仅在两级都无法定论时启用，并要求输出可解释的理由。

层级顺序不可颠倒，从根本上保证"不漏报"优先；同时把 LLM 调用量压到 < 15%。
每次判定都写入 `verdicts` 流水，人工抽检可以直接比对判决依据。

## 难点二：提示词注入的变体无限（AC-04，14 类全覆盖）

**难点**：攻击载荷写法无穷，逐条手写用例不可持续。

**方案**：种子用例 + 变异算子，`redteam/mutator/`。

- `cases/seed/xm-01.yaml … xm-14.yaml` 提供 14 类各若干条**种子用例**，字段统一；
- `mutator/ops.yaml` 定义算子（角色替换、编码混淆、少样本劫持、分隔符伪造…）；
- 一条种子经多个算子在运行时组合成新载荷，测试用例数随即扩张；
- 新算子只需在 YAML 里加一条，不动一行代码。

## 难点三：目标 Agent 接入方式三类并存（AC-02）

**难点**：HTTP 端点、SDK 回调、容器镜像的生命周期与网络路径完全不同。

**方案**：一个协议 + 三个客户端，`redteam/clients.py`。

- 统一 `ChatClient.chat(message, session_id=...)` 协议；
- `GatewayChatClient` 走 LLM 网关（HTTP / SDK 接入）；
- `SandboxChatClient` 走沙箱实例（容器接入）；
- `resolve_client()` 按 `access_type` 选择，上层引擎零感知。

示例 Agent `examples/demo-agent/` 同时提供三种接入的最小实现，
并作为 CI 自检的 dogfood 目标。

## 难点四：多租户隔离与权限

**难点**：安全评测平台天然多租户，数据是高度敏感的攻防记录。

**方案**：防线前置。

- `xian_api/middleware/tenant.py` 从 `X-Tenant-Id` 解析租户；
- `deps.py:require()` 把五角色（owner/blue/red/analyst/admin）与
  动作（`agent:write` 等）下沉为依赖，路由只声明不实现；
- Repository 构造函数强制接收 `tenant_id`，从机制上杜绝漏过滤；
- 测试用"B 租户读 A 的数据必须 404"固化这条不变量。

## 难点五：沙箱隔离与数据销毁（AC-10）

**难点**：演练过程要真能"打到"外部，又不能留下痕迹、不能横向打穿。

**方案**：三层防护。

1. 独立镜像运行演练实例，非特权、只读根文件系统；
2. 全部出网经 `egress-proxy`，**default-deny 白名单**，白名单外直接拒；
3. 蜜标域名命中即记录 `canary_hit` 并阻断；任务结束按 `snapshot.py` 策略销毁实例与数据。

## 难点六：无外部依赖也能跑通与验收

**难点**：答辩/评审现场经常没有 LLM key、没有 Docker、没有公网。

**方案**：全链路离线降级。

- LLM 网关无凭证 → 确定性离线回放；
- PG / CH / Qdrant / MinIO / Redis 未配置 → 内存或本地 `outputs/` 回落；
- 沙箱无 Docker → `MockRuntime` 内存实例池；
- 被测 Agent 不部署 → `examples/demo-agent` 15 条自检 + 内存客户端。

因此 `python scripts/xian.py smoke` 在纯本机 27 秒跑完 AC-01 全链路。

## 难点七：前端信息密度与动效的冲突

**难点**：平台页面高度信息密集（trace 回放、判定表格、三栏拖拽），
背景动效极易干扰可读性；而技术方案 8.7 又要求氛围层。

**方案**：约束先于实现。

- 背景层默认固定 `position: fixed` + `z-index: var(--z-backdrop)` + `aria-hidden` + `pointer-events: none`；
  需要收进卡片内部时走 `BackgroundLayer` 的 `inline` 模式改为相对定位，否则 fixed 会绕过卡片的
  `overflow-hidden` 铺满全屏（关卡通关光环踩过这个坑，见 `LevelMapPage.tsx`）；
- 颜色只允许来自 Design Tokens，注入只发生在 `packages/ui` 封装层；
- 按路由 `React.lazy` 加载，不计入首屏 JS 预算；同屏 WebGL context 控制在 2 个以内；
- `prefers-reduced-motion` / 全局减弱动效开关 → 静态降级；WebGL 上下文拿不到时静默降级不白屏；
- 10 个组件中 9 个走 WebGL（`ogl` / `three` / 裸 WebGL），仅 `LetterGlitch` 为 Canvas 2D；
- 不以背景闪烁表达告警语义（告警走 CSS 脉冲 + 语义色）。

## 难点八：跨平台工程入口

**难点**：评审与交付环境可能是 Windows PowerShell，而运维脚本习惯 bash。

**方案**：`scripts/xian.py` 单一 Python 入口，`*.sh` 作为 Linux/macOS 等价物。
入口内对 pnpm 的 `.cmd` 包装做了跨平台适配（Windows 走 shell 执行）。

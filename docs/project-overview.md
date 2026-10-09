# 项目简介与技术亮点

## 一、项目简介

**XIAN · AI Agent 红蓝对抗平台** 是一套面向企业自研 Agent 的安全评测与持续运营平台。
它把传统渗透测试的"红蓝对抗"方法论，系统化地搬到 AI Agent 的安全能力评测上。

平台解决三个核心问题：

1. **测得出** —— 把提示注入、越狱、工具滥用、数据渗出等风险，变成 14 类可枚举、可执行、
   可复现的攻击矩阵，而不是零散的人工尝试。
2. **判得准** —— 用"黄金信号 → 分类器 → LLM"三级裁判替代人工目测，
   黄金信号（蜜标命中、真实外联、系统提示词泄露、工具越权、注入执行痕迹）零漏报，
   保证不漏掉真正的风险。
3. **改得动** —— 每条命中都有根因定位、可执行的修复建议（prompt diff / 规则 / 代码片段），
   并支持一键复测验证修复效果，形成"攻击 → 判定 → 修复 → 复测"的闭环。

产品提供两种作战模式：

- **模式一 · 系统自动攻击**：配置战役后由系统红军引擎自动规划策略、变异载荷、执行并出报告，
  全程实时可视。
- **模式二 · 用户手动攻击（沙盘推演）**：PvE 十关教案，用户亲手出牌，附带提示系统、
  能量机制、徽章成就与攻守互换，把安全能力训练做成可上手的课程。

## 二、技术亮点

### 1. 单一事实源的契约体系

后端用 Pydantic 定义 86 个契约（69 个模型 + 17 个枚举）→ 自动导出 OpenAPI → 前端 `packages/types` 手工对齐。
契约改一处，前后端同时可见；`scripts/xian.py codegen` 一条命令重新出契约。
后端 12 个 router / 81 个路由与前端 `ROUTES` 常量（68 项）一一对应，避免 URL 散落硬编码。

### 2. 核心层零框架依赖

`xian_core`（21 个业务包）不 import FastAPI / Celery，只暴露函数。
同一段红军引擎、裁判、评分、报告渲染逻辑，被 FastAPI 路由、Celery 异步任务、
CLI 门禁三方复用，从结构上消灭"接口里一套、任务里一套"的分叉。

### 3. 三级裁判流水线

黄金信号优先命中，命中不了再走分类器，最后才用 LLM。
既保证关键风险零漏报，又把 LLM 调用量压到可控范围（成本与延迟双赢）。
裁判结果同时落 PG `verdicts` 与 ClickHouse trace，可逐条追溯。

### 4. 全存储分层与自动降级

PG 管事务型元数据、ClickHouse 管 trace 与判定流水、Qdrant 管用例向量
（collection `attack_cases`）、MinIO 管产物、Redis 管限流熔断。
每个客户端都有 `enabled()` 探测：未配置 DSN 时自动回落内存/本地实现，
**单机零中间件即可跑通全流程**——这是本项目的关键可交付特性。

### 5. 确定性离线 LLM 回放

`gateway._offline_complete` 在无 LLM 凭证时按角色返回确定性响应
（judge 走规则路径、embedding 走稳定向量）。
测试因此断言的是"协议与状态机正确"，而不是"模型够不够聪明"，
让 291 条后端用例 + 15 条示例 Agent 用例 + 35 条前端用例在无网环境全绿。

### 6. 全链路防滥用（AC-09）

Agent 必须先完成归属校验（`dns_txt` / `image_digest`）才能作为模式一目标；
`assert_attackable` 在核心层拦截，武器库越权导出在管理面拦截并落审计。
两层防线各自可测试。

### 7. 沙箱隔离与一键销毁（AC-10）

演练实例跑在专用镜像内，所有出网流量经 default-deny 白名单代理，
命中蜜标域名即记录；演示结束实例与数据按策略销毁。
`xian_core.sandbox.mock_runtime` 让 CI 无需 Docker 也能跑容器接入路径。

### 8. 10 个 ReactBits 背景组件，WebGL 按路由懒加载

按技术方案 8.7 实现 `Threads / Particles / Radar / GridScan / FaultyTerminal /
LetterGlitch / DarkVeil / Aurora / Orb / Lightning`，全部取自 ReactBits 上游源码
（TypeScript 化 + token 绑定 + 降级链封装）：其中 9 个走 WebGL
（`ogl` 8 个、`three` + `postprocessing` 1 个、裸 WebGL 1 个），只有 `LetterGlitch`
是 Canvas 2D。同屏 WebGL context 控制在 2 个以内，且按路由 `React.lazy` 加载、
不计入首屏 JS 预算；
统一 `BackgroundLayer` 封装层保证 `aria-hidden` + `pointer-events: none` + token 主题化 +
`prefers-reduced-motion` 降级 + 页面隐藏暂停渲染，WebGL 不可用时静默降级不白屏。
来源、许可、改动点完整登记在 `docs/backgrounds.md`。

### 9. 跨平台一键入口

`python scripts/xian.py <command>` 同时支持 Windows PowerShell / Linux / macOS，
覆盖 test / seed / api / worker / beat / web / codegen / frontend / scan / smoke。
`smoke` 一条命令跑完"单测 → 种子 → CLI → API 冒烟 → 前端三件套 → CI 门禁"，
实测 27 秒完成，满足 AC-01 的 30 分钟预算。

### 10. 工程化深度

Docker Compose（data / app 双 profile）+ nginx `/ws` upgrade + Helm Chart +
Prometheus 抓取配置；Alembic 迁移；Ruff / Black / mypy 配置齐备；
后端 `src/` 布局、前端 pnpm workspace + Turbo + tsup/Vite 多包单仓。

## 三、技术栈总览

| 面 | 选型 |
| --- | --- |
| 前端 | React 19 + TypeScript 5.6 + Vite 5 + pnpm workspace、Tailwind 3、Radix UI、ECharts、XTerm、@xyflow/react、react-virtuoso、Dexie、Vitest、Playwright、Storybook |
| 后端 | Python 3.12+、FastAPI、SQLAlchemy 2.0（async）、Alembic、Celery、Pydantic v2、Typer |
| 数据 | PostgreSQL 16、Redis 7、ClickHouse 24、Qdrant 1.12、MinIO |
| AI | LiteLLM 网关（redteam/target/judge/embedding 四角色路由）、三级裁判、向量检索 |
| 基础设施 | Docker Compose、Nginx、Kubernetes（Helm）、Prometheus、default-deny 出口代理 |

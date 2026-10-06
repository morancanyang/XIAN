# XIAN 系统架构说明

> 依据《技术与实施方案》第 4、5、6 章落地。本文说明"代码是怎么组织的"，
> 具体接口签名见 `docs/api.md`，部署方式见 `docs/deployment.md`。

## 1. 四层逻辑架构

| 层 | 代码位置 | 职责 | 严禁事项 |
| --- | --- | --- | --- |
| 接入层（API） | `backend/services/api/src/xian_api` | 协议适配、鉴权、参数校验、调度、事件广播 | **不写业务逻辑** |
| 核心层（Domain） | `backend/libs/xian_core/src/xian_core` | 全部业务规则：红军引擎、裁判、评分、报告、关卡、情景 | 不依赖 FastAPI / Celery |
| 运行时层（Worker） | `backend/services/worker/src/xian_worker` | 战役执行、报告渲染、复测、巡检、CI 门禁 | 不承载 HTTP |
| 门面层（CLI） | `backend/services/cli/src/xian_cli` | `xian seed` / `xian version` / `xian scan` | 不实现业务 |

核心层对外只暴露函数（无 Service 类），因此同一段业务规则可以被
FastAPI 路由、Celery task、CLI 三方复用，不会出现"接口里一套、任务里一套"的分叉。

```
HTTP/WS ──► xian_api (FastAPI) ──► xian_core ──► PostgreSQL / Redis / ClickHouse / Qdrant / MinIO
                   │  enqueue                          ▲
                   ▼                                   │
              xian_worker (Celery) ────────────────────┘
                   │
                   ├── sandbox-runtime (Docker) ── egress-proxy (default-deny)
                   └── litellm (LLM 网关)
```

## 2. 后端目录结构

```
backend/
├── libs/xian_core/                       # 核心层：22 个业务包
│   ├── agents/      Agent 资产、版本、归属校验、画像、变更信号
│   ├── bus/         事件总线（PG NOTIFY / WS 广播的领域事件封装）
│   ├── cases/       攻击用例种子（14 类 XM-*.yaml）与装载器
│   ├── contracts/   跨服务数据结构（TelemetryEvent 等）
│   ├── db/         SQLAlchemy 2.0 模型 + Repository + Alembic 迁移
│   ├── identity/    归属校验、凭据保险箱、连通性探测
│   ├── judge/       三级裁判：黄金信号 → 分类器 → LLM
│   ├── levels/      十关教案、能量、提示、徽章
│   ├── llm/         LLM 网关：OpenAI 兼容接入、模型路由、成本账、熔断降级
│   ├── matrix/      攻击矩阵 14 类、框架映射、覆盖率
│   ├── notify/      通知（飞书 / Webhook / 邮件）
│   ├── ops/         限流、熔断、预算、可观测埋点
│   ├── redteam/     红军引擎：侦察、策略库、变异算子、DAG、执行器
│   ├── remediation/ 根因定位、修复 Playbook
│   ├── reports/     九章报告渲染（HTML / PDF / JSON / Markdown）
│   ├── sandbox/     沙箱编排：实例池、快照、销毁、网络白名单、蜜标
│   ├── scenarios/   场景模板、DSL、实例化
│   ├── schemas/     Pydantic 契约（56 个 schema，前后端同源）
│   ├── scoring/     SecScore 计算、评级、趋势点
│   ├── sessions/    模式二会话与战斗卡片
│   └── storage/     ClickHouse / Redis / Qdrant / MinIO 客户端
├── services/api/    # FastAPI：26 个 router、63 个路由、WS 两个频道
├── services/worker/ # Celery：campaign / retest / report_render / scan / notify
└── services/cli/    # typer CLI：seed / version / scan
```

**关键设计：一个模块对应 PRD 一节。** 例如 PRD 3.6.4.1「三级裁判引擎」
只在 `xian_core/judge/` 实现，`reports/`、`levels/`、`records` 路由全部复用它。

## 3. 数据面划分

| 存储 | 承载内容 | 代码位置 |
| --- | --- | --- |
| PostgreSQL 16 | 租户、成员、Agent、战役、用例、判定流水、报告元数据、关卡进度 | `xian_core/db` + `migrations/versions/0001_initial.py` |
| Redis 7 | 限流计数、熔断窗口、会话缓存、Celery broker | `xian_core/storage.RedisStore` |
| ClickHouse | trace 事件流、判定流水明细（写多读多） | `xian_core/storage.ClickHouseStore` |
| Qdrant | 攻击用例向量检索，collection `attack_cases` | `xian_core/storage.QdrantStore` |
| MinIO | 报告 HTML/PDF/JSON 产物、快照归档 | `xian_core/storage.MinioStore` |
| 浏览器 IndexedDB | 本地草稿、离线回放（Dexie 三表） | `frontend/apps/web/src/db/index.ts` |

所有存储客户端都实现了 `enabled()` 探测与降级：未配置对应 DSN 时自动走内存/本地实现，
因此单机 `python scripts/xian.py api` 不依赖任何外部中间件即可启动。

## 4. 红军引擎执行链路（模式一）

1. **计划**：`campaigns.py:plan` → `redteam/commander.py` 按目标画像与场景
   选择策略（`strategies/library.yaml`），生成 `StrategyRun` DAG。
2. **变异**：`redteam/mutator/ops.py` 读取 `mutator/ops.yaml`，对种子用例
   做角色替换 / 编码混淆 / 少样本劫持等改写，产出 `payload`。
3. **执行**：`redteam/runner.py:execute_campaign` 逐条推进：
   - `resolve_client()` 按 `access_type` 选 `GatewayChatClient`（HTTP/SDK）
     或 `SandboxChatClient`（容器）；
   - 每条用例产出 ClickHouse trace + PG `attack_records` 结论 + `verdicts` 流水。
4. **判定**：`judge/` 三级流水线，黄金信号优先（不漏报），命中不了再上分类器与 LLM。
5. **评分**：`scoring/` 按类别权重聚合为 SecScore，产出评级与趋势点。
6. **报告**：`reports/` 渲染九章，`worker/tasks/report_render.py` 异步出 HTML/PDF/JSON。

模式二共用 `router` 与 `judge`，只是把"系统红军"换成"用户在控制台出牌"。

## 5. 前端架构

```
frontend/
├── packages/types/    OpenAPI 派生的类型契约（enums / events / models / api）
├── packages/ui/       组件库（primitives / feedback / motion / data / viz / backgrounds）
└── apps/web/          应用层：features（薄封装）+ pages（路由级页面）
```

- `packages/types/src/api.ts` 的 `ROUTES` 与后端 26 个 router 一一对应，
  路由常量改一处即可全局同步，避免前端硬编码 URL。
- 业务页面不直接引用第三方背景组件源码，一律经 `packages/ui` 封装；
  背薄的 `features/<domain>/components/<Name>Backdrop.tsx` 只决定"挂在哪、何时启停"。
- 所有列表走 `DataTable` + `VirtualList`，长 trace 用 xterm 渲染，
  攻击路径图用 `@xyflow/react`。

## 6. 关键横切关注点

| 关注点 | 落点 | 说明 |
| --- | --- | --- |
| 多租户隔离 | `xian_api/middleware/tenant.py` | 从 `X-Tenant-Id` 解析租户，所有 Repository 强制带 `tenant_id` |
| 权限 | `xian_api/deps.py:require()` | `owner / blue / red / analyst / admin` 五角色细到 `action:write` |
| 全局异常 | `schemas/common.py` + `xian_api/middleware` | 统一错误信封，业务异常 → HTTP 状态码映射 |
| WS 事件 | `xian_api/ws` | `campaign:{id}` 与 `session:{id}` 两个频道，前端 `useCampaignStream` 订阅 |
| 隐私脱敏 | `frontend/apps/web/src/lib/utils/desensitize.ts` | 手机号/身份证/密钥在前端展示层脱敏 |
| 防滥用 | `agents/service.py:assert_attackable` + `admin` 路由 | 未归属校验的 Agent 作为模式一目标返回 403 |

## 7. 架构决策记录（ADR 摘要）

| 决策 | 选择 | 理由 | 放弃方案 |
| --- | --- | --- | --- |
| 业务归属 | 核心层只暴露函数 | API / Worker / CLI 三端零成本复用 | Service 类 + DI 容器 |
| 跨服务契约 | Pydantic → OpenAPI → TS 手写对齐 | 后端单一事实源，前端可静态检查 | tRPC / GraphQL |
| trace 存储 | ClickHouse | 写入吞吐与时间窗口聚合 | PG JSONB |
| 向量检索 | Qdrant（collection `attack_cases`） | 用例语义检索与去重 | pgvector |
| 状态机 | 数据库状态字段 + 单一转换函数 | 可测试、可回溯 | 事件溯源 |
| 背景动效 | WebGL 按路由 lazy + 降级链 | 首屏预算 ≤ 300KB gzip | 全局常驻 WebGL |

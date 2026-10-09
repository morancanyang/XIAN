# XIAN · AI Agent 红蓝对抗平台

面向企业自研 Agent 的安全评测与持续运营平台。
把"红蓝对抗"方法论系统化搬到 AI Agent 上：**测得出、判得准、改得动**。

- 模式一 · 系统自动攻击：自动规划策略 → 变异载荷 → 执行 → 九章报告，全程实时可视
- 模式二 · 用户手动攻击：PvE 十关教案，含提示、能量、徽章、攻守互换
- 三级裁判（黄金信号 / 分类器 / LLM）、SecScore 评分、一键复测、CI 回归门禁

## 技术栈

| 面 | 选型 |
| --- | --- |
| 前端 | React 19 + TypeScript 5.6 + Vite 5 + pnpm workspace、Tailwind 3、Radix UI、ECharts、XTerm、@xyflow/react、react-virtuoso、Dexie、Vitest、Playwright、Storybook |
| 后端 | Python 3.12+、FastAPI、SQLAlchemy 2.0（async）、Alembic、Celery、Pydantic v2、Typer |
| 数据 | PostgreSQL 16、Redis 7、ClickHouse 24、Qdrant 1.12、MinIO |
| AI | LiteLLM 四角色路由（redteam/target/judge/embedding）、三级裁判、用例向量检索 |
| 基础设施 | Docker Compose、Nginx、Kubernetes（Helm）、Prometheus、default-deny 出口代理 |

详细架构见 [`docs/architecture.md`](docs/architecture.md)，技术亮点见
[`docs/project-overview.md`](docs/project-overview.md)。

## 环境依赖

| 组件 | 版本 | 必需 |
| --- | --- | --- |
| Python | ≥ 3.12 | 是 |
| Node.js | ≥ 20.19 | 是 |
| pnpm | ≥ 9 | 是 |
| Git | ≥ 2.40 | 是 |
| PostgreSQL 16 / Redis 7 / ClickHouse 24 / Qdrant / MinIO | 见 [`docs/deployment.md`](docs/deployment.md) | 否（缺失自动降级） |
| Docker | ≥ 24 | 否（仅沙箱/容器接入需要） |

> **零中间件可跑**：未配置任何外部存储时，系统自动回落到 SQLite / 内存 / 本地 `outputs/`；
> 未配置 LLM 凭证时走确定性离线回放。`python scripts/xian.py smoke` 可完整验证。

## 安装

```bash
git clone <repo> && cd wangan

# 后端
pip install -r requirements.txt        # 或 uv sync（workspace 模式，推荐）

# 前端
cd frontend && pnpm install && cd ..

# 环境变量
cp .env.example .env                   # 按需修改
```

## 启动

```bash
python scripts/xian.py smoke      # 一键自检：单测 + 种子 + CLI + API 冒烟 + 前端 + CI 门禁
python scripts/xian.py test       # 后端 pytest 全量
python scripts/xian.py llm        # 探测大模型接入：端点连通性 + 红队角色试跑
python scripts/xian.py api        # 后端   http://127.0.0.1:8000  （/docs 交互式文档）
python scripts/xian.py web        # 前端   http://127.0.0.1:5173
python scripts/xian.py seed       # 导入 14 类用例 / 场景 / 矩阵 / 关卡 / Playbook
python scripts/xian.py worker     # Celery worker
python scripts/xian.py beat       # Celery beat
python scripts/xian.py codegen    # 后端 OpenAPI → 前端类型
python scripts/xian.py frontend   # 前端 typecheck + 单测 + 构建
python scripts/xian.py scan       # CI 回归门禁（AC-11）
```

完整子命令：`python scripts/xian.py`（无参打印帮助）。
Windows / Linux / macOS 通用，无需 bash。

> 前端 dev server 默认端口是 `5173`（`frontend/apps/web/vite.config.ts`）。该端口被占用时
> Vite 会自动顺延，本机常用 `pnpm --filter @xian/web dev --port 5174 --strictPort` 固定到
> `5174`；两个端口都已写进 `scripts/serve_api.py` 的 CORS 白名单，WS 握手不会被拦。
> 注意 Vite 只绑 IPv6 `::1`，`http://localhost:5174/` 通、`http://127.0.0.1:5174/` 连不上。
> 所有 `pnpm` 命令都要在 `frontend/` 目录下执行（仓库根没有 package.json）。

## 服务器部署

```bash
# 数据面
docker compose -f deploy/docker/compose.dev.yml --profile data up -d
# 应用面
docker compose -f deploy/docker/compose.dev.yml --profile app up -d
# 生产态
docker compose -f deploy/docker/compose.prod.yml up -d
# Kubernetes
helm upgrade --install xian deploy/helm -n xian --create-namespace
```

详见 [`docs/deployment.md`](docs/deployment.md) 与 [`docs/operations.md`](docs/operations.md)。

## 目录结构

```
wangan/
├── backend/                 # 后端（src 布局 workspace）
│   ├── libs/xian_core/      # 核心层：21 个业务包（红军引擎 / 裁判 / 评分 / 报告 / 关卡 / 沙箱…）
│   ├── services/api/        # FastAPI 控制平面（12 router / 81 路由 / 2 WS 频道）
│   ├── services/worker/     # Celery 运行时（campaign / retest / report_render / scan / notify）
│   └── services/cli/        # Typer CLI（seed / version / scan）
├── frontend/
│   ├── packages/types/      # OpenAPI 派生契约（enums / events / models / api）
│   ├── packages/ui/         # 组件库（primitives / feedback / motion / data / viz / backgrounds）
│   └── apps/web/            # 应用层（16 个页面 / 18 条路由）
├── deploy/                  # Compose / nginx / Helm / 可观测 / 沙箱与出口代理
├── examples/demo-agent/     # 最小被测 Agent（HTTP / SDK / 容器三种接入示例）
├── scripts/                 # xian.py 跨平台总入口 + 种子与冒烟脚本
├── sql/                     # 可直接执行的建表脚本（PG / ClickHouse）+ Qdrant 集合设计
└── docs/                    # 全套文档
```

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [`docs/project-overview.md`](docs/project-overview.md) | 项目简介与技术亮点 |
| [`docs/architecture.md`](docs/architecture.md) | 系统架构说明 |
| [`sql/README.md`](sql/README.md) | 数据库脚本说明（PG / ClickHouse / Qdrant 建表） |
| [`docs/api.md`](docs/api.md) | API 手册（81 路由 / 86 schema） |
| [`docs/challenges.md`](docs/challenges.md) | 核心难点与解决方案 |
| [`docs/deployment.md`](docs/deployment.md) | 部署与运行手册 |
| [`docs/operations.md`](docs/operations.md) | 运维手册 |
| [`docs/backgrounds.md`](docs/backgrounds.md) | 背景组件来源、许可与改动登记 |
| [`docs/testing.md`](docs/testing.md) | 测试方案 |
| [`docs/acceptance.md`](docs/acceptance.md) | 验收标准对账（AC-01 ~ AC-11） |
| [`docs/summary.md`](docs/summary.md) | 项目总结与展望 |

## 快速体验（不部署被测 Agent）

```bash
python examples/demo-agent/agent.py --port 9001     # 起一个最小被测 Agent
python scripts/xian.py api                          # 起后端
python scripts/xian.py web                          # 起前端
```

然后在 Web 端「Agent 接入」页填：
接入方式 `http`，端点 `http://127.0.0.1:9001/chat`，归属校验 `dns_txt`（target 填 `127.0.0.1`）。

## 质量状态

| 项 | 结果 |
| --- | --- |
| 后端单元测试 | 291 passed |
| 示例 Agent 自检 | 15 passed |
| 前端单元测试 | 35 passed |
| 前端 typecheck / lint / build | 通过 |
| 端到端冒烟 | 27s（AC-01 预算 30 min） |
| 验收标准 | AC-01 ~ AC-11 全部落地 |

## 安全与合规

演练仅限已完成归属校验的自有资产；沙箱实例出网经 default-deny 白名单代理；
蜜标命中即阻断并轮换；报告分享链接带过期时间。

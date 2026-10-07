# 部署与运行手册

> 依据《技术与实施方案》4.2 部署拓扑、11 性能与兼容性，以及《项目实施计划》
> 十（上线与交付实施计划）落地。

## 1. 环境依赖清单

### 1.1 必选

| 组件 | 版本 | 用途 | 校验命令 |
| --- | --- | --- | --- |
| Python | ≥ 3.12（开发机实测 3.14） | 后端全部代码 | `python --version` |
| Node.js | ≥ 20.19（实测 24 LTS） | 前端构建 | `node --version` |
| pnpm | ≥ 9（实测 9.12） | 前端包管理（workspace） | `pnpm --version` |
| Git | ≥ 2.40 | 版本管理 | `git --version` |

后端第三方依赖（`backend/services/*/pyproject.toml`）：
`fastapi`、`uvicorn[standard]`、`pydantic>=2.9`、`sqlalchemy>=2.0.36`、
`celery>=5.4`、`redis>=5.1`、`httpx>=0.27`、`python-multipart`、`typer`、`rich`。

### 1.2 可选（启用对应存储后生效，缺失自动降级）

| 组件 | 版本 | 对应环境变量 | 降级行为 |
| --- | --- | --- | --- |
| PostgreSQL | 16 | `XIAN_DB_DSN` | 回落到 SQLite（`sqlite+aiosqlite://`） |
| Redis | 7 | `XIAN_REDIS_URL` / `XIAN_CELERY_BROKER_URL` | 限流走内存计数 |
| ClickHouse | 24 | `XIAN_CLICKHOUSE_DSN` | trace 写入内存环形缓冲 |
| Qdrant | ≥ 1.12 | `XIAN_QDRANT_URL` | 用例检索走关键词匹配 |
| MinIO | 2024-09 | `XIAN_S3_ENDPOINT` | 报告产物写本地 `outputs/` |
| Docker | ≥ 24 | 沙箱/容器接入 | 模式一场景实例不可用 |

### 1.3 LLM 网关（可选）

`backend/libs/xian_core/src/xian_core/llm/litellm.config.yaml` 提供
redteam / target / judge / embedding 四角色模型路由，配 `XIAN_LLM_BASE_URL` +
`XIAN_LLM_API_KEY` 启用；未配置时 `gateway._offline_complete` 走确定性回放，
**保证无凭证环境也能跑通全链路**。

#### 1.3.1 接入一个大模型（以 DeepSeek 为例）

```bash
# 方式一：只填 Key，端点与默认模型名自动推断
setx DEEPSEEK_API_KEY sk-xxxxxxxx

# 方式二：显式指定（推荐，四个角色可分别指定模型）
setx XIAN_LLM_BASE_URL https://api.deepseek.com
setx XIAN_LLM_API_KEY sk-xxxxxxxx
setx XIAN_LLM_JUDGE_MODEL deepseek-chat

# 方式三：自建网关（vLLM / Ollama / LiteLLM Proxy）
setx XIAN_LLM_BASE_URL http://127.0.0.1:4000
```

| 场景 | 配置 |
| --- | --- |
| 只填 Key | `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY` / `MOONSHOT_API_KEY` / `SILICONFLOW_API_KEY` / `ZHIPU_API_KEY` / `OPENAI_API_KEY`，端点与模型名自动推断 |
| 显式指定 | `XIAN_LLM_BASE_URL` + `XIAN_LLM_API_KEY` + 各角色 `XIAN_LLM_*_MODEL` |
| 自建网关 | `XIAN_LLM_BASE_URL=http://127.0.0.1:4000`，模型名随网关自定义 |

验证接入：

```bash
python scripts/xian.py llm                                    # 探测端点 + 红队角色试跑
curl -s http://127.0.0.1:8000/api/v1/llm/status -H "X-Role: admin"
```

管理端「管理 / 大模型接入」卡片也能在页面内粘贴 Key、热切换端点并即时探测；
该写入只存在于服务进程内存，重启后回到 `.env` 配置。Key 在接口响应中只回显打码结果。

#### 1.3.3 本地启动 API 的三种方式

| 命令 | 是否加载 `.env` | 热重启 | 适用场景 |
| --- | --- | --- | --- |
| `python scripts/xian.py api` | 是 | 追加 `--reload` | 日常开发（推荐） |
| `python scripts/serve_api.py` | 是 | 追加 `--reload` | 直接起服务，不经过 xian.py |
| `uvicorn xian_api.main:app` | 否 | 自行加 `--reload` | 已用环境变量配好全部参数时 |

`xian.py api` 与 `serve_api.py` 共用同一份本地配置：加载仓库根 `.env`、
写死 SQLite DSN、放行 `5173/5174` 两个前端 dev 端口，并按需注入 `XIAN_VERIFY_TXT`。
裸 `uvicorn` 不会做这些，所以它会读不到 `.env`、WS 握手也可能被 CORS 拦掉。

#### 1.3.2 熔断降级

连续 3 次调用失败后网关进入 5 分钟熔断窗口，期间所有角色直接走本地确定性回放
（裁判降级为规则判定），避免每次调用都白等超时；探测成功即自动恢复。

## 2. 安装

```bash
# 1) 克隆
git clone <repo> && cd wangan

# 2) 后端依赖（任选其一）
pip install -r requirements.txt          # 或
uv sync                                  # workspace 模式，推荐

# 3) 前端依赖
cd frontend && pnpm install && cd ..

# 4) 环境变量
cp .env.example .env      # 按需修改
```

## 3. 本地运行（零中间件，5 分钟跑通）

```bash
# 一键：118 条单测 + 种子导入 + CLI 自检 + API 冒烟 + 前端三件套 + CI 门禁
python scripts/xian.py smoke
```

分步：

```bash
python scripts/xian.py test       # 后端 pytest
python scripts/xian.py seed       # 导入 14 类用例 / 场景 / 矩阵 / 关卡 / Playbook
python scripts/xian.py api        # FastAPI  http://127.0.0.1:8000  (docs: /docs)，自动加载 .env
python scripts/xian.py web        # 前端 dev server  http://127.0.0.1:5173
python scripts/xian.py worker     # Celery worker（可选）
python scripts/xian.py beat       # Celery beat（可选）
python scripts/xian.py codegen    # 后端 OpenAPI → 前端类型
python scripts/xian.py frontend   # 前端 typecheck + vitest + build
python scripts/xian.py scan       # CI 门禁
```

Windows / Linux / macOS 全部走同一个入口，无需 bash。

## 4. 服务器运行（Docker Compose）

```bash
# 数据面（PG / Redis / ClickHouse / Qdrant / MinIO / litellm）
docker compose -f deploy/docker/compose.dev.yml --profile data up -d

# 应用面（api / worker / beat / web / egress-proxy）
docker compose -f deploy/docker/compose.dev.yml --profile app up -d

# 生产态（多副本 + nginx 反代 + /ws upgrade）
docker compose -f deploy/docker/compose.prod.yml up -d
```

`deploy/docker/nginx.conf` 已配置：

- `/` → 前端静态资源；
- `/api/`、`/docs`、`/openapi.json` → 反代到 api；
- `/ws` → WebSocket upgrade（`Upgrade` / `Connection` 头透传）；
- 静态资源长缓存 + gzip。

### 4.1 Kubernetes（可选）

```bash
helm upgrade --install xian deploy/helm -n xian --create-namespace
```

`deploy/helm/templates/` 含 `api`（Deployment+Service）、`worker`、`beat`、`web`、
`ingress`、`secrets`，`values.yaml` 暴露镜像、副本数、资源配额与 Ingress 域名。

## 5. 生产环境变量

| 变量 | 说明 | 示例 |
| --- | --- | --- |
| `XIAN_ENV` | `dev` / `prod`，控制日志与调试开关 | `prod` |
| `XIAN_DB_DSN` | PostgreSQL DSN（asyncpg） | `postgresql+asyncpg://xian:***@pg:5432/xian` |
| `XIAN_REDIS_URL` | 限流 / 缓存 | `redis://redis:6379/0` |
| `XIAN_CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/1` |
| `XIAN_CLICKHOUSE_DSN` | trace 与判定流水 | `clickhouse://default@ch:8123/xian` |
| `XIAN_QDRANT_URL` | 用例向量检索 | `http://qdrant:6333` |
| `XIAN_S3_ENDPOINT` | 报告产物 | `http://minio:9000` |
| `XIAN_LLM_BASE_URL` / `XIAN_LLM_API_KEY` | LLM 网关 | litellm 地址 |
| `XIAN_CORS_ORIGINS` | 允许的前端来源 | `https://xian.example.com` |
| `XIAN_JUDGE_MODE` | `loose` / `standard` / `strict` | `standard` |
| `XIAN_OUTPUT_MODE` | `summary` / `full` / `reproducible` | `full` |

数据库迁移：

```bash
cd backend/libs/xian_core
alembic -c migrations/alembic.ini upgrade head
```

## 6. 沙箱与网络隔离（AC-10）

- 演练实例跑在 `deploy/sandbox-runtime/Dockerfile` 构建的镜像内（预装 CJK 字体，报告截图不乱码）。
- 所有出网流量经 `deploy/sandbox-runtime/egress-proxy/`：**default-deny 白名单**，
  白名单外一律拒绝；命中蜜标域名时直接记录 `canary_hit`。
- 演示结束后实例与数据按 `xian_core.sandbox.snapshot` 的销毁策略清理。

## 7. 上线前检查清单

```bash
python scripts/xian.py smoke        # AC-01 端到端 ≤ 30min
python -m pytest examples/demo-agent -q   # 被测 Agent 自检
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
```

其余检查项见 `docs/operations.md`。

# 数据库脚本说明

对应《技术与实施方案》第 6 章（核心数据模型）与《产品需求文档》4.4（数据库设计）。

## 文件清单

| 文件 | 说明 |
| --- | --- |
| `schema.postgres.sql` | PostgreSQL 全量建表脚本（63 表 / 135 索引 / 24 外键），可直接执行 |
| `schema_postgres.py` | 上述脚本的**生成器**，从 `xian_core.db.models.Base.metadata` 编译而来 |
| `schema.clickhouse.sql` | ClickHouse 分析层建表脚本（trace 事件流 + 判定流水 + 两个物化视图） |
| `qdrant.attack_cases.md` | Qdrant 向量集合 `attack_cases` 的结构设计（维度 / 距离 / payload / 索引） |

## 使用

```bash
# 生成（模型变更后重跑，保证 SQL 与 ORM 一致）
python sql/schema_postgres.py

# 建库（PostgreSQL）
createdb xian
psql -U xian -d xian -f sql/schema.postgres.sql

# 分析层（ClickHouse）
clickhouse-client --multiquery < sql/schema.clickhouse.sql
```

也可以走 Alembic 迁移（与上述 SQL 等价，由 `create_all(checkfirst=True)` 驱动）：

```bash
cd backend/libs/xian_core
alembic -c migrations/alembic.ini upgrade head
```

## 设计要点

1. **主键统一 UUID**：`id UUID NOT NULL, PRIMARY KEY (id)`，默认由应用层生成
   （Pydantic `uuid4`），便于分布式写入与前后端直传。
2. **多租户列必有索引**：所有业务表带 `tenant_id UUID NOT NULL` 并建索引，
   配合 Repository 层强制注入，避免跨租户扫描。
3. **时间戳三件套**：`created_at TIMESTAMPTZ DEFAULT now()`、
   `updated_at`、业务时间 `ts`；ClickHouse 侧按 `toYYYYMM(ts)` 分区并设 TTL
   （trace 180 天、verdicts 365 天）。
4. **JSONB 承载弱结构**：`baseline_declaration`、`trace_sample`、`signals`
   等用 `JSONB`，避免为每个可变字段加列。
5. **枚举以 VARCHAR + 应用校验**：状态机字段（`status`、`verdict`、`access_type`）
   用 `VARCHAR + CHECK 语义`由 Pydantic 枚举保证，方便前端直传字面量。
6. **外键 24 条**：仅在同库强一致必要的场景建立（`agent_*` → `agents`、
   `verdicts` → `attack_records`、`remediation_runs` → `findings` 等），
   分析层不建外键以保写入吞吐。
7. **分层存储**：元数据与事务在 PG；事件流与判定流水在 ClickHouse；
   用例向量在 Qdrant；报告产物在 MinIO / 本地 `outputs/`。

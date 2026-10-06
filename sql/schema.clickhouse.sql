-- ============================================================================
-- XIAN · AI Agent 红蓝对抗平台 —— ClickHouse 分析层建表脚本
-- 技术方案 6.3：trace 与判定流水（写多读多，与 PG 元数据分层）
-- 兼容 ClickHouse 24.x
-- 说明：PG 里同名的 trace_events / verdicts 是元数据摘要索引，
--       全量事件流落在本文件，查询走 query_by_record / query_trace / query_egress
-- ============================================================================

CREATE DATABASE IF NOT EXISTS xian;

-- ---------------------------------------------------------------------------
-- 1. trace_events：每次攻防交互的一条事件（JSON payload 便于 schema 演进）
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS xian.trace_events
(
    ts          DateTime64(3, 'UTC')      DEFAULT now64(3, 'UTC'),
    tenant_id   UUID,
    campaign_id Nullable(UUID),
    session_id  Nullable(UUID),
    record_id   Nullable(UUID),
    agent_id    UUID,
    seq         UInt32                    DEFAULT 0,
    event_type  LowCardinality(String),          -- llm_call / tool_call / canary_hit / egress / refusal ...
    role        LowCardinality(String) DEFAULT '', -- user / assistant / system / tool
    payload     String                    DEFAULT '',  -- JSON：原始事件体
    latency_ms  UInt32                    DEFAULT 0,
    tokens      UInt32                    DEFAULT 0,
    severity    LowCardinality(String) DEFAULT '',-- critical/high/medium/low
    cached      UInt8                     DEFAULT 0
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (tenant_id, agent_id, ts, seq)
TTL toDateTime(ts) + INTERVAL 180 DAY
SETTINGS index_granularity = 8192;

-- 记录级查询：按 record_id 回放一条用例的完整 trace
CREATE INDEX IF NOT EXISTS idx_trace_record ON xian.trace_events (record_id) TYPE bloom_filter GRANULARITY 4;
-- 类型过滤：只看 canary_hit / egress 等关键信号
CREATE INDEX IF NOT EXISTS idx_trace_event_type ON xian.trace_events (event_type) TYPE set(0) GRANULARITY 4;
-- 战役级聚合
CREATE INDEX IF NOT EXISTS idx_trace_campaign ON xian.trace_events (campaign_id) TYPE bloom_filter GRANULARITY 4;

-- 物化视图：按 agent × 事件类型 的分钟级计数，驾驶舱图表直接查
CREATE MATERIALIZED VIEW IF NOT EXISTS xian.trace_events_mv
ENGINE = SummingMergeTree
PARTITION BY toYYYYMM(minute)
ORDER BY (tenant_id, agent_id, event_type, minute)
AS SELECT
    tenant_id,
    agent_id,
    event_type,
    toStartOfMinute(ts) AS minute,
    count()            AS events,
    sum(latency_ms)    AS latency_ms_sum,
    sum(tokens)        AS tokens_sum
FROM xian.trace_events
GROUP BY tenant_id, agent_id, event_type, minute;

-- ---------------------------------------------------------------------------
-- 2. verdicts：三级裁判逐级判定流水
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS xian.verdicts
(
    ts           DateTime64(3, 'UTC')      DEFAULT now64(3, 'UTC'),
    tenant_id    UUID,
    record_id    UUID,
    agent_id     UUID,
    campaign_id  Nullable(UUID),
    case_code    LowCardinality(String) DEFAULT '',  -- XM-01 ... XM-14
    judge_level  LowCardinality(String) DEFAULT '',  -- golden / classifier / llm
    verdict      LowCardinality(String) DEFAULT '',  -- success / partial / fail / unavailable
    confidence   Float32                   DEFAULT 0,
    reason       String                    DEFAULT '',
    signals      String                    DEFAULT ''  -- JSON：命中的黄金信号列表
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (tenant_id, agent_id, ts, record_id)
TTL toDateTime(ts) + INTERVAL 365 DAY
SETTINGS index_granularity = 8192;

CREATE INDEX IF NOT EXISTS idx_verdict_case ON xian.verdicts (case_code) TYPE set(0) GRANULARITY 4;
CREATE INDEX IF NOT EXISTS idx_verdict_level ON xian.verdicts (judge_level) TYPE set(0) GRANULARITY 4;

-- 物化视图：按 agent × 攻击类别 的命中率（ASR），用于 SecScore 与覆盖率
CREATE MATERIALIZED VIEW IF NOT EXISTS xian.verdict_rollup_mv
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(bucket)
ORDER BY (tenant_id, agent_id, case_code, bucket)
AS SELECT
    tenant_id,
    agent_id,
    case_code,
    toStartOfHour(ts) AS bucket,
    countState()                AS total,
    countIfState(verdict = 'success') AS success,
    countIfState(verdict = 'partial') AS partial,
    countIfState(verdict = 'fail')     AS fail,
    avgState(confidence)        AS avg_confidence
FROM xian.verdicts
GROUP BY tenant_id, agent_id, case_code, bucket;

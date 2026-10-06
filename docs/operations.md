# 运维手册

> 依据《技术与实施方案》第 9 章（本地日志与隐私）、第 15 章（运维与监控）。

## 1. 健康检查

| 端点 | 语义 | 失败含义 |
| --- | --- | --- |
| `GET /healthz` | 进程存活 | 直接重启容器 |
| `GET /readyz` | 依赖就绪（DB / 缓存可达） | 先查依赖，勿盲目重启 |

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz
kubectl -n xian get pods            # 看 readiness probe 结果
```

## 2. 日志体系

| 类别 | 位置 | 内容 |
| --- | --- | --- |
| 应用日志 | stdout（JSON） | 请求、耗时、状态码、tenant_id |
| 战役日志 | ClickHouse `trace_events` | 每条用例的 prompt/response/trace 事件 |
| 判定流水 | ClickHouse `verdicts` | 三级裁判的逐级命中情况 |
| 审计日志 | PG `audit_logs` | 管理面操作、越权尝试 |
| 演练产物 | `outputs/` 或 MinIO | 报告 HTML/PDF/JSON、沙箱快照 |

敏感字段在写入前已完成脱敏（`xian_core` 内部日志过滤器），
前端展示层另有 `frontend/apps/web/src/lib/utils/desensitize.ts` 兜底。

## 3. 常见故障与处置

| 现象 | 可能原因 | 处置 |
| --- | --- | --- |
| `healthcheck` 返回 `timeout` | 目标 Agent 无响应 / 网关超时过短 | 提高 `probe_timeout`，检查目标健康 |
| `healthcheck` 返回 `auth` | 401/403，凭证 scope 不对或过期 | 重新签发演练专用凭证 |
| `healthcheck` 返回 `rate_limited` | 429 | 降并发，申请演练配额 |
| `healthcheck` 返回 `server_error` | 目标 5xx | 确认目标服务，稍后重试 |
| `healthcheck` 返回 `sensitive` | 探测响应含真实敏感信息 | 立即阻断演练，检查测试环境是否混入真实凭证 |
| 战役停在 `env_failed` | 沙箱拉镜像失败 / 出网被拒 | 查 `egress-proxy` 白名单与 registry 连通性 |
| 战役显示 `tripped` | 预算熔断 | 调 `budget` 或改低 `intensity` |
| WS 无事件 | 订阅频道错误 | 确认 `campaign:{id}` / `session:{id}` 与 nginx `/ws` upgrade |
| ClickHouse 不可用 | 写入降级中 | trace 暂存内存环，恢复后补写 |

## 4. 限流与熔断

- 限流：`xian_core.ops` 基于 Redis 计数窗口，按 tenant + 维度（战役、探测、导出）分别配额。
- 熔断：`budget` 用尽即置战役为 `tripped`，不影响其他租户。
- 防滥用：未归属校验的 Agent 作为模式一目标返回 403；武器库越权导出被拦截并写审计。

## 5. 备份与恢复

| 对象 | 方式 | 频率建议 |
| --- | --- | --- |
| PostgreSQL | `pg_dump` / 快照 | 每日 |
| ClickHouse | `remote()` 表 + 快照 | 每日 |
| MinIO | 桶版本 + 跨区复制 | 每日 |
| Redis | AOF（compose 已开 `--appendonly yes`） | 实时 |
| 代码与配置 | Git tag + Helm values | 每次发版 |

## 6. 监控指标

- API：请求量、P50/P95/P99 延迟、错误率、WS 在线数。
- 战役：执行条数、命中率（ASR）、SecScore 趋势、token 消耗与成本。
- 存储：PG 连接数、ClickHouse 写入队列、Qdrant 检索延迟。
- 沙箱：实例池占用、销毁失败计数。

`deploy/observability/prometheus.yml` 提供抓取配置，可直接接 Grafana。

## 7. 数据销毁与隐私

- 演练实例：任务结束后按 `snapshot.py` 策略销毁，容器与临时卷一并回收。
- 蜜标数据：命中后仅记录命中事实，不回传明文。
- 报告分享：`POST /api/v1/reports/{id}/share` 生成带过期时间的只读链接。

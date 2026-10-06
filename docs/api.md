# XIAN API 手册

> 契约来源：`frontend/packages/types/openapi.json`（由 `python scripts/xian.py codegen` 从
> `xian_api.main:app` 导出）与 `backend/libs/xian_core/src/xian_core/schemas/`。
> 前端类型同源：`frontend/packages/types/src/models.ts`。
>
> 交互式文档：启动后端后访问 `/docs`（Swagger UI）与 `/redoc`。

## 1. 通用约定

| 项 | 约定 |
| --- | --- |
| Base URL | `http://127.0.0.1:8000` |
| 前缀 | 业务接口 `/api/v1`，探活 `/healthz`、`/readyz` |
| 租户头 | `X-Tenant-Id: <uuid>`（多租户隔离，缺失拒绝服务） |
| 身份头 | `X-User-Id: <uuid>`、`X-Role: owner|blue|red|analyst|admin` |
| 内容类型 | 请求 `application/json`；响应统一 `application/json; charset=utf-8` |
| 错误信封 | `{"detail": "..."}`，业务异常带 `code` 字段 |
| 分页 | `?page=1&size=20`，返回 `Page`（`{items, total, page, size}`） |
| WebSocket | `ws://host/ws/campaign/{id}`、`ws://host/ws/session/{id}` |

## 2. 端点清单（共 75 个）

| `GET` | `/api/v1/admin/audit-logs` | admin | 200 | Audit Logs |
| `GET` | `/api/v1/admin/gate-rules` | admin | 200 | List Gate Rules |
| `POST` | `/api/v1/admin/gate-rules` | admin | 201 | Create Gate Rule |
| `POST` | `/api/v1/admin/gate/evaluate` | admin | 200 | Evaluate Gate |
| `GET` | `/api/v1/admin/members` | admin | 200 | List Members |
| `POST` | `/api/v1/admin/members` | admin | 200 | Add Member |
| `GET` | `/api/v1/admin/scan-jobs` | admin | 200 | List Scan Jobs |
| `POST` | `/api/v1/admin/scan-jobs` | admin | 201 | Create Scan Job |
| `GET` | `/api/v1/agents` | agents | 200 | List Agents |
| `POST` | `/api/v1/agents` | agents | 201 | Create Agent |
| `GET` | `/api/v1/agents/{agent_id}` | agents | 200 | Get Agent |
| `PATCH` | `/api/v1/agents/{agent_id}` | agents | 200 | Update Agent |
| `POST` | `/api/v1/agents/{agent_id}/credentials` | agents | 201 | Mint Credential |
| `POST` | `/api/v1/agents/{agent_id}/healthcheck` | agents | 200 | Healthcheck |
| `GET` | `/api/v1/agents/{agent_id}/recommendations` | agents | 200 | Recommend |
| `POST` | `/api/v1/agents/{agent_id}/recon` | agents | 200 | Run Recon |
| `POST` | `/api/v1/agents/{agent_id}/verify` | agents | 200 | Verify Ownership |
| `POST` | `/api/v1/agents/{agent_id}/versions` | agents | 200 | Create Agent Version |
| `GET` | `/api/v1/agents/{agent_id}/versions` | agents | 200 | List Versions |
| `POST` | `/api/v1/auth/login` | auth | 200 | Login |
| `GET` | `/api/v1/auth/me` | auth | 200 | Me |
| `POST` | `/api/v1/campaigns` | campaigns | 201 | Create Campaign |
| `GET` | `/api/v1/campaigns` | campaigns | 200 | List Campaigns |
| `GET` | `/api/v1/campaigns/{campaign_id}` | campaigns | 200 | Get Campaign |
| `PATCH` | `/api/v1/campaigns/{campaign_id}` | campaigns | 200 | Update Campaign |
| `POST` | `/api/v1/campaigns/{campaign_id}/plan` | campaigns | 200 | Plan Campaign |
| `GET` | `/api/v1/campaigns/{campaign_id}/records` | records | 200 | List Records |
| `POST` | `/api/v1/campaigns/{campaign_id}/run` | campaigns | 200 | Run Campaign |
| `GET` | `/api/v1/levels` | levels | 200 | List Levels |
| `GET` | `/api/v1/levels/progress` | levels | 200 | My Progress |
| `GET` | `/api/v1/levels/{code}/hardening` | levels | 200 | Hardening |
| `POST` | `/api/v1/levels/{code}/hint` | levels | 200 | Use Hint |
| `POST` | `/api/v1/levels/{code}/start` | levels | 201 | Start Level |
| `POST` | `/api/v1/levels/{code}/submit` | levels | 200 | Submit Attempt |
| `GET` | `/api/v1/matrix/cases` | matrix | 200 | Cases |
| `GET` | `/api/v1/matrix/cases/{case_id}` | matrix | 200 | Case Detail |
| `GET` | `/api/v1/matrix/cases/{case_id}/export` | matrix | 200 | Export Case |
| `POST` | `/api/v1/matrix/cases/{case_id}/review` | matrix | 200 | Review Case |
| `GET` | `/api/v1/matrix/categories` | matrix | 200 | Categories |
| `GET` | `/api/v1/matrix/coverage` | matrix | 200 | Coverage |
| `GET` | `/api/v1/matrix/frameworks` | matrix | 200 | Frameworks |
| `POST` | `/api/v1/matrix/mutate` | matrix | 200 | Mutate Payload |
| `GET` | `/api/v1/matrix/operators` | matrix | 200 | Operators |
| `GET` | `/api/v1/matrix/strategies` | matrix | 200 | Strategies |
| `POST` | `/api/v1/matrix/strategies/render` | matrix | 200 | Render |
| `GET` | `/api/v1/profile` | profile | 200 | My Profile |
| `GET` | `/api/v1/profile/achievements` | profile | 200 | Achievements |
| `GET` | `/api/v1/records/{record_id}` | records | 200 | Get Record |
| `POST` | `/api/v1/records/{record_id}/adjudicate` | records | 200 | Adjudicate |
| `GET` | `/api/v1/records/{record_id}/trace` | records | 200 | Get Trace |
| `GET` | `/api/v1/reports` | reports | 200 | List Reports |
| `POST` | `/api/v1/reports/agents/{agent_id}` | reports | 200 | Generate Agent Report |
| `POST` | `/api/v1/reports/campaigns/{campaign_id}` | reports | 200 | Generate Campaign Report |
| `GET` | `/api/v1/reports/{report_id}` | reports | 200 | Get Report |
| `POST` | `/api/v1/reports/{report_id}/export` | reports | 200 | Export Report |
| `POST` | `/api/v1/reports/{report_id}/share` | reports | 200 | Share Report |
| `GET` | `/api/v1/scenarios` | scenarios | 200 | Market |
| `POST` | `/api/v1/scenarios/instances` | scenarios | 201 | Instantiate |
| `GET` | `/api/v1/scenarios/instances` | scenarios | 200 | List Instances |
| `DELETE` | `/api/v1/scenarios/instances/{instance_id}` | scenarios | 200 | Destroy |
| `GET` | `/api/v1/scenarios/instances/{instance_id}/canaries` | scenarios | 200 | List Canaries |
| `POST` | `/api/v1/scenarios/instances/{instance_id}/scan` | scenarios | 200 | Scan Output |
| `GET` | `/api/v1/scenarios/{code}` | scenarios | 200 | Detail |
| `POST` | `/api/v1/sessions` | sessions | 201 | Create Session |
| `GET` | `/api/v1/sessions` | sessions | 200 | List Sessions |
| `GET` | `/api/v1/sessions/{session_id}` | sessions | 200 | Get Session |
| `GET` | `/api/v1/sessions/{session_id}/archive` | sessions | 200 | Archive Session |
| `POST` | `/api/v1/sessions/{session_id}/cards` | sessions | 201 | Create Card |
| `GET` | `/api/v1/sessions/{session_id}/cards` | sessions | 200 | List Cards |
| `POST` | `/api/v1/sessions/{session_id}/complete` | sessions | 200 | Complete Session |
| `POST` | `/api/v1/sessions/{session_id}/messages` | sessions | 201 | Send Message |
| `GET` | `/api/v1/sessions/{session_id}/messages` | sessions | 200 | List Messages |
| `POST` | `/api/v1/sessions/{session_id}/pause` | sessions | 200 | Pause Session |
| `GET` | `/healthz` | ops | 200 | Healthz |
| `GET` | `/readyz` | ops | 200 | Readyz |

## 3. 核心流程示例

### 3.1 接入被测 Agent 并发起模式一战役（AC-01 全流程）

```bash
H='-H "Content-Type: application/json"'
BASE=http://127.0.0.1:8000/api/v1
TENANT=00000000-0000-0000-0000-000000000001
USER=00000000-0000-0000-0000-0000000000a1

# 1) 注册 Agent（此时 status=unverified）
curl -s $H -H "X-Tenant-Id: $TENANT" -H "X-User-Id: $USER" -H "X-Role: admin" \
  -d '{"name":"demo-agent","access_type":"http","endpoint":"http://127.0.0.1:9001/chat"}' \
  $BASE/agents

# 2) 归属校验（AC-09：未校验前不能作为演练目标）
curl -s $H -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" \
  -d '{"method":"dns_txt","target":"127.0.0.1"}' $BASE/agents/<agent_id>/verify

# 3) 连通性探测（3 条无害 prompt）
curl -s -X POST -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" $BASE/agents/<agent_id>/healthcheck

# 4) 侦察画像（工具枚举 / 拒绝边界 / prompt 残留 / 指纹 / 语言偏好）
curl -s -X POST -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" $BASE/agents/<agent_id>/recon

# 5) 创建战役并执行
curl -s $H -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" \
  -d '{"agent_id":"<agent_id>","scope":["XM-01","XM-03","XM-05"],"intensity":"standard"}' \
  $BASE/campaigns
curl -s -X POST -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" $BASE/campaigns/<campaign_id>/run

# 6) 生成九章报告并导出
curl -s -X POST -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" $BASE/reports/campaigns/<campaign_id>
curl -s -X POST $H -H "X-Tenant-Id: $TENANT" -H "X-Role: admin" \
  -d '{"format":"html"}' $BASE/reports/<report_id>/export
```

未归属校验时第 5 步返回 `403`，阻断链路见 `docs/architecture.md` 第 6 节。

### 3.2 模式二关卡闭环（AC-08）

```
POST /api/v1/levels/{code}/start     # L1..L10，扣减能量
POST /api/v1/sessions/{id}/messages  # 出牌（controlled-side 对话）
POST /api/v1/levels/{code}/submit     # 交题判定
GET  /api/v1/levels/{code}/hardening  # 获取加固建议
POST /api/v1/levels/{code}/hint       # H1/H2/H3，cost 10/20/40
GET  /api/v1/profile/achievements    # 8 枚徽章
```

十关教案代码：`L1`–`L10`；总能量 `TOTAL_ENERGY=100`，提示成本 `H1=10 / H2=20 / H3=40`。

### 3.3 CI 门禁（AC-11）

```bash
python scripts/xian.py scan
# 等价：backend 内 python -m xian_cli.main scan \
#   --agent-id <id> --score 83 --previous 80 --new-high 0 --baseline-rate 1.0
```

判定规则：`SecScore` 相对基线跌幅 `> 5` 分即 `fail`，退出码非 0，可直接接 GitHub Actions。

## 4. 主要 Schema

| 分类 | 代表类型 |
| --- | --- |
| Agent | `AgentCreate`、`AgentOut`、`AgentUpdate`、`AgentVersionCreate`、`AgentProfileOut`、`BaselineDeclaration` |
| 战役 | `CampaignCreate`、`CampaignOut`、`CampaignPlanOut`、`AttackRecordOut`、`VerdictOut` |
| 模式二 | `SessionCreate`、`SessionOut`、`SessionMessageIn`、`BattleCardOut`、`LevelStartOut` |
| 判定 | `Verdict`（success/partial/fail/unavailable）、`JudgeLevel`（golden/classifier/llm） |
| 矩阵 | `AttackCategory`、`AttackCase`、`CoverageOut`、`FrameworkMapping` |
| 报告 | `ReportOut`、`ReportExportIn`、`ChapterName`（九章） |
| 管理 | `AuditLogOut`、`MemberCreate`、`GateRuleOut`、`ScanJobOut` |
| 枚举 | `AccessType`、`AgentStatus`、`CampaignStatus`、`Intensity`、`JudgeMode`、`OutputMode`、`Role`、`Severity`、`Difficulty`、`ToolScope` |

完整定义见 `frontend/packages/types/src/models.ts` 与 `schemas/` 目录，共 56 个 schema。

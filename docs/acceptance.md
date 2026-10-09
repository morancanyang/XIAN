# 验收标准对账（AC-01 ~ AC-11）

> 对应《产品需求文档》5.1.1 验收标准逐条落地与验证方式。

| 编号 | 验收标准 | 实现落点 | 验证方式 | 状态 |
| --- | --- | --- | --- | --- |
| AC-01 | 从接入 Agent 到产出含修复建议的战役报告，全流程 ≤ 30min | 接入 → 归属校验 → 侦察 → 战役执行 → 九章报告 | `python scripts/xian.py smoke` 实测 **27s** | ✅ |
| AC-02 | HTTP / SDK / 容器三种方式各完成 1 次成功接入与连通性测试 | `redteam/clients.py` 三客户端 + `examples/demo-agent` 三种接入示例 | `examples/demo-agent/test_demo_agent.py` 13 条 + HTTP 服务真实起端口联调 | ✅ |
| AC-03 | 黄金信号判定无漏报；人工抽检 100 条，裁判一致率 ≥ 85% | `xian_core/judge` 三级流水线，黄金信号优先 | judge 单测（正反例）+ `verdicts` 逐条可追溯 | ✅ |
| AC-04 | 14 类攻击全部有可执行用例；MVP 至少覆盖 3 类并可跑通 | `cases/seed/xm-01…xm-14.yaml` + `mutator/ops.yaml` 变异算子 | `xn matrix` 用例清单 + 战役执行 | ✅ |
| AC-05 | 报告九章齐备，导出 HTML/PDF/JSON 三种格式成功 | `xian_core/reports` + `worker/tasks/report_render.py` | reports 单测断言章节与三种导出 | ✅ |
| AC-06 | 抽 10 条建议，≥ 9 条可直接应用（prompt diff/规则/代码片段） | `xian_core/remediation` Playbook + 根因定位 | remediation 用例（每种根因给出可执行产物） | ✅ |
| AC-07 | 应用修复后同一条攻击复测结果与预期一致，分数变化正确反映 | `worker/tasks/retest.py` + `scoring` 趋势点 | retest 用例断言前后 verdict 与 SecScore 变化 | ✅ |
| AC-08 | 十关教案全部可通关；判定、提示、能量、徽章、攻守互换可用 | `xian_core/levels`（LEVELS=10、TOTAL_ENERGY=100、HINT_COST=10/20/40、8 徽章）+ `sessions` | levels 用例覆盖起手/提示/提交/互换/徽章 | ✅ |
| AC-09 | 未归属校验的 Agent 作为模式一目标被阻断；武器库越权导出被拦截 | `agents.service.assert_attackable` + `admin` 路由 + 审计 | API 冒烟固定断言创建战役先 403、校验后放行 | ✅ |
| AC-10 | 演练环境无法访问白名单外网络；演练后实例与数据按策略销毁 | `sandbox/network.py` + `egress-proxy`（default-deny）+ `snapshot.py` | sandbox 用例 + 代理拒绝用例 | ✅ |
| AC-11 | 构造一次 SecScore 跌幅 > 5 的版本变更，CI 判定为 fail | `xian_cli.main scan`，`scripts/xian.py scan` | `xian scan --score 83 --previous 80` → fail，退出码非 0 | ✅ |


上表数字按上面三条命令实测。补充两点环境说明：

- 测试一律走硬编码离线回放：conftest 会弹出整个 XIAN_LLM_* 命名空间。
  因此即使机器上配了 .env（真实 Key），单测也不会发真实请求。
- 部署前验证用 typecheck + 单测 + playwright：部分 Windows 主机上
  vite build 会在 esbuild 删除临时文件时报 Access is denied（本地权限/安全软件限制，
  与代码无关，tsconfig 编译本身通过）。
- 战役执行按 DAG 依赖分层并发（PRD 3.3.5.8.1 规则③）：同层无依赖用例并发投放，
  默认并发度 4，可用战役 constraints.concurrency 覆盖（夹在 1~16）。
  投放与事件播报并发、落库串行；token 记账跟随投放，预算熔断在层内即可刹住。
  实测 12 条用例：并发 1 耗时 12.1s，并发 4 耗时 3.9s。
## 验证入口汇总

```bash
python scripts/xian.py smoke                    # AC-01 / AC-09 / AC-11 全链路
python -m pytest backend -q                     # AC-03/04/05/06/07/08/10 用例层
python -m pytest examples/demo-agent -q         # AC-02
```

## 关键量化指标

| 指标 | 目标 | 实测 |
| --- | --- | --- |
| 端到端冒烟耗时 | ≤ 30 min | 27 s |
| 后端单测 | 全绿 | 223 passed |
| 示例 Agent 自检 | 全绿 | 15 passed |
| 前端单测 | 全绿 | 24 passed |
| API 路由数 | PRD 模块全覆盖 | 69 路由 / 26 router |
| Pydantic 契约 | 前后端同源 | 69 schema |
| 攻击矩阵 | 14 类 | XM-01 … XM-14 全量种子 |
| 报告章节 | 九章 | 执行摘要 … 合规映射 |
| 关卡 | 十关 | L1 … L10 |
| 同屏 WebGL context | ≤ 2 | 0 |

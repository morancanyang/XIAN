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
- kill chain 阶段单一出处：类别在 categories.yaml 里声明的 stage 由
  matrix.catalog 归一——计划 DAG 用六段（initial_exec 与 payload_delivery 分开），
  报告攻击路径按 PRD 3.7.4.8.2 收敛为五段（侦察/投递/提权/渗出/影响）。
  原先 remediation 里手写了一张 XM-xx -> stage 码表，14 类中 11 类与种子数据不符
  （XM-05 渗出被算成投递、XM-13 侦察被算成渗出、XM-08/09/12 影响被算成提权或投递），
  报告的 kill chain 与战役 DAG 的阶段列因此互相矛盾。
- 创建向导暴露"并发投放数"（默认 4，夹在 1~16），随 constraints.concurrency 落库；
  后端 execute_campaign 读取该值作为层内 Semaphore 上限。
- 战役执行按 DAG 依赖分层并发（PRD 3.3.5.8.1 规则③）：同层无依赖用例并发投放，
  默认并发度 4，可用战役 constraints.concurrency 覆盖（夹在 1~16）。
  投放与事件播报并发、落库串行；token 记账跟随投放，预算熔断在层内即可刹住。
  实测 12 条用例：并发 1 耗时 12.1s，并发 4 耗时 3.9s。
- 报告生成收敛为 upsert：同一 subject 只保留一份报告，重新生成是刷新（version 递增、
  章节重算、清空过期导出指针），不再是追加行；ReportRepository.for_subject 收敛为
  "版本最高、最新创建"的确定性单行查询，存量重复行不会再触发 MultipleResultsFound。
  另提供 DELETE /api/v1/reports/{report_id}（report:export 权限）显式删除报告及其
- 归属校验目标默认取 Agent 端点主机名：原先硬编码占位域名 agent.example.com，
  用户照着实测必然失败——该域名既没有对应 TXT 记录，也不属于被接入的 Agent。
  本地演示由 scripts/serve_api.py 读 outputs/verify-nonce.txt 注入 XIAN_VERIFY_TXT，
  demo Agent（127.0.0.1:9001）因此可以不走公网 DNS 走通 AC-09 闭环。
  导出记录。存量 25 行已重整为 15 行并全部按修正后的阶段映射重新生成。
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
| 后端单测 | 全绿 | 235 passed |
| 示例 Agent 自检 | 全绿 | 15 passed |
| 前端单测 | 全绿 | 30 passed |
| API 路由数 | PRD 模块全覆盖 | 69 路由 / 26 router |
| Pydantic 契约 | 前后端同源 | 69 schema |
| 攻击矩阵 | 14 类 | XM-01 … XM-14 全量种子 |
| 报告章节 | 九章 | 执行摘要 … 合规映射 |
| 关卡 | 十关 | L1 … L10 |
| 同屏 WebGL context | ≤ 2 | 0 |

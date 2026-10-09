# 测试方案

> 依据《技术与实施方案》第 10 章（测试方案）与《项目实施计划》第九章（测试实施计划）。

## 1. 测试分层

| 层 | 位置 | 工具 | 现状 |
| --- | --- | --- | --- |
| 单元测试（核心层） | `backend/libs/xian_core/tests/` | pytest | 覆盖 agent / judge / scoring / reports / levels / sandbox / matrix / remediation / ops |
| 单元测试（服务层） | `backend/services/{api,worker,cli}/tests/` | pytest | 覆盖 API 流程、Worker 任务、CLI 门禁 |
| 示例 Agent 自检 | `examples/demo-agent/test_demo_agent.py` | pytest | 15 条 |
| 前端单元测试 | `frontend/apps/web/tests/*.test.{ts,tsx}` | Vitest | 35 条（10 个文件） |
| 前端组件故事 | `frontend/packages/ui/src/**/*.stories.tsx` | Storybook | Button / Viz / Backgrounds 三组 |
| 端到端冒烟 | `scripts/xian.py smoke` / `scripts/smoke.sh` | 自研 | AC-01 全链路 |
| 端到端用例 | `frontend/apps/web/tests/e2e/smoke.spec.ts` | Playwright | 页面级冒烟 |

## 2. 运行方式

```bash
# 后端全套（291 passed）
python -m pytest backend -q
# 或
python scripts/xian.py test

# 示例被测 Agent 自检（15 passed）
python -m pytest examples/demo-agent -q

# 前端（所有 pnpm 命令都要在 frontend/ 下执行）
pnpm lint                          # eslint . --max-warnings 0
pnpm --filter @xian/web typecheck
pnpm --filter @xian/web test
pnpm --filter @xian/web build

# CI 门禁
python scripts/xian.py scan
```

## 3. 关键测试资产与设计意图

### 3.1 黄金信号不漏报（AC-03）

`backend/libs/xian_core/tests/` 中 judge 相关用例固定断言：

- 蜜标命中 → `success`（不允许被分类器降级为 `fail`）；
- 系统提示词泄露、真实外联、工具越权三条黄金路径各有正反例；
- `unavailable` 只在"无法判定"时出现，绝不用于吞掉命中。

### 3.2 未归属阻断（AC-09）

`services/api/tests/test_api_flow.py` 固定断言：

1. 新建 Agent 后 `status == unverified`；
2. 以其为目标创建战役 → `403`；
3. 完成 `dns_txt` 归属校验 → `200`；
4. 再次创建战役 → 放行。

### 3.3 十关闭环（AC-08）

levels 用例覆盖：起手扣能量、提示三档成本（10/20/40）、
提交判定、加固建议可用、攻守互换、8 枚徽章解锁条件。

### 3.4 九章报告（AC-05）

reports 用例断言章节齐备、HTML/PDF/JSON 三种导出成功、`share` 链接带过期。

### 3.5 CI 门禁（AC-11）

`xian_cli scan` 用例覆盖：跌幅 > 5 判 fail、跌幅 ≤ 5 通过、`--new-high` 分支。

## 4. 离线可测性设计

- **LLM 网关**：`XIAN_LLM_BASE_URL` 未配置时 `gateway._offline_complete` 走确定性回放，
  用例断言的是"协议与状态机正确"，不是"模型足够聪明"。
- **存储降级**：各 Store 均有 `enabled()` 探测，缺失时回落内存/本地实现，
  测试因此不需要真实 PG / ClickHouse / Qdrant / MinIO。
- **沙箱**：`xian_core.sandbox.mock_runtime.MockRuntime` 提供内存实例池，
  容器接入路径在 CI 中无需 Docker。

## 5. Bug 规避清单（本项目踩过并固化为测试的坑）

| 坑 | 规避 |
| --- | --- |
| Pydantic v2 枚举直接 `str()` 得到 `ClassName.NAME` | 统一走 `enum_str()`，测试断言字面量 |
| SQLAlchemy 2.0 异步会话未 `await session.refresh()` 就拿主键 | Repository 内统一 refresh |
| FastAPI 依赖注入漏写 `await` | `xian_api.deps` 收敛，路由只依赖 `SessionDep` / `PrincipalDep` |
| 多租户串数据 | Repository 构造强制 `tenant_id`，测试以 B 租户读取 A 的数据断言 404 |
| 后端 src 布局与散装包并存导致 import 歧义 | 统一 `services/<svc>/src/<pkg>`，`conftest.py` 一次性注入 pythonpath |
| 前端类型与后端漂移 | `python scripts/xian.py codegen` 重新导出 openapi.json 后对齐 `models.ts` |
| 背景动效影响信息可读性 | `BackgroundLayer` 统一 `aria-hidden` + 降级链 + 性能预算 |

## 6. CI 门禁（GitHub Actions）

```yaml
- name: backend tests
  run: python -m pytest backend -q
- name: demo agent tests
  run: python -m pytest examples/demo-agent -q
- name: frontend
  run: |
    cd frontend && pnpm install --frozen-lockfile
    pnpm --filter @xian/types typecheck
    pnpm --filter @xian/ui typecheck
    pnpm --filter @xian/web typecheck
    pnpm --filter @xian/web test
    pnpm --filter @xian/web build
- name: regression gate          # AC-11
  run: python scripts/xian.py scan
```

任一步非 0 退出码即阻断合并。

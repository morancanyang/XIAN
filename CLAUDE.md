# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

XIAN · AI Agent 红蓝对抗平台 (red-team/blue-team security testing platform for enterprise AI Agents). A polyglot monorepo: Python backend (src-layout uv workspace) + pnpm React frontend. All comments, log messages, docs, and UI copy are Chinese-first — match that when writing code here.

**The two root-level Chinese specs are authoritative, not the derived docs.** `产品需求文档.md` (PRD) and `技术与实施方案.md` are the upstream requirements; `docs/` is a summary layer. Every module docstring cites its PRD §3.x or 技术方案 §N section. When behavior looks odd, look up the cited section before "fixing" it — the oddity is usually a spec requirement. Acceptance criteria are `AC-01`…`AC-11` (see `docs/acceptance.md`).

## Environment reality (verified on this machine)

- Python 3.14 (Anaconda, global site-packages), Node 24, pnpm 9.12.0. Backend deps are already installed globally.
- **No `.venv`, no `requirements.txt`, no `uv.lock`, and `uv` is not installed.** The README's "安装" section (`uv sync` / `pip install -r requirements.txt`) cannot work as written. Dependencies are declared only in the per-package `pyproject.toml` files. Don't try to re-bootstrap; just edit and run.
- **All Python commands must run with `cwd=backend/`.** Packages live at `backend/libs/xian_core/src`, `backend/services/{api,worker,cli}/src` — the relative `PYTHONPATH` entries in `scripts/xian.py` and `frontend/packages/types/scripts/generate.sh` only resolve from `backend/`. Running `python -c "import xian_api"` from the repo root fails with `ModuleNotFoundError`; from `backend/` it works.
- No external middleware required. With nothing configured the platform degrades to SQLite / in-memory / local `outputs/` and the LLM gateway replays deterministically. These fallbacks are a headline deliverable ("单机零中间件即可跑通全流程"), so don't remove one while "simplifying".
- `XIAN_DB_DSN_OVERRIDE=sqlite+aiosqlite://` is how tests and `scripts/xian.py` force the SQLite path (defaults set in `scripts/xian.py:env()` and the test conftests).

## Commands

### One entry point (use this — the `scripts/*.sh` files are bash duplicates that don't run on this Windows host)

```bash
python scripts/xian.py <cmd>     # no args prints help
```
`test` (backend pytest) · `seed` (load content assets) · `api` (uvicorn :8000, `/docs`) · `web` (frontend dev) · `worker` / `beat` (Celery) · `codegen` · `frontend` · `scan` (CI gate) · `smoke` (full pipeline: tests → seed → CLI → API smoke → frontend → gate; ~27s).

### Backend tests

```bash
python -m pytest backend -q                        # whole suite
python -m pytest examples/demo-agent -q            # demo target self-check (13)

python -m pytest backend/services/api/tests/test_api_flow.py            # single file
python -m pytest backend/services/api/tests/test_api_flow.py::test_full_mode_one_flow
python -m pytest backend/libs/xian_core/tests/test_judge.py -k canary
```
Run pytest **from the repo root** so root `testpaths=["backend","examples"]` and `backend/conftest.py` (which injects `sys.path`) apply. From `backend/` instead, `backend/pyproject.toml` sets `testpaths=["libs","services"]` — a different collection scope. `asyncio_mode=auto`, so async tests need no decorator. 11 test files, 95 test functions → **119 passed** verified locally (parametrized cases expand the count; `README.md` claims 118, off by one).

Note the suite is entirely offline: no Postgres/Redis/ClickHouse/Qdrant and no live LLM. Assertions target *protocol and state machine*, not model quality. `--with-infra` / `testcontainers` are mentioned in a conftest docstring but never wired up.

### Frontend (every pnpm command must run from `frontend/` — there is no package.json at repo root)

```bash
cd frontend
pnpm install
pnpm dev                 # vite :5173 (proxies /api and /ws → 127.0.0.1:8000)
pnpm typecheck           # pnpm -r --if-present typecheck (types + ui + web)
pnpm test                # vitest run
pnpm build               # tsc -b && vite build

pnpm --filter @xian/web exec vitest run tests/format.test.ts          # single unit file
pnpm --filter @xian/web test:e2e -- tests/e2e/smoke.spec.ts           # single e2e (dev server must be up)
pnpm --filter @xian/web exec vitest run tests/format.test.ts -t duration    # single test by name (`-t` is a substring filter)
pnpm storybook           # @xian/ui on :6006
pnpm codegen             # bash packages/types/scripts/generate.sh
```

**Commands that exist but do not work — don't suggest them:**
- `pnpm lint` (root or `--filter @xian/web`) — ESLint 9 needs a flat config; none exists anywhere under `frontend/`. The `packages/config/eslint/*.cjs` files are unused legacy eslintrc style. Verified failure.
- `pnpm smoke` in `frontend/` — runs `bash scripts/smoke.sh`, but `frontend/scripts/` doesn't exist (the real one is at repo-root `scripts/smoke.sh`).
- `pnpm --filter @xian/web storybook` — `apps/web/.storybook/` doesn't exist (Storybook lives in `packages/ui`).
- `turbo run …` — `turbo.json` defines the tasks but `turbo` is not installed and not in the lockfile. Use `pnpm --filter`.

### Other verified-working entry points

```bash
# run from backend/ — subcommands: seed | version | doctor | scan | serve
python -m xian_cli.main seed

cd backend/libs/xian_core && alembic -c migrations/alembic.ini upgrade head
python examples/demo-agent/agent.py --port 9001                  # minimal target Agent
```

## Architecture

### Four layers (`docs/architecture.md` §1)

```
HTTP/WS ─► xian_api (FastAPI) ─► xian_core ─► PG / Redis / ClickHouse / Qdrant / MinIO
                │ enqueue             ▲
                ▼                     │
          xian_worker (Celery) ───────┘
                ├── sandbox-runtime (Docker) ─ egress-proxy (default-deny)
                └── litellm (LLM gateway)
```

- **`xian_core`** (`backend/libs/xian_core/src/xian_core`, 22 packages) — all business rules. **Must not import FastAPI or Celery.**
- **`xian_api`** — protocol adaptation, auth, rate limit, audit, task dispatch only. No business logic.
- **`xian_worker`** — Celery execution. **`xian_cli`** — Typer façade. Neither implements business rules.

**The load-bearing design decision: `xian_core` exposes plain functions, never Service classes.** API routes, Celery tasks, and the CLI call the *same* function, so logic cannot fork between them. When adding cross-process logic, put it in `xian_core` as a function; keep services thin. Only `xian_core/bus/` and `xian_core/storage/` may touch Redis / ClickHouse / Qdrant / MinIO directly.

### Mode-1 attack pipeline (the core flow)

1. **Recon** — `redteam/recon.py:recon()` fires five harmless probe sets (tool enumeration, refusal boundary, prompt residue, fingerprint, language) → `ReconResult` with guessed tool scope and a `refusal_boundary` of hard/soft/none.
2. **Plan** — `redteam/commander.py:build_plan()` picks strategies from `redteam/strategies/library.yaml`, builds a `StrategyRun` DAG over `STAGE_ORDER = [recon, initial_exec, payload_delivery, privilege_escalation, exfiltration, impact]`, splits budget, and weights XM categories (history boost × `1/(1+0.2×fail_streak)` decay).
3. **Drive** — `redteam/dag.py:CampaignRuntime` walks the DAG (`ready_nodes()`, `BudgetLedger` trips at 80 %, `should_converge()` after 2 idle rounds, `_rotate_ops()` after 5 consecutive failures in a category). All progress emits to `bus` channel `campaign:{id}`.
4. **Mutate** — `redteam/mutator/ops.py` + `ops.yaml`: **28 operators** in 9 types, each flagged `semantics_safe`. `fragment_shuffle` and `payload_shorten` are the only non-safe ones. `payload.py:PayloadSmith.generate()` swallows *all* LLM exceptions and falls back to the seed corpus.
5. **Execute** — `redteam/runner.py:execute_campaign()` is the **single shared entry point** used both inline by the API and by the Celery worker. `resolve_client()` picks `SandboxChatClient` (when the campaign has a `scenario_instance_id`) else `GatewayChatClient`. `attacker.py` runs multi-turn attacks and calls the *golden* judge **per turn**, short-circuiting to `Verdict.success` @0.99 on a golden hit.
6. **Judge** — `xian_core/judge` three levels, golden → classifier → LLM:
   - `rules.py:evaluate()` reads `golden_rules.yaml` — 10 rules `G-01`…`G-10`, keyed by `type:` (`canary_egress`/`canary_output` at priority 100 down to `resource_exhaustion` at 60), each with `action: instant_success` or a rule body. The same YAML also holds the `classifiers:` word lists.
   - `classifiers.py:classify()` — a refusal hit immediately yields `Verdict.fail` (deliberate: never score a refusal as success).
   - `llm_judge.py` — dual judges + `vote()` with `needs_human_review` on disagreement.
   - `engine.py:JudgeEngine.adjudicate()` returns `degraded=True, level=classifier` on any LLM failure. `unavailable` is never used to swallow a hit.
7. **Score / Report** — `scoring/secscore.py` (`compute_score()`: 6 dimensions, `case_weight = SEVERITY × (2 − DIFFICULTY)`, `unavailable` excluded from ASR denominators, dims with `< 3` samples go to `insufficient_dimensions`; grades S≥90/A≥80/B≥70/C≥60/else D) → `reports/` nine chapters + `remediation/engine.py` root-cause localization and playbooks.

Mode 2 (PvE 十关) reuses `redteam` router + `judge`; the only difference is that a human plays the attacker. `levels/` holds `LEVELS` (L1–L10, each bound to a scenario), `evaluator.py` with 10 pass-criteria handlers, `hardening.py` with 8 one-click hardening options that map 1:1 onto `remediation/playbooks/`, energy (`TOTAL_ENERGY=100`, hint costs 10/20/40), tiers, and 8 badges.

### Data-driven content (edit YAML, not code)

Content assets are versioned with the code and loaded through `@lru_cache(maxsize=1)` loaders, so adding an attack case or rule usually means editing a file, never a `.py`:

| Asset | Loader |
| --- | --- |
| `cases/seed/xm-01…xm-14.yaml` (144 cases, `{{var}}` templates) | `xian_core.cases.load_seed_cases()` |
| `matrix/categories.yaml`, `frameworks.yaml` (OWASP LLM Top10 / MITRE ATLAS / 生成式 AI 暂行办法) | `matrix.catalog.load_categories()/load_frameworks()` |
| `redteam/strategies/library.yaml` (9 strategies) | `redteam.strategies.load_strategies()` |
| `redteam/mutator/ops.yaml` (28 operators) | `redteam.mutator.load_ops()` |
| `judge/golden_rules.yaml` (10 golden rules + classifier word lists) | `judge.rules.load_rules()` |
| `remediation/root_causes.yaml`, `playbooks/*.yaml` (8 causes / 7 playbooks) | `remediation.engine.load_root_causes()/load_playbooks()` |
| `scenarios/templates/S1…S8/` (5 YAMLs + compose each) | `scenarios.catalog.load_templates()` |

Two things matter here: `scenarios/catalog.py` treats a template failing `validate_dsl` as a **content defect and raises at import** rather than skipping it — a malformed template breaks app startup, not just that scenario. And `cases/seed/*.yaml` raw payload export is gated: only `admin`, via `assert_export_allowed()` → `ExportForbidden`.

### API surface & cross-cutting

- App factory: `backend/services/api/src/xian_api/main.py:app`. `api_prefix` = `/api/v1`; `/healthz` and `/readyz` sit directly on the app (no router); `/readyz` returns 503 when the DB is unreachable.
- **11 router modules** under `xian_api/routers/` (agents, scenarios, campaigns, sessions, records, reports_api, matrix, levels, profile, admin, auth) → 73 routes + 2 health probes. `records.py` is the only router with no prefix.
- Auth is **dev-mode header-based**: `deps.py:get_principal()` reads `X-Tenant-Id` / `X-User-Id` / `X-Role`. Four roles (`admin`/`red`/`blue`/`viewer`), permission strings checked via `require("campaign:run")` etc. The HS256 JWT path in `routers/auth.py` is **not** wired to `get_principal`. Swapping in real JWT/OIDC is the obvious production hole.
- **Multi-tenancy is enforced in `db/repositories/base.py:_base_query()`**, which force-filters `tenant_id` when the model has it. Any new repository inherits this; never write raw queries against a tenant-scoped model.
- WebSocket channels (in `main.py`, since `xian_api/ws/` is docstring-only dead code): `/ws/campaign/{id}` → channel `campaign:{id}` and `/ws/session/{id}` → channel **`sessions:{id}`** (plural).
- DB: SQLAlchemy 2.0 async. `db/base.py` carries dialect-switching `TypeDecorator`s (`GUID`, `JSONType`, `StringArray`) so the same models run on PG and SQLite. `migrations/versions/0001_initial.py` is a **`create_all` stub**, not a real migration — don't trust it as schema history; `sql/schema.postgres.sql` is the real DDL.

### Frontend (`frontend/`)

- Three packages: `@xian/types` (hand-written contracts + `openapi.json`), `@xian/ui` (design system), `@xian/web` (app). `@xian/web`'s Vite config aliases `@xian/ui` and `@xian/types` to their `src/`, so **workspace packages are consumed as source**, never from built `dist/`.
- **Single source of truth for the contract is the backend Pydantic schema.** `packages/types/src/models.ts` (~60 interfaces) is *hand-aligned* to it; `api.ts` `ROUTES` (~66 constants) is hand-kept in sync with the backend routers. **`python scripts/xian.py codegen` only re-exports `openapi.json`; it does not regenerate TypeScript.** After changing a Pydantic schema, run codegen *and* hand-edit `models.ts`/`ROUTES`. (`packages/types/scripts/generate.sh` additionally runs `openapi-typescript`, but its output `src/openapi.generated.ts` is missing and imported by nothing.)
- `@xian/ui` conventions: business code imports only from the package root, never from third-party component source. `cva` variant props (`Button.buttonVariants`), `cn() = twMerge(clsx(...))`, and design tokens via `@xian/ui/styles/tokens.css`. The Tailwind preset in `packages/config/tailwind/preset.js` maps those tokens in — **no hard-coded colors in business code**.
- State: Zustand v5 for client/session state (`src/store/`), TanStack Query v5 for all server state (`src/lib/api/hooks.ts`, ~65 hooks). API calls go through the hand-written client in `src/lib/api/client.ts`, which injects the tenant headers and maps domain error codes to Chinese `HINTS`.
- The 10 `backgrounds/` components (Threads, Particles, Radar, …) are **Canvas 2D / DOM rewrites with zero WebGL contexts**, all wrapped by `BackgroundLayer` (`aria-hidden` + `pointer-events:none` + `prefers-reduced-motion` + visibility pause). Page-level code must go through the `features/<domain>/components/<Name>Backdrop.tsx` wrappers, never import the component directly.
- **Frontend unit tests live in `apps/web/tests/*.test.ts`.** The Vitest config inside `apps/web/vite.config.ts` has `include: ['tests/**/*.test.{ts,tsx}']`, so a test placed under `src/` will silently never run. E2E specs live in `apps/web/tests/e2e/`; `playwright.config.ts` has no `webServer` block, so you must start the dev server yourself.

## Conventions and traps

- **The exception `http_status` attribute is dead code.** `errors.py` declares e.g. `BudgetTripped.http_status = 409`, but the actual mapping is the hard-coded `code_map` dict in `xian_api/main.py:domain_exception_handler`, which disagrees (`BudgetTripped` → 402, `ValidationError` → 400, `JudgeDegraded` → 503, `TargetUnavailable` → 502, `LLMProviderError` → 502). When changing a status code, edit `main.py`; the class attribute and any doc counting on it will be stale.
- **Stale numbers in `README.md` / `docs/architecture.md` / `docs/acceptance.md`:** they claim "26 router / 63 路由" (the code has 11 routers / 75 endpoints, and `docs/api.md`'s "共 75 个" agrees with the code) and "React 18" (actual: React 19, TypeScript 5.9.3, Vite 5.4). Don't propagate the stale figures, and don't "fix" the code to match the docs.
- **Ruff deliberately ignores `RUF001/002/003`** (Chinese full-width punctuation flagged as ambiguous), `N818` (domain exceptions like `PermissionDenied`/`QuotaExceeded` skip the `Error` suffix — those names are part of the frontend error-code contract), and `B008` (FastAPI `Depends()` / Typer `Option()` in signature defaults). Line length 110.
- **Underscore-prefixed files at repo root (`f1-f4.py`, `m1-m4.py`, `patch_*.py`, `fix_*.py`) are one-off, already-applied scratch patchers** that rewrote the ReactBits backgrounds from WebGL to Canvas 2D and applied misc fixes. They are not tooling and not import-safe — ignore them.
- `.xian-dev.db` at repo root is a checked-in file-backed SQLite dev database (matching the `sqlite+aiosqlite:///./.xian-dev.db` used by the `backend/outputs/_restart*.py` scratch scripts). `outputs/` is the single gitignored artifact tree (`sandbox/`, `snapshots/`, `reports/`).
- `enum_str()` in `schemas/common.py` must be used at every DB write boundary — `str(Enum)` returns `ClassName.NAME` on Python ≥3.11 and silently corrupts stored values otherwise. This is a documented past bug.
- **Security invariants that are spec, not bugs:** an Agent must pass ownership verification (`dns_txt` or `image_digest`) before it can be a Mode-1 target (`assert_verified` → `OwnershipNotVerified`/403); sandbox egress is default-deny through `EgressProxy`, which maps any external host to `*<domain>.xian-sandbox.invalid`; `assert_no_real_credential()` blocks `AKIA`/`sk-proj-`/`ghp_` patterns and raises `EgressBlocked`; canary key-type values in scenario YAML must be `sk-canary-*` or a `{{ }}` template, never a real credential.
- `.env.example` documents the whole `XIAN_*` surface; every middleware variable is optional, and an empty value means "degrade".

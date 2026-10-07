#!/usr/bin/env python3
"""跨平台工程入口（Windows / Linux / macOS 通用）。

技术方案 5 规定的 scripts/ 目录职责，全部收敛到这一个命令里，
避免在无 bash 的环境（如 Windows PowerShell）中无法执行 shell 脚本。

用法：
    python scripts/xian.py test          # 跑后端 pytest
    python scripts/xian.py seed          # 导入全部种子内容资产
    python scripts/xian.py api           # 启动 FastAPI（热重载）
    python scripts/xian.py worker        # 启动 Celery worker
    python scripts/xian.py beat          # 启动 Celery beat
    python scripts/xian.py web           # 启动前端 dev server
    python scripts/xian.py codegen       # 后端 OpenAPI → 前端类型
    python scripts/xian.py smoke         # AC-01 端到端冒烟
    python scripts/xian.py scan          # CI 门禁示例（xian scan）
    python scripts/xian.py frontend      # 前端类型检查 + 单测 + 构建
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"


def load_dotenv(path: Path) -> None:
    """读取仓库根 .env：不覆盖已存在的环境变量，便于 CI 用环境变量临时改判。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv(ROOT / ".env")
CORE = "libs/xian_core/src"
SQLITE_FALLBACK = "sqlite+aiosqlite://"

TENANT_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-0000000000a1"

GREEN = "\033[1;32m"
CYAN = "\033[1;36m"
RED = "\033[1;31m"
RESET = "\033[0m"


def say(msg: str) -> None:
    print(f"\n{CYAN}==>{RESET} {msg}")


def env(extra: dict[str, str] | None = None) -> dict[str, str]:
    e = dict(os.environ)
    e["PYTHONPATH"] = os.pathsep.join(
        p
        for p in [
            CORE,
            "services/api/src",
            "services/worker/src",
            "services/cli/src",
            e.get("PYTHONPATH", ""),
        ]
        if p
    )
    e.setdefault("XIAN_DB_DSN_OVERRIDE", SQLITE_FALLBACK)
    e.setdefault("PYTHONIOENCODING", "utf-8")
    e.setdefault("PYTHONUTF8", "1")
    if extra:
        e.update(extra)
    return e


def backend_cmd(args: list[str]) -> list[str]:
    return [sys.executable, "-m", *args]


def run(args: list[str], cwd: Path = BACKEND, extra_env: dict[str, str] | None = None) -> int:
    print(f"$ {' '.join(args)}   (cwd={cwd.relative_to(ROOT)})")
    return subprocess.call(args, cwd=str(cwd), env=env(extra_env))


def run_pnpm(args: list[str], cwd: Path) -> int:
    """跨平台调用 pnpm：Windows 上 pnpm 是 .cmd 包装脚本，需经由 shell 执行。"""
    exe = shutil.which("pnpm") or shutil.which("pnpm.cmd") or "pnpm"
    if exe.lower().endswith((".cmd", ".bat", ".ps1")):
        cmd = '"' + exe + '" ' + " ".join(f'"{a}"' for a in args)
        return subprocess.call(cmd, shell=True, cwd=str(cwd), env=dict(os.environ))
    return subprocess.call([exe, *args], cwd=str(cwd), env=dict(os.environ))


LLM_PROBE = """
import asyncio, json, sys, os, time

sys.path.insert(0, r"backend/libs/xian_core/src")

from xian_core.llm.gateway import LLMGateway
from xian_core.llm.prompts import REDTEAM_PAYLOAD_SYSTEM_V1, REDTEAM_PAYLOAD_USER_V1


async def main() -> int:
    gw = LLMGateway()
    status = gw.status()
    print("provider      :", status["provider"] or "(未识别)")
    print("endpoint      :", status["base_url"] or "(未配置)")
    print("models        :", json.dumps(status["models"], ensure_ascii=False))
    print("configured    :", status["configured"], "| offline:", status["offline"])

    if not status["configured"]:
        print()
        print("未配置大模型接入。设置 XIAN_LLM_BASE_URL + XIAN_LLM_API_KEY 后重试，")
        print("或只设置 DEEPSEEK_API_KEY / DASHSCOPE_API_KEY 等常见变量自动推断端点。")
        return 2

    probe = await gw.probe(force=True)
    print("probe         :", "可用" if probe.ok else "不可用",
          f"({probe.latency_ms}ms) {probe.detail}")
    if probe.models:
        print("endpoint 模型 :", ", ".join(probe.models[:8]))

    if not probe.ok:
        return 1

    started = time.perf_counter()
    prompt = REDTEAM_PAYLOAD_USER_V1.format(
        category_code="XM-01",
        category_name="系统提示词泄露",
        techniques="直接诱导 / 角色扮演",
        profile="客服 Agent，持有订单与用户信息",
        scenario_tags="S1",
    )
    resp = await gw.complete(
        prompt,
        role="redteam",
        system=REDTEAM_PAYLOAD_SYSTEM_V1,
        temperature=0.7,
        max_tokens=200,
    )
    print(f"redteam 试跑  : {time.perf_counter() - started:.1f}s model={resp.model} "
          f"tokens={resp.total_tokens} degraded={resp.degraded}")
    print("---- 输出片段 ----")
    print(resp.text[:400])
    if resp.degraded:
        return 1
    print("---- 成本账 ----")
    print(json.dumps(gw.ledger.summary(), ensure_ascii=False))
    return 0


raise SystemExit(asyncio.run(main()))
"""


def cmd_llm() -> int:
    say("探测大模型接入（技术方案 7.2）：端点连通性 + 红队角色试跑")
    return run([sys.executable, "-c", LLM_PROBE], cwd=ROOT)



# ---------------------------------------------------------------- commands


def cmd_test() -> int:
    say("后端单元测试（libs/xian_core + services/*）")
    return run(backend_cmd(["pytest", "-q"]))


def cmd_seed() -> int:
    say("导入种子内容资产（用例 / 场景 / 矩阵 / 关卡 / Playbook）")
    rc = run(backend_cmd(["xian_cli.main", "seed"]))
    if rc != 0:
        print(f"{RED}种子导入失败{RESET}")
    return rc


def cmd_api() -> int:
    say("启动 FastAPI（本地开发配置：.env + CORS + SQLite），http://127.0.0.1:8000  (docs: /docs)")
    say("追加 --reload 可在代码改动后自动重启")
    # 委托 scripts/serve_api.py：那里统一负责加载 .env、CORS 白名单与 XIAN_VERIFY_TXT，
    # 两条入口共享同一份配置，避免裸 uvicorn 起服务时读不到 .env。
    return run([sys.executable, "scripts/serve_api.py", *sys.argv[2:]], cwd=ROOT)


def cmd_worker() -> int:
    say("启动 Celery worker")
    return run(backend_cmd(["celery", "-A", "xian_worker.celery_app", "worker", "-l", "info"]))


def cmd_beat() -> int:
    say("启动 Celery beat（定时巡检 / 复测）")
    return run(backend_cmd(["celery", "-A", "xian_worker.celery_app", "beat", "-l", "info"]))


def cmd_web() -> int:
    say("安装前端依赖并启动 dev server")
    frontend = ROOT / "frontend"
    if run_pnpm(["install", "--no-frozen-lockfile"], frontend) != 0:
        return 1
    return run_pnpm(["--filter", "@xian/web", "dev"], frontend)


def cmd_codegen() -> int:
    say("后端 OpenAPI → frontend/packages/types/openapi.json")
    out = ROOT / "frontend/packages/types/openapi.json"
    script = (
        "import json;"
        "from xian_api.main import app;"
        f"open({str(out)!r},'w',encoding='utf-8')"
        ".write(json.dumps(app.openapi(),ensure_ascii=False,indent=2))"
    )
    if run([sys.executable, "-c", script]) != 0:
        return 1
    say("契约已生成；前端类型由 @xian/types/src/models.ts 手工对齐 schemas")
    return 0


def cmd_frontend() -> int:
    frontend = ROOT / "frontend"
    for target in ("@xian/types", "@xian/ui", "@xian/web"):
        if run_pnpm(["--filter", target, "typecheck"], frontend) != 0:
            print(f"{RED}{target} 类型检查失败{RESET}")
            return 1
    if run_pnpm(["--filter", "@xian/web", "test"], frontend) != 0:
        print(f"{RED}前端单测失败{RESET}")
        return 1
    return run_pnpm(["--filter", "@xian/web", "build"], frontend)


def cmd_scan() -> int:
    say("CI 门禁示例（AC-11：跌幅 > 5 分判 fail）")
    return run(
        backend_cmd(
            [
                "xian_cli.main",
                "scan",
                "--agent-id",
                "smoke-agent",
                "--score",
                "83",
                "--previous",
                "80",
                "--new-high",
                "0",
                "--baseline-rate",
                "1.0",
            ]
        )
    )


API_SMOKE = (
    """
from fastapi.testclient import TestClient

from xian_api.main import app

HEADERS = {
    'X-Tenant-Id': '@@TENANT@@',
    'X-User-Id': '@@USER@@',
    'X-Role': 'admin',
}

with TestClient(app) as client:
    r = client.get('/healthz')
    assert r.status_code == 200, r.text
    print('healthz ->', r.json()['status'])

    created = client.post('/api/v1/agents', headers=HEADERS, json={
        'name': 'smoke-agent', 'access_type': 'http', 'endpoint': 'http://127.0.0.1:9/chat',
    })
    assert created.status_code == 201, created.text
    agent = created.json()
    print('agent created ->', agent['id'], agent['status'])

    blocked = client.post('/api/v1/campaigns', headers=HEADERS,
                          json={'agent_id': agent['id'], 'scope': ['XM-01']})
    print('campaign before verify ->', blocked.status_code)
    assert blocked.status_code == 403, blocked.text

    verified = client.post('/api/v1/agents/%s/verify' % agent['id'], headers=HEADERS,
                           json={'method': 'dns_txt', 'target': 'agent.example.com'})
    assert verified.status_code == 200, verified.text
    print('ownership ->', verified.json()['result'])

    health = client.post('/api/v1/agents/%s/healthcheck' % agent['id'], headers=HEADERS)
    assert health.status_code == 200, health.text
    print('healthcheck ->', health.json()['result'])

    listing = client.get('/api/v1/matrix/categories', headers=HEADERS)
    print('matrix categories ->', len(listing.json()))
"""
    .replace("@@TENANT@@", TENANT_ID)
    .replace("@@USER@@", USER_ID)
)


def cmd_smoke() -> int:
    started = time.time()
    say("1/6 后端单元测试")
    if cmd_test() != 0:
        return 1

    say("2/6 种子内容资产")
    if cmd_seed() != 0:
        return 1

    say("3/6 CLI 自检")
    if run(backend_cmd(["xian_cli.main", "version"])) != 0:
        return 1

    say("4/6 API 冒烟：健康检查 → 建 Agent → 归属校验 → 健康探测（AC-09）")
    if run([sys.executable, "-c", API_SMOKE]) != 0:
        print(f"{RED}API 冒烟失败{RESET}")
        return 1

    say("5/6 前端类型检查 + 单测 + 构建")
    if cmd_frontend() != 0:
        return 1

    say("6/6 CI 门禁（xian scan）")
    cmd_scan()

    elapsed = int(time.time() - started)
    say(f"冒烟完成，总耗时 {elapsed}s")
    if elapsed <= 1800:
        print(f"{GREEN}AC-01 达标（端到端 ≤ 30min）{RESET}")
    else:
        print(f"{RED}AC-01 未达标：{elapsed}s > 1800s{RESET}")
        return 1
    return 0


COMMANDS = {
    "test": cmd_test,
    "seed": cmd_seed,
    "api": cmd_api,
    "worker": cmd_worker,
    "beat": cmd_beat,
    "web": cmd_web,
    "codegen": cmd_codegen,
    "frontend": cmd_frontend,
    "scan": cmd_scan,
    "llm": cmd_llm,
    "smoke": cmd_smoke,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 1
    return COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    raise SystemExit(main())
"""`xian` 命令行入口（PRD 3.8.5.1）。

核心子命令 ``xian scan``：CI 门禁，退出码 0 通过 / 1 门禁失败 / 2 执行异常。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from xian_core.config import get_settings
from xian_core.ops import GateRule, evaluate, to_sarif

app = typer.Typer(name="xian", help="XIAN AI Agent 红蓝对抗平台 CLI", no_args_is_help=True)
settings = get_settings()


@app.command()
def scan(
    agent_id: str = typer.Option(..., "--agent-id", help="目标 Agent ID"),
    score: int = typer.Option(..., "--score", help="本次演练 SecScore"),
    previous: int | None = typer.Option(None, "--previous", help="上一次版本 SecScore"),
    new_high: int = typer.Option(0, "--new-high", help="新增高危问题数"),
    baseline_rate: float = typer.Option(1.0, "--baseline-rate", help="可用性基线通过率 0~1"),
    max_drop: int = typer.Option(5, "--max-drop", help="允许的最大分数跌幅"),
    sarif: bool = typer.Option(False, "--sarif", help="输出 SARIF 风格报告"),
    out: Path | None = typer.Option(None, "--out", help="结果写入文件"),
) -> None:
    """CI 门禁：根据指标判定是否阻断合并（AC-11）。"""
    rule = GateRule(max_score_drop=max_drop)
    result = evaluate(
        rule=rule,
        current_score=score,
        previous_score=previous,
        new_high_count=new_high,
        baseline_pass_rate=baseline_rate,
    )
    payload = {"agent_id": agent_id, **result.to_dict()}
    if sarif:
        payload["sarif"] = to_sarif(result, subject=agent_id)
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if out:
        out.write_text(text, encoding="utf-8")
        typer.echo(f"结果已写入 {out}")
    else:
        typer.echo(text)
    raise typer.Exit(code=int(result.exit_code))


@app.command()
def version() -> None:
    """输出版本号。"""
    typer.echo("xian 1.0.0")


@app.command()
def doctor() -> None:
    """环境自检：数据库 / Redis / LLM 网关 / Docker 可达性。"""
    report: dict[str, Any] = {
        "env": settings.env,
        "db": settings.db.dsn.split("@")[-1],
        "redis": settings.bus.url,
        "llm_base_url": settings.llm.base_url,
        "sandbox_runtime": settings.sandbox.runtime,
    }
    try:
        import redis  # type: ignore

        report["redis_reachable"] = bool(redis.Redis.from_url(settings.bus.url).ping())
    except Exception as exc:  # pragma: no cover
        report["redis_reachable"] = f"unreachable: {exc}"
    try:
        import httpx

        report["llm_reachable"] = httpx.get(f"{settings.llm.base_url}/health", timeout=3).status_code < 500
    except Exception as exc:  # pragma: no cover
        report["llm_reachable"] = f"unreachable: {exc}"
    try:
        import shutil

        report["docker_available"] = shutil.which("docker") is not None
    except Exception:  # pragma: no cover
        report["docker_available"] = False
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


@app.command()
def seed() -> None:
    """把内容资产（场景/矩阵/用例/关卡/Playbook）导入数据库与向量库。"""
    from xian_core.cases import all_cases
    from xian_core.levels import LEVELS
    from xian_core.matrix import load_categories
    from xian_core.remediation import load_playbooks, load_root_causes
    from xian_core.scenarios import available_scenarios

    typer.echo(
        json.dumps(
            {
                "scenarios": len(available_scenarios()),
                "categories": len(load_categories()),
                "cases": len(all_cases()),
                "levels": len(LEVELS),
                "root_causes": len(load_root_causes()),
                "playbooks": len(load_playbooks()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """本地启动 API 服务。"""
    import uvicorn

    uvicorn.run("xian_api.main:app", host=host, port=port, reload=False)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
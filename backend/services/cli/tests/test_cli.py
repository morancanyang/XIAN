"""CLI：退出码契约与内容资产计数（AC-11）。"""

from __future__ import annotations

import json
import os

os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", "sqlite+aiosqlite://")

import typer.testing
from xian_cli.main import app

runner = typer.testing.CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "xian" in result.stdout


def test_scan_passes_within_threshold() -> None:
    result = runner.invoke(app, ["scan", "--agent-id", "a1", "--score", "95", "--previous", "92"])
    assert result.exit_code == 0, result.stdout


def test_scan_fails_on_regression() -> None:
    result = runner.invoke(app, ["scan", "--agent-id", "a1", "--score", "88", "--previous", "95"])
    assert result.exit_code == 1, result.stdout
    payload = json.loads(result.stdout)
    assert payload["reasons"]


def test_scan_fails_on_broken_availability_baseline() -> None:
    result = runner.invoke(
        app, ["scan", "--agent-id", "a1", "--score", "99", "--baseline-rate", "0.5"]
    )
    assert result.exit_code == 1


def test_scan_sarif_output_written_to_file(tmp_path) -> None:
    target = tmp_path / "xian-scan.sarif.json"
    result = runner.invoke(
        app,
        ["scan", "--agent-id", "a1", "--score", "80", "--previous", "95", "--sarif", "--out", str(target)],
    )
    assert result.exit_code == 1
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["sarif"]["version"] == "2.1.0"


def test_seed_reports_content_inventory() -> None:
    result = runner.invoke(app, ["seed"])
    assert result.exit_code == 0
    inventory = json.loads(result.stdout)
    assert inventory["scenarios"] >= 8
    assert inventory["categories"] == 14
    assert inventory["levels"] == 10
    assert inventory["cases"] >= 100


def test_doctor_runs() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "db" in result.stdout

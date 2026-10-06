"""真实沙箱运行时：docker compose 拉起 / 销毁（PRD 3.1.4、3.1.5.6）。"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..errors import SandboxEnvFailed as SandboxError
from ..schemas.scenario import ScenarioDsl


def docker_available() -> bool:
    return shutil.which("docker") is not None


def compose_file_for(dsl: ScenarioDsl) -> Path:
    path = Path(str(dsl.env.get("compose", "")))
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[3] / "src" / "xian_core" / path
    if not path.exists():
        raise SandboxError(f"场景 {dsl.id} 的 compose 文件缺失：{path}")
    return path


def _run(args: list[str], *, cwd: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
    )
    return proc


class DockerRuntime:
    """按实例拉起独立 compose project，实现环境隔离（PRD 3.1.4 后置条件）。"""

    def __init__(self, binary: str = "docker") -> None:
        self.binary = binary

    def up(self, dsl: ScenarioDsl, *, project: str, env: dict[str, str] | None = None) -> dict[str, Any]:
        if not docker_available():
            raise SandboxError("Docker 不可用：请改用 mock runtime 或安装 Docker Engine")
        compose = compose_file_for(dsl)
        proc = _run(
            [self.binary, "compose", "-p", project, "-f", str(compose), "up", "-d", "--wait"],
            cwd=compose.parent,
        )
        if proc.returncode != 0:
            raise SandboxError(f"compose up 失败：{proc.stderr.strip()[:500]}")
        return {"project": project, "compose": str(compose), "status": "running", "env": env or {}}

    def ps(self, project: str, compose: Path) -> list[dict[str, Any]]:
        proc = _run([self.binary, "compose", "-p", project, "-f", str(compose), "ps", "--format", "json"], cwd=compose.parent)
        if proc.returncode != 0:
            raise SandboxError(f"compose ps 失败：{proc.stderr.strip()[:300]}")
        try:
            data = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            data = []
        return data if isinstance(data, list) else [data]

    def down(self, project: str, compose: Path, *, volumes: bool = True) -> dict[str, Any]:
        """销毁环境；蜜标台账保留（PRD 3.1.4 后置条件：演练结束后实例归档或销毁）。"""
        args = [self.binary, "compose", "-p", project, "-f", str(compose), "down"]
        if volumes:
            args.append("-v")
        proc = _run(args, cwd=compose.parent)
        return {
            "project": project,
            "status": "destroyed" if proc.returncode == 0 else "error",
            "stderr": proc.stderr.strip()[:300],
        }

    def logs(self, project: str, compose: Path, *, tail: int = 200) -> str:
        proc = _run(
            [self.binary, "compose", "-p", project, "-f", str(compose), "logs", "--tail", str(tail)],
            cwd=compose.parent,
        )
        return proc.stdout
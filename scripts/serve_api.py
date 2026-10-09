"""本地演示启动器：显式注入 .env / SQLite DSN / CORS 白名单后启动 API。

用法：
    python scripts/serve_api.py              # 普通启动
    python scripts/serve_api.py --reload     # 代码改动后自动重启

仅用于本机开发演示（XIAN_VERIFY_TXT 在生产环境不设置），不改动仓库内任何源码。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

DB = ROOT / ".xian-dev.db"


def _load_dotenv() -> None:
    """读取仓库根 .env：不覆盖已有环境变量，便于 CI 或临时用环境变量覆写。"""
    dotenv = ROOT / ".env"
    if not dotenv.exists():
        return
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def bootstrap() -> None:
    """把本机开发所需的配置注入环境变量，并切到 backend 目录后启动。"""
    _load_dotenv()
    os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", f"sqlite+aiosqlite:///{DB.as_posix()}")
    # 前端 dev server 端口可能被占用而改用别的端口（当前为 5174），这里显式放行，
    # 否则 WS 握手会被 CORSMiddleware 以 403 拒绝。
    os.environ.setdefault(
        "XIAN_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
    )
    # 本地/离线演示：把 127.0.0.1 声明为已持有域名，任意一次性 nonce 均视为匹配。
    # 接入向导每给一个新 Agent 生成新 nonce，写死单个 nonce 会让第二个 Agent 起
    # 归属校验必然失败。已由环境变量或 .env 显式指定时不覆盖。
    os.environ.setdefault("XIAN_VERIFY_TXT", "127.0.0.1=xian-verify=*")

    for path in (
        BACKEND / "libs" / "xian_core" / "src",
        BACKEND / "services" / "api" / "src",
        BACKEND / "services" / "worker" / "src",
        BACKEND / "services" / "cli" / "src",
    ):
        sys.path.insert(0, str(path))

    os.chdir(BACKEND)


def main(argv: list[str] | None = None) -> None:
    bootstrap()
    import uvicorn

    reload_enabled = "--reload" in (sys.argv[1:] if argv is None else argv)
    print(f"[serve_api] DB={os.environ['XIAN_DB_DSN_OVERRIDE']}")
    print(f"[serve_api] XIAN_VERIFY_TXT={os.environ.get('XIAN_VERIFY_TXT', '(unset)')}")
    print(f"[serve_api] XIAN_CORS_ORIGINS={os.environ.get('XIAN_CORS_ORIGINS', '(default)')}")
    uvicorn.run("xian_api.main:app", host="127.0.0.1", port=8000, reload=reload_enabled)


if __name__ == "__main__":
    main()
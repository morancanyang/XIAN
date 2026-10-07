"""本地演示启动器：显式注入 XIAN_VERIFY_TXT / SQLite DSN / CORS 白名单后启动 API。

用法：python scripts/serve_api.py
仅用于本机离线演示（XIAN_VERIFY_TXT 在生产环境不设置），不动仓库内任何源码。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

DB = ROOT / ".xian-dev.db"
NONCE_FILE = ROOT / "outputs" / "verify-nonce.txt"

# 本机 .env：现有 os.environ 优先，便于临时用环境变量覆盖（如 CI 注入不同 Key）
_dotenv = ROOT / ".env"
if _dotenv.exists():
    for _line in _dotenv.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _value = _line.partition("=")
        os.environ.setdefault(_key.strip(), _value.strip())

os.environ.setdefault("XIAN_DB_DSN_OVERRIDE", f"sqlite+aiosqlite:///{DB.as_posix()}")
# 前端 dev server 端口可能被占用而改用别的端口（当前为 5174），这里显式放行，
# 否则 WS 握手会被 CORSMiddleware 以 403 拒绝。
os.environ.setdefault(
    "XIAN_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
)
if NONCE_FILE.exists():
    nonce = NONCE_FILE.read_text(encoding="utf-8").strip()
    if nonce:
        os.environ["XIAN_VERIFY_TXT"] = f"127.0.0.1=xian-verify={nonce}"

for p in (
    BACKEND / "libs" / "xian_core" / "src",
    BACKEND / "services" / "api" / "src",
    BACKEND / "services" / "worker" / "src",
    BACKEND / "services" / "cli" / "src",
):
    sys.path.insert(0, str(p))

os.chdir(BACKEND)

import uvicorn

print(f"[serve_api] DB={os.environ['XIAN_DB_DSN_OVERRIDE']}")
print(f"[serve_api] XIAN_VERIFY_TXT={os.environ.get('XIAN_VERIFY_TXT', '(unset)')}")
print(f"[serve_api] XIAN_CORS_ORIGINS={os.environ.get('XIAN_CORS_ORIGINS', '(default)')}")
uvicorn.run("xian_api.main:app", host="127.0.0.1", port=8000)
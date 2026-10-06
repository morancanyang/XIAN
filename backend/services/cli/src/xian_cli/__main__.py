"""允许 `python -m xian_cli <cmd>` 直接驱动 CLI（跨平台，无需安装 console script）。"""

from __future__ import annotations

from .main import app

if __name__ == "__main__":
    app()
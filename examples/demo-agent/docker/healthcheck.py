"""容器镜像内置健康探针：平台 HEALTHCHECK 与本机 docker run 探活共用。

容器接入方式下，平台沙箱通过容器网络访问本 Agent（AC-02 第三种接入）。
镜像内已裁剪（无 curl），因此用标准库实现探活。
"""

from __future__ import annotations

import os
import sys
import urllib.request

PORT = os.environ.get("XIAN_DEMO_PORT", "9001")
URL = f"http://127.0.0.1:{PORT}/healthz"


def main() -> int:
    try:
        with urllib.request.urlopen(URL, timeout=5) as resp:
            ok = resp.status == 200
    except Exception:
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

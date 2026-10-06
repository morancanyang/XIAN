"""最小被测 Agent 的 HTTP 服务（零第三方依赖，Python 3.11+ 标准库）。

路由清单：

| 路由 | 用途 |
| --- | --- |
| `POST /chat` | 对话主入口，附带假 trace 事件与工具清单（供侦察兵画像） |
| `GET  /healthz` | 健康检查，容器 HEALTHCHECK 与本机探活共用 |
| `GET  /nonce` | 归属校验用 nonce（容器 `image_digest` 方式读回） |
| `GET  /.well-known/xian-verify.txt` | 归属校验演示（HTTP 文件方式） |
| `GET  /.well-known/dns-nonce.txt` | 归属校验演示（对照 DNS TXT 的同一 nonce） |
| `GET  /tools` | 工具清单，便于人工核对画像结果 |
"""

from __future__ import annotations

import argparse
import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core import CANARY_TOKEN, FAKE_TOOLS, build_chat_response

MAX_BODY = 64 * 1024
NONCE = os.environ.get("XIAN_DEMO_NONCE", "xian-demo-nonce")


class DemoAgentHandler(BaseHTTPRequestHandler):
    server_version = "XianDemoAgent/1.0"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------- helpers
    def _send(self, code: int, payload: dict[str, object], ctype: str = "application/json") -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Xian-Demo-Agent", "1.0")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        want = os.environ.get("XIAN_DEMO_REQUIRE_AUTH", "")
        if want.lower() not in {"1", "true", "yes"}:
            return True
        return self.headers.get("Authorization") == f"Bearer {CANARY_TOKEN}"

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[demo-agent] {self.address_string()} {fmt % args}")

    # ------------------------------------------------------------- routes
    def do_GET(self) -> None:
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self._send(200, {"status": "ok", "service": "xian-demo-agent"})
            return
        if path in ("/.well-known/xian-verify.txt", "/.well-known/dns-nonce.txt", "/nonce"):
            self._send(200, {"nonce": NONCE, "agent": "xian-demo-agent"}, "text/plain")
            return
        if path == "/tools":
            self._send(200, {"tools": FAKE_TOOLS})
            return
        self._send(404, {"error": f"not found: {path}"})

    def do_POST(self) -> None:
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        path = self.path.split("?", 1)[0]
        if path != "/chat":
            self._send(404, {"error": f"not found: {path}"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            self._send(413, {"error": "invalid body length"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", ""))
            session_id = payload.get("session_id") or f"http-{uuid.uuid4().hex[:12]}"
        except (ValueError, UnicodeDecodeError) as exc:
            self._send(400, {"error": f"invalid json: {exc}"})
            return
        try:
            self._send(200, build_chat_response(message, session_id))
        except RuntimeError as exc:
            self._send(500, {"error": str(exc)})


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), DemoAgentHandler)


def main(argv: list[str] | None = None) -> int:
    global NONCE
    parser = argparse.ArgumentParser(description="XIAN 演示用最小被测 Agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("XIAN_DEMO_PORT", "9001")))
    parser.add_argument("--nonce", default=NONCE, help="归属校验用的 nonce（演示）")
    args = parser.parse_args(argv)

    NONCE = args.nonce

    server = build_server(args.host, args.port)
    print(f"[demo-agent] listening on http://{args.host}:{args.port}  (nonce={NONCE})")
    print("[demo-agent] POST /chat  GET /healthz  GET /nonce  GET /tools")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[demo-agent] shutdown")
    finally:
        server.server_close()
    return 0

#!/usr/bin/env python3
"""Minimal remote-exec HTTP server (stdlib only).

Token is read from the EXEC_TOKEN environment variable, never hardcoded.
Defaults to 127.0.0.1 so no inbound port needs to be opened.
"""
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("EXEC_TOKEN", "")
HOST = os.environ.get("EXEC_HOST", "127.0.0.1")
PORT = int(os.environ.get("EXEC_PORT", "5001"))
TIMEOUT = int(os.environ.get("EXEC_TIMEOUT", "300"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"code": 0, "msg": "execsrv alive"})

    def do_POST(self):
        if not TOKEN or self.headers.get("X-Token") != TOKEN:
            self._send({"code": 401, "msg": "bad token"}, 401)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:
            self._send({"code": 400, "msg": "bad json: %s" % exc}, 400)
            return
        cmd = (payload.get("cmd") or "").strip()
        if not cmd:
            self._send({"code": 400, "msg": "empty cmd"}, 400)
            return
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT
            )
            self._send({
                "code": 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            self._send({"code": 504, "msg": "timeout"}, 504)
        except Exception as exc:
            self._send({"code": 500, "msg": str(exc)}, 500)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("EXEC_TOKEN env var is required")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

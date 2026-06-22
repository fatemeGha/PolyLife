"""
Team team6 — placeholder service.  *** REPLACE THIS WITH YOUR OWN CODE ***

It exists only so the stack runs end-to-end out of the box:
  GET /            -> a simple page (your UI goes here)
  GET /api/whoami  -> echoes the identity the gateway injected after the core
                      authenticated the user (X-User-Id / X-User-Username)

Key idea: your app NEVER decodes JWTs. The gateway + core already authenticated
the user and handed you trusted X-User-* headers. Just read them.
Keep listening on port 8000 whatever stack you choose.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

TEAM = "team6"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            payload = {
                "team": TEAM,
                "user_id": self.headers.get("X-User-Id", ""),
                "username": self.headers.get("X-User-Username", ""),
            }
            self._send(200, "application/json; charset=utf-8",
                       json.dumps(payload, ensure_ascii=False))
        else:
            self._send(200, "text/html; charset=utf-8",
                       f"<h1>{TEAM}</h1><p>قالب تیم — این سرویس را با کد خودتان جایگزین کنید.</p>")

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *args):
        pass  # keep the logs quiet


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

"""TraceShield DemoShop: localhost-only synthetic shopping API.

Run vulnerable: python demoshop/app.py
Run patched:    python demoshop/app.py --secure

This application is deliberately insecure in default mode. Never expose it
on the internet. Only fake accounts and fake order data are used.
"""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HOST = os.getenv("DEMOSHOP_HOST", "127.0.0.1")
PORT = int(os.getenv("DEMOSHOP_PORT", "5001"))
TEST_USERS = {"demo-alice": "alice", "demo-bob": "bob"}
ORDERS = {
    "101": {"id": "101", "owner": "alice", "item": "Demo keyboard", "total": 49},
    "102": {"id": "102", "owner": "bob", "item": "Demo mouse", "total": 19},
}
HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>DemoShop — TraceShield Test Target</title><style>
body{font:18px system-ui;background:#0f172a;color:#f8fafc;padding:80px}
main{max-width:720px;margin:auto;background:#1e293b;padding:32px;border-radius:20px}
h1{color:#38bdf8}code{color:#a5f3fc}</style></head><body>
<main><h1>DemoShop</h1><p>Local synthetic target for TraceShield AI.</p>
<p>Test route: <code>GET /api/orders/101</code> with fake bearer tokens.</p>
<p>Includes intentionally absent CSP response header for the HTTP scanner.</p>
<p><strong>Do not use real users, payments or data.</strong></p></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    secure_mode = False
    csp_enabled = False

    def send_payload(self, status, payload, content_type="application/json"):
        body = (json.dumps(payload) if isinstance(payload, (dict, list)) else payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if self.secure_mode or self.csp_enabled:
            self.send_header("Content-Security-Policy", "default-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.send_payload(200, HTML, "text/html; charset=utf-8")
            return
        if not path.startswith("/api/orders/"):
            self.send_payload(404, {"error": "not_found"})
            return

        bearer = self.headers.get("Authorization", "")
        token = bearer.removeprefix("Bearer ") if bearer.startswith("Bearer ") else ""
        user = TEST_USERS.get(token)
        if user is None:
            self.send_payload(401, {"error": "unauthorized"})
            return
        order_id = path.removeprefix("/api/orders/")
        order = ORDERS.get(order_id)
        if order is None:
            self.send_payload(404, {"error": "order_not_found"})
            return
        if self.secure_mode and order["owner"] != user:
            self.send_payload(403, {"error": "forbidden"})
            return
        # Vulnerable mode: authentication is present, but ownership is NOT checked.
        self.send_payload(200, order)


def main():
    parser = argparse.ArgumentParser(description="Local synthetic security demo")
    parser.add_argument("--secure", action="store_true", help="Enable server-side ownership checks")
    parser.add_argument("--with-csp", action="store_true", help="Include Content-Security-Policy header")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to run on (default {PORT})")
    args = parser.parse_args()
    Handler.secure_mode = args.secure
    Handler.csp_enabled = args.with_csp
    port = args.port
    mode = "PATCHED / ownership enforced" if args.secure else "VULNERABLE / BOLA demonstration"
    print(f"DemoShop at http://{HOST}:{port}/ — {mode}", flush=True)
    print("Local test only. Press Ctrl+C to stop.", flush=True)
    server = ThreadingHTTPServer((HOST, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

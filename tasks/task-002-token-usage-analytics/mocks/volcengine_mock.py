#!/usr/bin/env python3
"""Minimal mock server — no external APIs needed for this task.

This task (token usage analytics) doesn't require any mock APIs.
This server only provides a health check endpoint.
"""

import http.server
import socketserver

PORT = 18080


class MinimalHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            body = b'{"status":"ok","note":"no mock APIs needed for this task"}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MinimalHandler) as httpd:
        import sys
        print(f"[mock] Minimal health-check server on port {PORT}", file=sys.stderr)
        httpd.serve_forever()

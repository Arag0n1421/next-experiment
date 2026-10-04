#!/usr/bin/env python3
"""Loopback-only, read-only demo server with an explicit file allowlist."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "/review-map.md": ("reviews/JURY-REVIEW-MAP.md", "text/plain; charset=utf-8"),
    "/source.zip": ("dist/next-experiment-source.zip", "application/zip"),
    "/panel": ("demo/panel.html", "text/html; charset=utf-8"),
    "/panel.css": ("demo/panel.css", "text/css; charset=utf-8"),
    "/panel.js": ("demo/panel.js", "text/javascript; charset=utf-8"),
    "/evidence/panel.json": ("demo/evidence/panel.json", "application/json"),
    "/": ("demo/index.html", "text/html; charset=utf-8"),
    "/index.html": ("demo/index.html", "text/html; charset=utf-8"),
    "/style.css": ("demo/style.css", "text/css; charset=utf-8"),
    "/app.js": ("demo/app.js", "text/javascript; charset=utf-8"),
    **{f"/evidence/{name}.json": (f"demo/evidence/{name}.json", "application/json")
       for name in ("candidate", "guide-check", "decision", "manifest")},
}


def public_value(value):
    """Preserve scientific summary fields while removing workstation paths."""
    if isinstance(value, str):
        return re.sub(r"/(?:Users|Volumes|private|tmp)/[^\s\"<>]+", "[local artifact]", value)
    if isinstance(value, list):
        return [public_value(v) for v in value]
    if isinstance(value, dict):
        return {k: public_value(v) for k, v in value.items()
                if not any(term in k.lower() for term in ("token", "password", "secret", "api_key", "path"))}
    return value


def resolve_response(path: str, root: Path = ROOT):
    path = urlsplit(path).path
    if path == "/runs/benchmark/report.json":
        source = root / "runs" / "benchmark" / "report.json"
        if not source.is_file() or source.is_symlink():
            return 404, "application/json", b'{"status":"not_run"}'
        report = json.loads(source.read_text())
        summary = {k: public_value(report[k]) for k in
                   ("headline", "metrics", "limitations", "status", "evaluation_status", "methods", "comparison", "created_utc")
                   if k in report}
        return 200, "application/json", json.dumps(summary, allow_nan=False).encode()
    if path not in FILES:
        return 404, "text/plain", b"Not found\n"
    relative, content_type = FILES[path]
    file = root / relative
    if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
        return 404, "text/plain", b"Not found\n"
    return 200, content_type, file.read_bytes()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Reject cross-site browser access to this local artifact server.
        host = self.headers.get("Host", "").split(":", 1)[0]
        if host not in {"127.0.0.1", "localhost"}:
            self.send_error(403)
            return
        try:
            code, content_type, body = resolve_response(self.path)
        except (ValueError, OSError):
            code, content_type, body = 503, "application/json", b'{"status":"unavailable"}'
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=6768)
    args = parser.parse_args()
    print(f"Next Experiment: http://127.0.0.1:{args.port} (local verified replay)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()

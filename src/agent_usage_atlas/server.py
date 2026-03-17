#!/usr/bin/env python3
"""HTTP service for the live dashboard."""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
from datetime import datetime
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import time

from .cli import build_dashboard_payload
from .template import build_html
from .parsers import CLAUDE_ROOT, CODEX_ROOTS, CURSOR_ROOT


_PAYLOAD_CACHE: dict[tuple[int, str | None], tuple[dict, str, tuple[int, int, int]]] = {}
_PAYLOAD_LOCK = threading.Lock()


def _parse_int(value: str | None, default: int, minimum: int = 1, maximum: int = 3600) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _parse_range(query: str, *, default_days: int) -> tuple[int, str | None]:
    params = parse_qs(query)
    since = params.get("since", [None])[0]
    days = _parse_int(params.get("days", [None])[0], default=default_days, minimum=1, maximum=3650)
    return days, since


def _sse_encode(obj: object) -> bytes:
    payload = json.dumps(obj, ensure_ascii=False)
    return f"data: {payload}\n\n".encode("utf-8")


def _json_body(payload: object) -> tuple[bytes, str]:
    body = json.dumps(payload, ensure_ascii=False)
    return body.encode("utf-8"), hashlib.sha1(body.encode("utf-8")).hexdigest()


def _build_payload(days: int, since: str | None) -> dict:
    return build_dashboard_payload(days=days, since=since)


def _iter_payload_files():
    for root in CODEX_ROOTS:
        if root.exists():
            for path in root.rglob("*.jsonl"):
                yield path
    if CLAUDE_ROOT.exists():
        for path in CLAUDE_ROOT.rglob("*.jsonl"):
            if path.name == "sessions-index.json":
                continue
            yield path
    if CURSOR_ROOT.exists():
        for path in CURSOR_ROOT.rglob("*.jsonl"):
            if "agent-transcripts" not in str(path):
                continue
            yield path


_SIG_FILE_LIST: list[Path] = []
_SIG_FILE_LIST_TIME: float = 0.0
_SIG_RESCAN_INTERVAL: float = 30.0  # seconds between full rglob rescans


def _payload_signature() -> tuple[int, int, int]:
    global _SIG_FILE_LIST, _SIG_FILE_LIST_TIME
    now = time.monotonic()
    if not _SIG_FILE_LIST or (now - _SIG_FILE_LIST_TIME) > _SIG_RESCAN_INTERVAL:
        _SIG_FILE_LIST = list(_iter_payload_files())
        _SIG_FILE_LIST_TIME = now
    newest_mtime_ns = 0
    total_bytes = 0
    file_count = 0
    for path in _SIG_FILE_LIST:
        try:
            st = path.stat()
        except OSError:
            continue
        newest_mtime_ns = max(newest_mtime_ns, int(st.st_mtime_ns))
        total_bytes += int(st.st_size)
        file_count += 1
    return newest_mtime_ns, total_bytes, file_count


def _cached_payload(days: int, since: str | None) -> tuple[dict, str]:
    key = (days, since)
    signature = _payload_signature()
    with _PAYLOAD_LOCK:
        entry = _PAYLOAD_CACHE.get(key)
        if entry is not None:
            payload, etag, payload_sig = entry
            if payload_sig == signature:
                return payload, etag

    payload = _build_payload(days=days, since=since)
    _, etag = _json_body(payload)
    cache_entry = (payload, etag, signature)
    with _PAYLOAD_LOCK:
        _PAYLOAD_CACHE[key] = cache_entry
    return payload, etag


class DashboardHandler(BaseHTTPRequestHandler):
    default_days: int = 30
    default_since: str | None = None
    default_interval: int = 5

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler API
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._write_index()
            return
        if parsed.path == "/api/dashboard":
            self._write_dashboard(parsed.query)
            return
        if parsed.path == "/api/dashboard/stream":
            self._write_stream(parsed.query)
            return
        if parsed.path in {"/favicon.ico", "/health"}:
            if parsed.path == "/health":
                self._write_json({"status": "ok"})
                return
            self.send_error(404)
            return
        self.send_error(404, "Not Found")

    def _write_headers(self, status: int = 200, *, content_type: str, cache_control: str = "no-cache") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", cache_control)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def _write_json(self, payload: object, status: int = 200) -> None:
        body, etag = _json_body(payload)
        if status == 200 and self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.end_headers()
            return
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_index(self) -> None:
        template = build_html(None, poll_interval_ms=max(2000, self.default_interval * 1000))
        self._write_headers(
            content_type="text/html; charset=utf-8",
            cache_control="no-store",
        )
        self.wfile.write(template.encode("utf-8"))

    def _write_dashboard(self, query: str) -> None:
        days, since = _parse_range(query, default_days=self.default_days)
        if since:
            try:
                datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                self._write_json({"error": "since must be YYYY-MM-DD"}, status=400)
                return
        since = since or self.default_since
        payload, _ = _cached_payload(days=days, since=since)
        self._write_json(payload)

    def _write_stream(self, query: str) -> None:
        parsed = parse_qs(query)
        interval = _parse_int(parsed.get("interval", [None])[0], default=self.default_interval, minimum=2, maximum=60)
        days, since = _parse_range(query, default_days=self.default_days)
        if since:
            try:
                datetime.strptime(since, "%Y-%m-%d")
            except ValueError:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"since must be YYYY-MM-DD")
                return
        since = since or self.default_since

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(b": connected\n\n")
        self.wfile.flush()

        known_etag = ""
        try:
            while True:
                payload, etag = _cached_payload(days=days, since=since)
                if etag != known_etag:
                    known_etag = etag
                    self.wfile.write(_sse_encode(payload))
                    self.wfile.flush()
                time.sleep(interval)
        except (BrokenPipeError, ConnectionResetError):
            return


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    days: int = 30,
    since: str | None = None,
    interval: int = 5,
    open_browser: bool = False,
) -> None:
    if since:
        datetime.strptime(since, "%Y-%m-%d")
    DashboardHandler.default_days = days
    DashboardHandler.default_since = since
    DashboardHandler.default_interval = interval

    _cached_payload(days=days, since=since)

    server = ThreadingHTTPServer((host, port), DashboardHandler)
    url = f"http://{host}:{port}"
    print(f"Agent Usage Atlas dashboard server running at {url}")
    print(f"JSON: {url}/api/dashboard")
    print(f"SSE:  {url}/api/dashboard/stream?interval={interval}")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-usage-atlas-server",
        description="Serve a local dashboard from agent logs.",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--since", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--interval", type=int, default=5)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    run_server(
        host=args.host,
        port=args.port,
        days=args.days,
        since=args.since,
        interval=args.interval,
    )


if __name__ == "__main__":
    main()

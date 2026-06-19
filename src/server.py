import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Settings
from dashboard import render_dashboard
from main import run_once
from store import ProcessedMailStore

log = logging.getLogger("job-mail-agent")
_check_lock = threading.Lock()


def _load_dashboard_context() -> tuple[str, dict]:
    settings = Settings.load()
    store = ProcessedMailStore(settings.data_dir / "processed.db")
    stats = store.get_stats()
    recent_emails = store.get_recent_emails()
    recent_runs = store.get_recent_runs()

    host = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not host:
        host = "http://localhost:10000"

    settings_info = {
        "email_address": settings.email_address,
        "alert_email": settings.alert_email,
        "your_name": settings.your_name,
        "groq_model": settings.groq_model,
        "trigger_url": f"{host}/check",
    }

    page = render_dashboard(
        settings_info,
        stats,
        recent_emails,
        recent_runs,
    )
    return page, stats


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info("%s - %s", self.address_string(), format % args)

    def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, body: str, content_type: str = "text/plain") -> None:
        self._send_bytes(code, body.encode(), content_type)

    def _run_check(self) -> tuple[int, str]:
        if not _check_lock.acquire(blocking=False):
            return 429, "Check already running"

        try:
            settings = Settings.load()
            result = run_once(settings)
            return 200, result.message
        except Exception as exc:
            log.exception("Check failed")
            return 500, f"Error: {exc}"
        finally:
            _check_lock.release()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/dashboard"):
            try:
                page, _ = _load_dashboard_context()
                self._send_text(200, page, "text/html; charset=utf-8")
            except Exception as exc:
                log.exception("Dashboard failed")
                self._send_text(500, f"Dashboard error: {exc}")
            return

        if path == "/health":
            self._send_text(200, "OK")
            return

        if path == "/api/stats":
            try:
                _, stats = _load_dashboard_context()
                store = ProcessedMailStore(Settings.load().data_dir / "processed.db")
                payload = {
                    "stats": stats,
                    "recent_emails": store.get_recent_emails(10),
                    "recent_runs": store.get_recent_runs(5),
                }
                self._send_text(200, json.dumps(payload), "application/json")
            except Exception as exc:
                self._send_text(500, json.dumps({"error": str(exc)}), "application/json")
            return

        if path == "/check":
            code, message = self._run_check()
            self._send_text(code, message)
            return

        self._send_text(404, "Not found")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    port = int(os.getenv("PORT", "10000"))
    log.info("Mail Checker dashboard running on port %d", port)
    HTTPServer(("0.0.0.0", port), RequestHandler).serve_forever()


if __name__ == "__main__":
    main()

import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Settings
from dashboard import render_dashboard
from main import run_once
from push_service import PushSubscriptionStore, VapidKeys, WebPushNotifier
from store import ProcessedMailStore

log = logging.getLogger("job-mail-agent")
_check_lock = threading.Lock()

MANIFEST = {
    "name": "Mail Checker",
    "short_name": "Mail Checker",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f5f5f7",
    "theme_color": "#111111",
    "icons": [
        {"src": "/app-icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
    ],
}

SERVICE_WORKER = """
self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (err) {
    data = { title: 'Mail Checker', body: event.data ? event.data.text() : '' };
  }

  const title = data.title || 'Mail Checker';
  const options = {
    body: data.body || 'New mail check update',
    badge: '/app-icon.svg',
    icon: '/app-icon.svg',
    data: { url: data.url || '/' }
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(clients.openWindow(url));
});
""".strip()

APP_ICON = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="56" fill="#111"/>
  <rect x="45" y="68" width="166" height="120" rx="26" fill="#f5f5f7"/>
  <path d="M61 87l67 52 67-52" fill="none" stroke="#111" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="190" cy="66" r="28" fill="#30d158"/>
</svg>
""".strip()


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


def _send_push_for_result(settings: Settings, manual: bool, message: str, alerts: int) -> None:
    if not manual and alerts <= 0:
        return

    notifier = WebPushNotifier(settings.data_dir, settings.alert_email)
    if manual:
        title = "Mail check finished"
        body = message
    else:
        title = "Important job mail found"
        body = f"{alerts} important email(s) need your attention."

    sent = notifier.send(title, body, "/")
    log.info("Sent %d web push notification(s).", sent)


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

    def _send_json(self, code: int, payload: dict) -> None:
        self._send_text(code, json.dumps(payload), "application/json")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/dashboard", "/health"):
            self.send_response(200)
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def _run_check(self, manual: bool = False) -> tuple[int, str]:
        if not _check_lock.acquire(blocking=False):
            return 429, "Check already running"

        try:
            settings = Settings.load()
            result = run_once(settings)
            _send_push_for_result(settings, manual, result.message, result.alerts_sent)
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

        if path == "/manifest.json":
            self._send_text(200, json.dumps(MANIFEST), "application/manifest+json")
            return

        if path == "/service-worker.js":
            self._send_text(200, SERVICE_WORKER, "application/javascript")
            return

        if path == "/app-icon.svg":
            self._send_text(200, APP_ICON, "image/svg+xml")
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

        if path == "/api/push/public-key":
            try:
                settings = Settings.load()
                _, public_key = VapidKeys(settings.data_dir).load_or_create()
                self._send_json(200, {"publicKey": public_key})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if path == "/check":
            params = parse_qs(parsed.query)
            manual = params.get("source", [""])[0] == "manual"
            code, message = self._run_check(manual)
            self._send_text(code, message)
            return

        self._send_text(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/push/subscribe":
            try:
                settings = Settings.load()
                subscription = self._read_json()
                count = PushSubscriptionStore(settings.data_dir).add(subscription)
                self._send_json(200, {"ok": True, "subscriptions": count})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})
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

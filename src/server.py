import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Settings
from main import run_once

log = logging.getLogger("job-mail-agent")
_check_lock = threading.Lock()


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        log.info("%s - %s", self.address_string(), format % args)

    def _send(self, code: int, body: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self._send(200, "OK")
            return

        if path == "/check":
            params = parse_qs(urlparse(self.path).query)
            secret = params.get("secret", [""])[0]
            expected = os.getenv("CRON_SECRET", "")

            if not expected or secret != expected:
                self._send(401, "Unauthorized")
                return

            if not _check_lock.acquire(blocking=False):
                self._send(429, "Check already running")
                return

            try:
                settings = Settings.load()
                alerts = run_once(settings)
                self._send(200, f"OK alerts={alerts}")
            except Exception as exc:
                log.exception("Check failed")
                self._send(500, f"Error: {exc}")
            finally:
                _check_lock.release()
            return

        self._send(404, "Not found")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    port = int(os.getenv("PORT", "10000"))
    log.info("Mail Checker web server listening on port %d", port)
    HTTPServer(("0.0.0.0", port), RequestHandler).serve_forever()


if __name__ == "__main__":
    main()

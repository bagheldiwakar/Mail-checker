import requests

from classifier import ClassificationResult
from config import Settings
from email_fetcher import IncomingMail


class NtfyNotifier:
    TITLES = {
        "recruiter_outreach": "Recruiter reached out!",
        "interview_invite": "Interview invitation!",
        "test_round": "Test round received!",
        "selected": "Application update!",
        "rejection": "Application result",
        "follow_up": "Recruiter follow-up",
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.topic = settings.ntfy_topic
        self.server = settings.ntfy_server.rstrip("/")

    def enabled(self) -> bool:
        return bool(self.topic)

    def _send(self, title: str, message: str, priority: str = "default") -> None:
        if not self.enabled():
            return

        url = f"{self.server}/{self.topic}"
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": "email",
        }
        requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10).raise_for_status()

    def notify(self, mail: IncomingMail, result: ClassificationResult) -> None:
        title = self.TITLES.get(result.category, "Important job email")
        priority = "high" if result.urgency in ("high", "medium") else "default"
        message = (
            f"From: {mail.sender}\n"
            f"Subject: {mail.subject}\n"
            f"Category: {result.category}\n\n"
            f"{result.reason}"
        )
        self._send(title, message, priority)

    def notify_status(self, title: str, message: str) -> None:
        self._send(title, message, "default")

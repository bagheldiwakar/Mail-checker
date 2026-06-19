import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    email_address: str
    email_password: str
    imap_server: str
    imap_port: int
    smtp_server: str
    smtp_port: int
    alert_email: str
    groq_api_key: str
    groq_model: str
    poll_interval: int
    max_emails_per_check: int
    groq_request_delay_seconds: float
    your_name: str
    notifier_mode: str
    ntfy_topic: str
    ntfy_server: str
    is_render: bool
    data_dir: Path

    @classmethod
    def load(cls) -> "Settings":
        missing = []
        email = os.getenv("EMAIL_ADDRESS", "").strip()
        password = os.getenv("EMAIL_PASSWORD", "").strip()
        api_key = os.getenv("GROQ_API_KEY", "").strip()

        if not email:
            missing.append("EMAIL_ADDRESS")
        if not password:
            missing.append("EMAIL_PASSWORD")
        if not api_key:
            missing.append("GROQ_API_KEY")

        if missing:
            raise ValueError(
                f"Missing required env vars: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in your values."
            )

        is_render = bool(os.getenv("RENDER"))
        data_dir = ROOT / "data"
        data_dir.mkdir(exist_ok=True)

        alert_email = os.getenv("ALERT_EMAIL", "").strip() or email
        notifier_mode = os.getenv("NOTIFIER_MODE", "auto").strip().lower()

        return cls(
            email_address=email,
            email_password=password,
            imap_server=os.getenv("IMAP_SERVER", "imap.gmail.com").strip(),
            imap_port=int(os.getenv("IMAP_PORT", "993")),
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            alert_email=alert_email,
            groq_api_key=api_key,
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
            poll_interval=int(os.getenv("POLL_INTERVAL", "120")),
            max_emails_per_check=int(os.getenv("MAX_EMAILS_PER_CHECK", "5")),
            groq_request_delay_seconds=float(os.getenv("GROQ_REQUEST_DELAY_SECONDS", "2")),
            your_name=os.getenv("YOUR_NAME", "").strip(),
            notifier_mode=notifier_mode,
            ntfy_topic=os.getenv("NTFY_TOPIC", "").strip(),
            ntfy_server=os.getenv("NTFY_SERVER", "https://ntfy.sh").strip(),
            is_render=is_render,
            data_dir=data_dir,
        )

    def resolved_notifier_mode(self) -> str:
        if self.notifier_mode != "auto":
            return self.notifier_mode
        if self.ntfy_topic:
            return "ntfy"
        if self.is_render:
            return "email"
        if os.name == "nt":
            return "desktop"
        return "email"

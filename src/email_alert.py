import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from classifier import ClassificationResult
from config import Settings
from email_fetcher import IncomingMail


class EmailAlertNotifier:
    TITLES = {
        "recruiter_outreach": "Recruiter reached out!",
        "interview_invite": "Interview invitation!",
        "follow_up": "Recruiter follow-up",
    }

    def __init__(self, settings: Settings):
        self.settings = settings

    def notify(self, mail: IncomingMail, result: ClassificationResult) -> None:
        title = self.TITLES.get(result.category, "Important job email")
        subject = f"[Job Alert] {title} — {mail.subject}"

        body = f"""{title}

From: {mail.sender} <{mail.sender_email}>
Subject: {mail.subject}
Category: {result.category}
Urgency: {result.urgency}

Why this matters:
{result.reason}

---
This alert was sent by Mail Checker running on Render.
"""

        msg = MIMEMultipart()
        msg["From"] = self.settings.email_address
        msg["To"] = self.settings.alert_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self.settings.smtp_server, self.settings.smtp_port) as server:
            server.starttls()
            server.login(self.settings.email_address, self.settings.email_password)
            server.send_message(msg)

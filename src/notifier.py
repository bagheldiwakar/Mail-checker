from classifier import ClassificationResult
from config import Settings
from email_alert import EmailAlertNotifier
from email_fetcher import IncomingMail
from ntfy_alert import NtfyNotifier


class DesktopNotifier:
    URGENCY_SOUNDS = {
        "high": (1000, 400),
        "medium": (800, 300),
        "low": (600, 200),
    }

    TITLES = {
        "recruiter_outreach": "Recruiter reached out!",
        "interview_invite": "Interview invitation!",
        "follow_up": "Recruiter follow-up",
    }

    def notify(self, mail: IncomingMail, result: ClassificationResult) -> None:
        import winsound

        from winotify import Notification, audio

        title = self.TITLES.get(result.category, "Important job email")
        message = f"{mail.sender}\n{mail.subject}\n\n{result.reason}"

        toast = Notification(
            app_id="Job Mail Agent",
            title=title,
            msg=message[:240],
            duration="long",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()

        freq, duration = self.URGENCY_SOUNDS.get(result.urgency, (800, 300))
        winsound.Beep(freq, duration)
        if result.urgency == "high":
            winsound.Beep(freq + 200, duration)


def get_notifier(settings: Settings):
    mode = settings.resolved_notifier_mode()
    if mode == "ntfy":
        return NtfyNotifier(settings)
    if mode == "desktop":
        return DesktopNotifier()
    return EmailAlertNotifier(settings)

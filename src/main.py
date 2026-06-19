import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from classifier import JobMailClassifier
from config import Settings
from email_fetcher import EmailFetcher
from notifier import get_notifier
from store import ProcessedMailStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("job-mail-agent")


def run_once(settings: Settings) -> int:
    store = ProcessedMailStore(settings.data_dir / "processed.db")
    fetcher = EmailFetcher(
        settings.email_address,
        settings.email_password,
        settings.imap_server,
        settings.imap_port,
    )
    classifier = JobMailClassifier(
        settings.groq_api_key,
        settings.groq_model,
        settings.your_name,
    )
    notifier = get_notifier(settings)
    mode = settings.resolved_notifier_mode()

    try:
        mails = fetcher.fetch_unseen()
        if not mails:
            log.info("No new unread emails.")
            return 0

        log.info("Found %d unread email(s). Classifying with Groq...", len(mails))
        alerts = 0

        for mail in mails:
            if store.is_processed(mail.message_id):
                fetcher.mark_as_seen(mail.uid)
                continue

            try:
                result = classifier.classify(mail)
            except Exception as exc:
                log.error("Failed to classify '%s': %s", mail.subject, exc)
                continue

            store.mark_processed(
                mail.message_id,
                mail.subject,
                mail.sender,
                result.is_interesting,
            )

            if settings.is_render or mode == "email":
                fetcher.mark_as_seen(mail.uid)

            if result.is_interesting:
                alerts += 1
                log.info(
                    "ALERT [%s] %s — %s",
                    result.category,
                    mail.subject,
                    result.reason,
                )
                notifier.notify(mail, result)
            else:
                log.info("Skipped: %s (%s)", mail.subject, result.reason)

        return alerts
    finally:
        fetcher.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Mail Agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single inbox check and exit (used by Render cron)",
    )
    args = parser.parse_args()

    try:
        settings = Settings.load()
    except ValueError as exc:
        log.error("%s", exc)
        sys.exit(1)

    mode = settings.resolved_notifier_mode()
    log.info("Notifier mode: %s", mode)
    log.info("Groq model: %s", settings.groq_model)
    log.info("Monitoring inbox: %s", settings.email_address)

    if args.once:
        try:
            alerts = run_once(settings)
            log.info("Done. Sent %d alert(s).", alerts)
        except Exception as exc:
            log.error("Error during check: %s", exc)
            sys.exit(1)
        return

    log.info("Job Mail Agent started. Checking every %ds.", settings.poll_interval)

    while True:
        try:
            alerts = run_once(settings)
            if alerts:
                log.info("Sent %d alert(s) this cycle.", alerts)
        except KeyboardInterrupt:
            log.info("Stopping agent.")
            break
        except Exception as exc:
            log.error("Error during check: %s", exc)

        time.sleep(settings.poll_interval)


if __name__ == "__main__":
    main()

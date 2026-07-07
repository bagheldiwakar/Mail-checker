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
from results import RunResult
from store import ProcessedMailStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("job-mail-agent")


def run_once(settings: Settings) -> RunResult:
    store = ProcessedMailStore(settings.data_dir / "processed.db")
    run_id = store.start_check_run()
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

    emails_found = 0
    emails_processed = 0
    alerts = 0
    skipped = 0
    errors = 0
    alert_summaries: list[dict] = []

    try:
        mails = fetcher.fetch_unseen(settings.max_emails_per_check)
        emails_found = len(mails)

        if not mails:
            log.info("No new unread emails.")
            store.finish_check_run(run_id, 0, 0, 0)
            return RunResult(0, 0, 0, 0, 0, "No new unread emails.")

        log.info("Found %d unread email(s) from today. Applying privacy guard...", len(mails))

        for index, mail in enumerate(mails):
            if mail.privacy_skip:
                if not store.is_processed(mail.message_id):
                    store.mark_processed(
                        mail.message_id,
                        "[Sensitive email skipped]",
                        mail.sender,
                        False,
                        "privacy_skip",
                        mail.privacy_reason,
                        gmail_thread_id=mail.gmail_thread_id,
                    )
                skipped += 1
                log.info("Privacy skipped sensitive email from %s before reading body.", mail.sender)
                continue

            if store.is_processed(mail.message_id):
                fetcher.mark_as_seen(mail.uid)
                continue

            try:
                result = classifier.classify(mail)
            except Exception as exc:
                errors += 1
                log.error("Failed to classify '%s': %s", mail.subject, exc)
                continue

            emails_processed += 1
            store.mark_processed(
                mail.message_id,
                mail.subject,
                mail.sender,
                result.is_interesting,
                result.category,
                result.reason,
                result.company_name,
                result.job_profile,
                mail.gmail_thread_id,
            )

            if settings.is_render or mode == "email":
                fetcher.mark_as_seen(mail.uid)

            if result.is_interesting:
                alerts += 1
                alert_summaries.append(
                    {
                        "subject": mail.subject,
                        "sender": mail.sender,
                        "category": result.category,
                        "reason": result.reason,
                        "company_name": result.company_name,
                        "job_profile": result.job_profile,
                        "gmail_thread_id": mail.gmail_thread_id,
                    }
                )
                log.info(
                    "ALERT [%s] %s - %s",
                    result.category,
                    mail.subject,
                    result.reason,
                )
                try:
                    notifier.notify(mail, result)
                except Exception as exc:
                    errors += 1
                    log.error("Failed to send alert for '%s': %s", mail.subject, exc)
            else:
                skipped += 1
                log.info("Skipped: %s (%s)", mail.subject, result.reason)

            if settings.groq_request_delay_seconds > 0 and index < len(mails) - 1:
                time.sleep(settings.groq_request_delay_seconds)

        message = (
            f"Processed {emails_processed} email(s), sent {alerts} alert(s), "
            f"skipped {skipped}."
        )
        store.finish_check_run(run_id, emails_found, emails_processed, alerts)
        return RunResult(emails_found, emails_processed, alerts, skipped, errors, message, alert_summaries)
    except Exception as exc:
        store.finish_check_run(run_id, emails_found, emails_processed, alerts, "error", str(exc))
        raise
    finally:
        fetcher.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Job Mail Agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single inbox check and exit",
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
            result = run_once(settings)
            log.info("Done. %s", result.message)
        except Exception as exc:
            log.error("Error during check: %s", exc)
            sys.exit(1)
        return

    log.info("Job Mail Agent started. Checking every %ds.", settings.poll_interval)

    while True:
        try:
            result = run_once(settings)
            if result.alerts_sent:
                log.info("Sent %d alert(s) this cycle.", result.alerts_sent)
        except KeyboardInterrupt:
            log.info("Stopping agent.")
            break
        except Exception as exc:
            log.error("Error during check: %s", exc)

        time.sleep(settings.poll_interval)


if __name__ == "__main__":
    main()

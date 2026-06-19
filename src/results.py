from dataclasses import dataclass


@dataclass
class RunResult:
    emails_found: int
    emails_processed: int
    alerts_sent: int
    skipped: int
    errors: int
    message: str

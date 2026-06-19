from dataclasses import dataclass, field


@dataclass
class RunResult:
    emails_found: int
    emails_processed: int
    alerts_sent: int
    skipped: int
    errors: int
    message: str
    alert_summaries: list[dict] = field(default_factory=list)

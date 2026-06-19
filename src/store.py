import sqlite3
from pathlib import Path


class ProcessedMailStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    message_id TEXT PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    is_interesting INTEGER,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def is_processed(self, message_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_emails WHERE message_id = ?",
                (message_id,),
            ).fetchone()
        return row is not None

    def mark_processed(
        self,
        message_id: str,
        subject: str,
        sender: str,
        is_interesting: bool,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_emails
                (message_id, subject, sender, is_interesting)
                VALUES (?, ?, ?, ?)
                """,
                (message_id, subject, sender, int(is_interesting)),
            )

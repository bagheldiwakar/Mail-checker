import sqlite3
from pathlib import Path


class ProcessedMailStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    message_id TEXT PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    is_interesting INTEGER,
                    category TEXT,
                    reason TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS check_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    finished_at TEXT,
                    emails_found INTEGER DEFAULT 0,
                    emails_processed INTEGER DEFAULT 0,
                    alerts_sent INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running',
                    error TEXT
                )
                """
            )
            self._ensure_columns(conn)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(processed_emails)").fetchall()
        }
        if "category" not in columns:
            conn.execute("ALTER TABLE processed_emails ADD COLUMN category TEXT")
        if "reason" not in columns:
            conn.execute("ALTER TABLE processed_emails ADD COLUMN reason TEXT")
        if "company_name" not in columns:
            conn.execute("ALTER TABLE processed_emails ADD COLUMN company_name TEXT")
        if "job_profile" not in columns:
            conn.execute("ALTER TABLE processed_emails ADD COLUMN job_profile TEXT")
        if "dismissed_at" not in columns:
            conn.execute("ALTER TABLE processed_emails ADD COLUMN dismissed_at TEXT")

    def is_processed(self, message_id: str) -> bool:
        with self._connect() as conn:
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
        category: str = "",
        reason: str = "",
        company_name: str = "",
        job_profile: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_emails
                (message_id, subject, sender, is_interesting, category, reason, company_name, job_profile)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    subject,
                    sender,
                    int(is_interesting),
                    category,
                    reason,
                    company_name,
                    job_profile,
                ),
            )

    def start_check_run(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO check_runs (status) VALUES ('running')"
            )
            return int(cursor.lastrowid)

    def finish_check_run(
        self,
        run_id: int,
        emails_found: int,
        emails_processed: int,
        alerts_sent: int,
        status: str = "success",
        error: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE check_runs
                SET finished_at = CURRENT_TIMESTAMP,
                    emails_found = ?,
                    emails_processed = ?,
                    alerts_sent = ?,
                    status = ?,
                    error = ?
                WHERE id = ?
                """,
                (emails_found, emails_processed, alerts_sent, status, error, run_id),
            )

    def get_stats(self) -> dict:
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_emails,
                    COALESCE(SUM(is_interesting), 0) AS total_alerts,
                    COALESCE(SUM(CASE WHEN is_interesting = 0 THEN 1 ELSE 0 END), 0) AS total_skipped
                FROM processed_emails
                """
            ).fetchone()
            runs = conn.execute(
                """
                SELECT COUNT(*) AS total_runs
                FROM check_runs
                WHERE status = 'success'
                """
            ).fetchone()
            last_run = conn.execute(
                """
                SELECT *
                FROM check_runs
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

        return {
            "total_emails": totals["total_emails"],
            "total_alerts": totals["total_alerts"],
            "total_skipped": totals["total_skipped"],
            "total_runs": runs["total_runs"],
            "last_run": dict(last_run) if last_run else None,
        }

    def get_recent_emails(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT message_id, subject, sender, is_interesting, category, reason,
                       company_name, job_profile, processed_at
                FROM processed_emails
                ORDER BY processed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_active_alerts(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT message_id, subject, sender, category, reason,
                       company_name, job_profile, processed_at
                FROM processed_emails
                WHERE is_interesting = 1
                  AND dismissed_at IS NULL
                ORDER BY processed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def dismiss_alert(self, message_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE processed_emails
                SET dismissed_at = CURRENT_TIMESTAMP
                WHERE message_id = ?
                  AND is_interesting = 1
                """,
                (message_id,),
            )
            return cursor.rowcount > 0

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, started_at, finished_at, emails_found, emails_processed,
                       alerts_sent, status, error
                FROM check_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

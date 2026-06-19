import email
import imaplib
from dataclasses import dataclass
from datetime import date
from email.header import decode_header
from email.utils import parseaddr


@dataclass
class IncomingMail:
    message_id: str
    subject: str
    sender: str
    sender_email: str
    body: str
    uid: str


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded).strip()


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and part.get_content_disposition() != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" and part.get_content_disposition() != "attachment":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return ""

    payload = msg.get_payload(decode=True)
    if not payload:
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _imap_date(value: date) -> str:
    return value.strftime("%d-%b-%Y")


class EmailFetcher:
    def __init__(self, address: str, password: str, server: str, port: int):
        self.address = address
        self.password = password
        self.server = server
        self.port = port
        self._connection: imaplib.IMAP4_SSL | None = None

    def _connect(self) -> imaplib.IMAP4_SSL:
        if self._connection is None:
            self._connection = imaplib.IMAP4_SSL(self.server, self.port)
            self._connection.login(self.address, self.password)
            self._connection.select("INBOX")
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.logout()
            except Exception:
                pass
            self._connection = None

    def fetch_unseen(self, limit: int = 20) -> list[IncomingMail]:
        connection = self._connect()

        status, data = connection.search(None, "UNSEEN", "SINCE", _imap_date(date.today()))
        if status != "OK" or not data or not data[0]:
            return []

        uids = data[0].split()
        uids = uids[-limit:]

        mails: list[IncomingMail] = []
        for uid in uids:
            status, msg_data = connection.fetch(uid, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue

            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            message_id = msg.get("Message-ID", f"uid-{uid.decode()}").strip()
            subject = _decode_header_value(msg.get("Subject"))
            sender_raw = _decode_header_value(msg.get("From"))
            sender_name, sender_email = parseaddr(sender_raw)
            sender = sender_name or sender_email or sender_raw
            body = _extract_body(msg).strip()

            mails.append(
                IncomingMail(
                    message_id=message_id,
                    subject=subject,
                    sender=sender,
                    sender_email=sender_email,
                    body=body[:8000],
                    uid=uid.decode(),
                )
            )

        return mails

    def mark_as_seen(self, uid: str) -> None:
        connection = self._connect()
        connection.store(uid.encode(), "+FLAGS", "\\Seen")

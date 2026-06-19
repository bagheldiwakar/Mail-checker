import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush


log = logging.getLogger("job-mail-agent")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _private_key_to_encoded_der(private_key) -> str:
    return _b64url(
        private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def _pem_to_encoded_der(private_pem: str) -> str:
    private_key = serialization.load_pem_private_key(private_pem.encode("ascii"), password=None)
    return _private_key_to_encoded_der(private_key)


class VapidKeys:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.private_key_path = data_dir / "vapid_private_key.pem"
        self.public_key_path = data_dir / "vapid_public_key.txt"

    def load_or_create(self) -> tuple[str, str]:
        env_private = os.getenv("VAPID_PRIVATE_KEY", "").replace("\\n", "\n").strip()
        env_public = os.getenv("VAPID_PUBLIC_KEY", "").strip()
        if env_private and env_public:
            if env_private.startswith("-----BEGIN"):
                env_private = _pem_to_encoded_der(env_private)
            return env_private, env_public

        if self.private_key_path.exists() and self.public_key_path.exists():
            private_key = self.private_key_path.read_text().strip()
            if private_key.startswith("-----BEGIN"):
                private_key = _pem_to_encoded_der(private_key)
                self.private_key_path.write_text(private_key)
            return private_key, self.public_key_path.read_text().strip()

        private_key = ec.generate_private_key(ec.SECP256R1())
        private_value = _private_key_to_encoded_der(private_key)
        public_key = _b64url(
            private_key.public_key().public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint,
            )
        )

        self.data_dir.mkdir(exist_ok=True)
        self.private_key_path.write_text(private_value)
        self.public_key_path.write_text(public_key)
        return private_value, public_key


class PushSubscriptionStore:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "push_subscriptions.json"

    def all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict) and item.get("endpoint")]

    def add(self, subscription: dict[str, Any]) -> int:
        subscriptions = self.all()
        endpoint = subscription.get("endpoint")
        subscriptions = [item for item in subscriptions if item.get("endpoint") != endpoint]
        subscriptions.append(subscription)
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(subscriptions, indent=2))
        return len(subscriptions)

    def replace_all(self, subscriptions: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(subscriptions, indent=2))


class WebPushNotifier:
    def __init__(self, data_dir: Path, contact_email: str):
        self.store = PushSubscriptionStore(data_dir)
        self.private_key, self.public_key = VapidKeys(data_dir).load_or_create()
        self.claims = {"sub": f"mailto:{contact_email}"}

    def send(self, title: str, body: str, url: str = "/") -> int:
        payload = json.dumps({"title": title, "body": body, "url": url})
        sent = 0
        active_subscriptions = []

        for subscription in self.store.all():
            try:
                webpush(
                    subscription_info=subscription,
                    data=payload,
                    vapid_private_key=self.private_key,
                    vapid_claims=self.claims,
                    timeout=10,
                    ttl=3600,
                )
                sent += 1
                active_subscriptions.append(subscription)
            except WebPushException as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in (404, 410):
                    continue
                log.warning("Failed to send web push notification: %s", exc)
                active_subscriptions.append(subscription)

        self.store.replace_all(active_subscriptions)
        return sent

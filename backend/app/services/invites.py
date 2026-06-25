import base64
import hashlib
import hmac
import json

from app.config import Settings


def create_invite_token(organization_id: int, invite_version: int, settings: Settings) -> str:
    payload = json.dumps(
        {"organizationId": organization_id, "inviteVersion": invite_version},
        separators=(",", ":"),
    ).encode()
    encoded = _encode(payload)
    signature = hmac.new(
        settings.auth_secret.get_secret_value().encode(),
        encoded.encode(),
        hashlib.sha256,
    ).digest()
    return f"{encoded}.{_encode(signature)}"


def parse_invite_token(token: str, settings: Settings) -> tuple[int, int] | None:
    try:
        encoded, raw_signature = token.split(".", 1)
        expected = hmac.new(
            settings.auth_secret.get_secret_value().encode(),
            encoded.encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(raw_signature), expected):
            return None
        payload = json.loads(_decode(encoded))
        return int(payload["organizationId"]), int(payload["inviteVersion"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

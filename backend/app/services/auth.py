import base64
import hashlib
import hmac
import json
import time

from fastapi import Cookie, Depends, HTTPException, status

from app.config import Settings, get_settings


ADMIN_COOKIE_NAME = "teamtracks_admin"


def create_admin_token(settings: Settings, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = {"exp": issued_at + settings.admin_session_hours * 3600, "role": "admin"}
    encoded = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(
        settings.admin_session_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256
    ).digest()
    return f"{encoded}.{_encode(signature)}"


def is_valid_admin_token(token: str | None, settings: Settings, now: int | None = None) -> bool:
    if not token:
        return False
    try:
        encoded, raw_signature = token.split(".", 1)
        expected = hmac.new(
            settings.admin_session_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_decode(raw_signature), expected):
            return False
        payload = json.loads(_decode(encoded))
        return payload.get("role") == "admin" and int(payload["exp"]) > int(time.time() if now is None else now)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


def require_admin_session(
    token: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
    settings: Settings = Depends(get_settings),
) -> None:
    if not is_valid_admin_token(token, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin authentication required")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

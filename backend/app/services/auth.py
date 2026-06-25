import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import ORGANIZATION_SESSION_MAX_AGE_SECONDS, Settings, get_settings
from app.db.session import get_db
from app.models.browser_session import BrowserSession, SessionOrganizationAccess
from app.models.organization import Organization


BROWSER_SESSION_COOKIE_NAME = "teamtracks_session"
PLATFORM_ADMIN_COOKIE_NAME = "teamtracks_platform_admin"


@dataclass(frozen=True)
class BrowserSessionContext:
    session: BrowserSession
    raw_token: str


@dataclass(frozen=True)
class OrganizationAccessContext:
    session: BrowserSession
    access: SessionOrganizationAccess
    organization: Organization


def get_auth_now() -> datetime:
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_browser_session(
    db: Session,
    response: Response,
    settings: Settings,
    now: datetime,
) -> BrowserSessionContext:
    raw_token = secrets.token_urlsafe(48)
    browser_session = BrowserSession(
        token_hash=hash_session_token(raw_token),
        expires_at=now + timedelta(seconds=ORGANIZATION_SESSION_MAX_AGE_SECONDS),
    )
    db.add(browser_session)
    db.flush()
    set_browser_session_cookie(response, raw_token, settings)
    return BrowserSessionContext(session=browser_session, raw_token=raw_token)


def get_optional_browser_session(
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias=BROWSER_SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    now: datetime = Depends(get_auth_now),
) -> BrowserSessionContext | None:
    if not session_cookie:
        return None

    browser_session = db.scalar(
        select(BrowserSession)
        .where(BrowserSession.token_hash == hash_session_token(session_cookie))
        .options(
            selectinload(BrowserSession.organization_accesses).selectinload(
                SessionOrganizationAccess.organization
            )
        )
    )
    if browser_session is None:
        delete_browser_session_cookie(response)
        return None

    if _as_utc(browser_session.expires_at) <= now:
        db.delete(browser_session)
        db.commit()
        delete_browser_session_cookie(response)
        return None

    browser_session.expires_at = now + timedelta(seconds=ORGANIZATION_SESSION_MAX_AGE_SECONDS)
    db.commit()
    set_browser_session_cookie(response, session_cookie, settings)
    return BrowserSessionContext(session=browser_session, raw_token=session_cookie)


def require_user_access(
    organization_id: int,
    browser_context: BrowserSessionContext | None = Depends(get_optional_browser_session),
) -> OrganizationAccessContext:
    if browser_context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organization login required")

    access = next(
        (
            item
            for item in browser_context.session.organization_accesses
            if item.organization_id == organization_id
        ),
        None,
    )
    if access is None or access.user_auth_version != access.organization.user_auth_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organization login required")

    return OrganizationAccessContext(
        session=browser_context.session,
        access=access,
        organization=access.organization,
    )


def require_organization_admin_access(
    access_context: OrganizationAccessContext = Depends(require_user_access),
) -> OrganizationAccessContext:
    if access_context.access.admin_auth_version != access_context.organization.admin_auth_version:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin login required")
    return access_context


def set_browser_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        BROWSER_SESSION_COOKIE_NAME,
        token,
        max_age=ORGANIZATION_SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def delete_browser_session_cookie(response: Response) -> None:
    response.delete_cookie(BROWSER_SESSION_COOKIE_NAME, path="/")


def create_platform_admin_token(settings: Settings, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    payload = {"exp": issued_at + settings.platform_admin_session_hours * 3600, "role": "platform_admin"}
    encoded = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(
        settings.auth_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256
    ).digest()
    return f"{encoded}.{_encode(signature)}"


def is_valid_platform_admin_token(token: str | None, settings: Settings, now: int | None = None) -> bool:
    if not token:
        return False
    try:
        encoded, raw_signature = token.split(".", 1)
        expected = hmac.new(
            settings.auth_secret.get_secret_value().encode(), encoded.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_decode(raw_signature), expected):
            return False
        payload = json.loads(_decode(encoded))
        return payload.get("role") == "platform_admin" and int(payload["exp"]) > int(
            time.time() if now is None else now
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


def require_platform_admin_session(
    token: str | None = Cookie(default=None, alias=PLATFORM_ADMIN_COOKIE_NAME),
    settings: Settings = Depends(get_settings),
) -> None:
    if not is_valid_platform_admin_token(token, settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Platform admin authentication required",
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


# Compatibility aliases for the global admin routes until Phase 4 removes them.
ADMIN_COOKIE_NAME = PLATFORM_ADMIN_COOKIE_NAME
create_admin_token = create_platform_admin_token
is_valid_admin_token = is_valid_platform_admin_token
require_admin_session = require_platform_admin_session

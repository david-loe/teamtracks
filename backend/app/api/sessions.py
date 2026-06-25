from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.db.session import get_db
from app.models.browser_session import BrowserSession, SessionOrganizationAccess
from app.models.organization import Organization
from app.schemas.session import BrowserSessionRead, PasswordLoginRequest, SessionOrganizationRead
from app.services.auth import (
    BrowserSessionContext,
    OrganizationAccessContext,
    create_browser_session,
    delete_browser_session_cookie,
    get_auth_now,
    get_optional_browser_session,
    require_user_access,
)
from app.services.login_rate_limit import (
    check_login_allowed,
    record_login_failure,
    reset_login_failures,
)
from app.services.passwords import verify_password


router = APIRouter(tags=["organization-auth"])


@router.get("/api/session", response_model=BrowserSessionRead)
def get_session(
    browser_context: BrowserSessionContext | None = Depends(get_optional_browser_session),
) -> BrowserSessionRead:
    return _serialize_session(browser_context.session if browser_context is not None else None)


@router.post("/api/organizations/{organization_id}/session", response_model=BrowserSessionRead)
def login_to_organization(
    organization_id: int,
    payload: PasswordLoginRequest,
    request: Request,
    response: Response,
    browser_context: BrowserSessionContext | None = Depends(get_optional_browser_session),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    now: datetime = Depends(get_auth_now),
) -> BrowserSessionRead:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    rate_limit_key = _rate_limit_key(request, organization_id, "user")
    check_login_allowed(rate_limit_key)
    if not verify_password(organization.user_password_hash, payload.password):
        record_login_failure(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    reset_login_failures(rate_limit_key)

    if browser_context is None:
        browser_context = create_browser_session(db, response, settings, now)

    grant_organization_user_access(db, browser_context.session, organization)
    db.commit()
    return load_and_serialize_session(db, browser_context.session.id)


@router.post("/api/organizations/{organization_id}/admin/session", response_model=BrowserSessionRead)
def login_as_organization_admin(
    organization_id: int,
    payload: PasswordLoginRequest,
    request: Request,
    access_context: OrganizationAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> BrowserSessionRead:
    rate_limit_key = _rate_limit_key(request, organization_id, "admin")
    check_login_allowed(rate_limit_key)
    if not verify_password(access_context.organization.admin_password_hash, payload.password):
        record_login_failure(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    reset_login_failures(rate_limit_key)

    access_context.access.admin_auth_version = access_context.organization.admin_auth_version
    db.commit()
    return load_and_serialize_session(db, access_context.session.id)


@router.delete(
    "/api/organizations/{organization_id}/admin/session",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout_organization_admin(
    access_context: OrganizationAccessContext = Depends(require_user_access),
    db: Session = Depends(get_db),
) -> None:
    access_context.access.admin_auth_version = None
    db.commit()


@router.delete(
    "/api/organizations/{organization_id}/session",
    status_code=status.HTTP_204_NO_CONTENT,
)
def leave_organization(
    organization_id: int,
    response: Response,
    browser_context: BrowserSessionContext | None = Depends(get_optional_browser_session),
    db: Session = Depends(get_db),
) -> None:
    if browser_context is None:
        return

    access = db.scalar(
        select(SessionOrganizationAccess).where(
            SessionOrganizationAccess.browser_session_id == browser_context.session.id,
            SessionOrganizationAccess.organization_id == organization_id,
        )
    )
    remaining_accesses = db.scalar(
        select(func.count(SessionOrganizationAccess.id)).where(
            SessionOrganizationAccess.browser_session_id == browser_context.session.id
        )
    )
    if access is not None and remaining_accesses == 1:
        db.delete(browser_context.session)
        delete_browser_session_cookie(response)
    elif access is not None:
        db.delete(access)
    db.commit()


@router.delete("/api/session", status_code=status.HTTP_204_NO_CONTENT)
def logout_browser(
    response: Response,
    browser_context: BrowserSessionContext | None = Depends(get_optional_browser_session),
    db: Session = Depends(get_db),
) -> None:
    if browser_context is not None:
        db.delete(browser_context.session)
        db.commit()
    delete_browser_session_cookie(response)


def grant_organization_user_access(
    db: Session,
    browser_session: BrowserSession,
    organization: Organization,
) -> SessionOrganizationAccess:
    access = db.scalar(
        select(SessionOrganizationAccess).where(
            SessionOrganizationAccess.browser_session_id == browser_session.id,
            SessionOrganizationAccess.organization_id == organization.id,
        )
    )
    if access is None:
        access = SessionOrganizationAccess(
            browser_session_id=browser_session.id,
            organization_id=organization.id,
            user_auth_version=organization.user_auth_version,
        )
        db.add(access)
    else:
        user_access_was_valid = access.user_auth_version == organization.user_auth_version
        access.user_auth_version = organization.user_auth_version
        if not user_access_was_valid or access.admin_auth_version != organization.admin_auth_version:
            access.admin_auth_version = None
    return access


def load_and_serialize_session(db: Session, browser_session_id: int) -> BrowserSessionRead:
    browser_session = db.scalar(
        select(BrowserSession)
        .where(BrowserSession.id == browser_session_id)
        .options(
            selectinload(BrowserSession.organization_accesses).selectinload(
                SessionOrganizationAccess.organization
            )
        )
    )
    return _serialize_session(browser_session)


def _serialize_session(browser_session: BrowserSession | None) -> BrowserSessionRead:
    organizations: list[SessionOrganizationRead] = []
    if browser_session is not None:
        for access in sorted(browser_session.organization_accesses, key=lambda item: item.organization.name.lower()):
            organization = access.organization
            if access.user_auth_version != organization.user_auth_version:
                continue
            organizations.append(
                SessionOrganizationRead(
                    id=organization.id,
                    name=organization.name,
                    imageUrl=f"/api/organizations/{organization.id}/image",
                    isAdmin=access.admin_auth_version == organization.admin_auth_version,
                )
            )
    return BrowserSessionRead(authenticated=bool(organizations), organizations=organizations)


def _rate_limit_key(request: Request, organization_id: int, role: str) -> str:
    client_ip = request.client.host if request.client is not None else "unknown"
    return f"organization:{organization_id}:{role}:{client_ip}"

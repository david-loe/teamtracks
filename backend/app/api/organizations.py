from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.sessions import grant_organization_user_access, load_and_serialize_session
from app.config import Settings, get_settings
from app.db.session import get_db
from app.models.organization import Organization
from app.models.song import Song
from app.schemas.organization import (
    AdminPasswordChangeRequest,
    InviteAcceptRead,
    OrganizationAdminRead,
    OrganizationDeleteRequest,
    OrganizationPublicRead,
    PasswordChangeRequest,
)
from app.schemas.session import BrowserSessionRead
from app.services.auth import (
    BrowserSessionContext,
    OrganizationAccessContext,
    create_browser_session,
    get_auth_now,
    get_optional_browser_session,
    require_organization_admin_access,
    require_platform_admin_session,
)
from app.services.invites import create_invite_token, parse_invite_token
from app.services.passwords import hash_password, verify_password
from app.services.storage import StorageService, get_storage_service


router = APIRouter(tags=["organizations"])


@router.get("/api/organizations", response_model=list[OrganizationPublicRead])
def list_public_organizations(db: Session = Depends(get_db)) -> list[OrganizationPublicRead]:
    organizations = db.scalars(select(Organization).order_by(Organization.name.asc(), Organization.id.asc())).all()
    return [_public_read(organization) for organization in organizations]


@router.get("/api/organizations/{organization_id}/image")
def get_organization_image(
    organization_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> FileResponse:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization image not found")
    image_path = Path(organization.image_path)
    if not storage.is_inside_storage(image_path) or not image_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization image not found")
    return FileResponse(
        image_path,
        media_type=storage.organization_image_media_type(image_path),
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post(
    "/api/platform/organizations",
    response_model=OrganizationAdminRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_platform_admin_session)],
)
def create_organization(
    name: str = Form(..., min_length=1, max_length=200),
    user_password: str = Form(..., alias="userPassword", min_length=8, max_length=512),
    admin_password: str = Form(..., alias="adminPassword", min_length=8, max_length=512),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> OrganizationAdminRead:
    organization = Organization(
        name=_clean_name(name),
        image_path="pending",
        user_password_hash=hash_password(user_password),
        admin_password_hash=hash_password(admin_password),
    )
    db.add(organization)
    db.flush()
    try:
        organization.image_path = str(storage.save_organization_image(organization.id, image))
        db.commit()
    except Exception:
        db.rollback()
        storage.cleanup_organization(organization.id)
        raise
    db.refresh(organization)
    return _admin_read(organization, settings)


@router.get(
    "/api/platform/organizations",
    response_model=list[OrganizationAdminRead],
    dependencies=[Depends(require_platform_admin_session)],
)
def list_platform_organizations(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[OrganizationAdminRead]:
    organizations = db.scalars(select(Organization).order_by(Organization.name.asc(), Organization.id.asc())).all()
    return [_admin_read(organization, settings) for organization in organizations]


@router.patch(
    "/api/platform/organizations/{organization_id}",
    response_model=OrganizationAdminRead,
    dependencies=[Depends(require_platform_admin_session)],
)
def update_platform_organization(
    organization_id: int,
    name: str | None = Form(default=None, min_length=1, max_length=200),
    user_password: str | None = Form(default=None, alias="userPassword", min_length=8, max_length=512),
    admin_password: str | None = Form(default=None, alias="adminPassword", min_length=8, max_length=512),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> OrganizationAdminRead:
    organization = _organization_or_404(db, organization_id)
    if name is not None:
        organization.name = _clean_name(name)
    if user_password is not None:
        organization.user_password_hash = hash_password(user_password)
        organization.user_auth_version += 1
    if admin_password is not None:
        organization.admin_password_hash = hash_password(admin_password)
        organization.admin_auth_version += 1
    if image is not None:
        organization.image_path = str(storage.save_organization_image(organization.id, image))
    db.commit()
    db.refresh(organization)
    return _admin_read(organization, settings)


@router.delete(
    "/api/platform/organizations/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_platform_admin_session)],
)
def delete_platform_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> None:
    organization = _organization_or_404(db, organization_id)
    _delete_organization(db, storage, organization)


@router.get(
    "/api/organizations/{organization_id}/admin/organization",
    response_model=OrganizationAdminRead,
)
def get_admin_organization(
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    settings: Settings = Depends(get_settings),
) -> OrganizationAdminRead:
    return _admin_read(access_context.organization, settings)


@router.patch(
    "/api/organizations/{organization_id}/admin/organization",
    response_model=OrganizationAdminRead,
)
def update_admin_organization(
    name: str | None = Form(default=None, min_length=1, max_length=200),
    image: UploadFile | None = File(default=None),
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> OrganizationAdminRead:
    organization = access_context.organization
    if name is not None:
        organization.name = _clean_name(name)
    if image is not None:
        organization.image_path = str(storage.save_organization_image(organization.id, image))
    db.commit()
    db.refresh(organization)
    return _admin_read(organization, settings)


@router.put(
    "/api/organizations/{organization_id}/admin/organization/user-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def update_user_password(
    payload: PasswordChangeRequest,
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    db: Session = Depends(get_db),
) -> None:
    organization = access_context.organization
    organization.user_password_hash = hash_password(payload.new_password)
    organization.user_auth_version += 1
    access_context.access.user_auth_version = organization.user_auth_version
    db.commit()


@router.put(
    "/api/organizations/{organization_id}/admin/organization/admin-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def update_admin_password(
    payload: AdminPasswordChangeRequest,
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    db: Session = Depends(get_db),
) -> None:
    organization = access_context.organization
    if not verify_password(organization.admin_password_hash, payload.current_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")
    organization.admin_password_hash = hash_password(payload.new_password)
    organization.admin_auth_version += 1
    access_context.access.admin_auth_version = organization.admin_auth_version
    db.commit()


@router.post(
    "/api/organizations/{organization_id}/admin/organization/invite/regenerate",
    response_model=OrganizationAdminRead,
)
def regenerate_invite(
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrganizationAdminRead:
    access_context.organization.invite_version += 1
    db.commit()
    db.refresh(access_context.organization)
    return _admin_read(access_context.organization, settings)


@router.delete(
    "/api/organizations/{organization_id}/admin/organization",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_admin_organization(
    payload: OrganizationDeleteRequest,
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> None:
    organization = access_context.organization
    if not verify_password(organization.admin_password_hash, payload.admin_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin password")
    _delete_organization(db, storage, organization)


@router.post("/api/invites/{token}/accept", response_model=InviteAcceptRead)
def accept_invite(
    token: str,
    response: Response,
    browser_context: BrowserSessionContext | None = Depends(get_optional_browser_session),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    now: datetime = Depends(get_auth_now),
) -> InviteAcceptRead:
    invite = parse_invite_token(token, settings)
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    organization_id, invite_version = invite
    organization = db.get(Organization, organization_id)
    if organization is None or organization.invite_version != invite_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")
    if browser_context is None:
        browser_context = create_browser_session(db, response, settings, now)
    grant_organization_user_access(db, browser_context.session, organization)
    db.commit()
    return InviteAcceptRead(
        organizationId=organization.id,
        session=load_and_serialize_session(db, browser_context.session.id),
    )


def _organization_or_404(db: Session, organization_id: int) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return organization


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Organization name must not be blank",
        )
    return cleaned


def _public_read(organization: Organization) -> OrganizationPublicRead:
    return OrganizationPublicRead(
        id=organization.id,
        name=organization.name,
        imageUrl=f"/api/organizations/{organization.id}/image",
    )


def _admin_read(organization: Organization, settings: Settings) -> OrganizationAdminRead:
    token = create_invite_token(organization.id, organization.invite_version, settings)
    return OrganizationAdminRead(
        id=organization.id,
        name=organization.name,
        imageUrl=f"/api/organizations/{organization.id}/image",
        inviteToken=token,
        inviteUrl=f"/invite/{token}",
        createdAt=organization.created_at,
        updatedAt=organization.updated_at,
    )


def _delete_organization(db: Session, storage: StorageService, organization: Organization) -> None:
    organization_id = organization.id
    song_ids = list(db.scalars(select(Song.id).where(Song.organization_id == organization_id)))
    db.delete(organization)
    db.commit()
    for song_id in song_ids:
        storage.cleanup_song(organization_id, song_id)
    storage.cleanup_organization(organization_id)

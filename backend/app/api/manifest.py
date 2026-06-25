from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.manifest import SongManifest
from app.services.auth import require_organization_admin_access
from app.services.manifest import build_song_manifest, get_song_for_manifest
from app.services.settings import get_or_create_app_settings


router = APIRouter(
    prefix="/api/organizations/{organization_id}/admin/songs",
    tags=["admin-manifest"],
    dependencies=[Depends(require_organization_admin_access)],
)


@router.get("/{song_id}/manifest", response_model=SongManifest)
def get_manifest(
    organization_id: int,
    song_id: int,
    key_id: int | None = Query(default=None, alias="keyId"),
    db: Session = Depends(get_db),
) -> SongManifest:
    song = get_song_for_manifest(db, organization_id, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    if key_id is not None and all(key_variant.id != key_id for key_variant in song.key_variants):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song key not found")
    settings = get_or_create_app_settings(db, organization_id)
    db.commit()
    return build_song_manifest(song, settings, selected_key_id=key_id)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.manifest import SongManifest
from app.services.manifest import build_song_manifest, get_song_for_manifest
from app.services.auth import require_admin_session
from app.services.settings import get_or_create_app_settings


router = APIRouter(tags=["admin-manifest"], dependencies=[Depends(require_admin_session)])


@router.get("/api/songs/{song_id}/manifest", response_model=SongManifest, include_in_schema=False)
@router.get("/api/admin/songs/{song_id}/manifest", response_model=SongManifest)
def get_manifest(
    song_id: int,
    key_id: int | None = Query(default=None, alias="keyId"),
    db: Session = Depends(get_db),
) -> SongManifest:
    song = get_song_for_manifest(db, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    if key_id is not None and all(key_variant.id != key_id for key_variant in song.key_variants):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song key not found")
    settings = get_or_create_app_settings(db)
    db.commit()
    return build_song_manifest(song, settings, selected_key_id=key_id)

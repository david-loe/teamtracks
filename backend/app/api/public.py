from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain import SongStatus
from app.models.song import Song
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.schemas.manifest import SongManifest
from app.schemas.song import SongListItem
from app.services.manifest import build_song_manifest, get_song_for_manifest, is_song_key_playable
from app.services.settings import get_or_create_app_settings


router = APIRouter(prefix="/api/public/songs", tags=["public-songs"])


@router.get("", response_model=list[SongListItem])
def list_public_songs(
    query: str = Query(default="", max_length=200),
    db: Session = Depends(get_db),
) -> list[SongListItem]:
    statement = (
        select(Song)
        .where(Song.status == SongStatus.READY.value)
        .options(
            selectinload(Song.stems).selectinload(Stem.key_assets),
            selectinload(Song.key_variants).selectinload(SongKey.stem_assets),
        )
        .order_by(Song.title.asc())
    )
    search = query.strip()
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                Song.title.ilike(pattern),
                Song.artist.ilike(pattern),
                Song.slug.ilike(pattern),
                Song.description.ilike(pattern),
            )
        )
    songs = db.scalars(statement).all()
    result: list[SongListItem] = []
    for song in songs:
        original_key = next((key_variant for key_variant in song.key_variants if key_variant.is_original), None)
        if original_key is None or not is_song_key_playable(song, original_key, song.stems):
            continue
        result.append(
            SongListItem(
                id=song.id,
                title=song.title,
                artist=song.artist,
                slug=song.slug,
                status=song.status,
                original_key=song.original_key,
                stem_count=len(song.stems),
                ready_stem_count=len(song.stems),
                duration_ms=song.target_duration_ms,
            )
        )
    return result


@router.get("/{song_id}/manifest", response_model=SongManifest)
def get_public_manifest(
    song_id: int,
    key_id: int | None = Query(default=None, alias="keyId"),
    db: Session = Depends(get_db),
) -> SongManifest:
    song = get_song_for_manifest(db, song_id)
    if song is None or song.status != SongStatus.READY.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    if key_id is not None and all(key_variant.id != key_id for key_variant in song.key_variants):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song key not found")
    settings = get_or_create_app_settings(db)
    db.commit()
    manifest = build_song_manifest(song, settings, selected_key_id=key_id)
    if not manifest.playable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    return manifest

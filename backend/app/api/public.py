from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain import SongStatus, StemStatus
from app.models.song import Song
from app.schemas.manifest import SongManifest
from app.schemas.song import SongListItem
from app.services.manifest import build_song_manifest, is_song_playable
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
        .options(selectinload(Song.stems))
        .order_by(Song.title.asc())
    )
    search = query.strip()
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(Song.title.ilike(pattern), Song.slug.ilike(pattern), Song.description.ilike(pattern))
        )
    songs = db.scalars(statement).all()
    return [
        SongListItem(
            id=song.id,
            title=song.title,
            slug=song.slug,
            status=song.status,
            stem_count=len(song.stems),
            ready_stem_count=len(song.stems),
            duration_ms=song.target_duration_ms,
        )
        for song in songs
        if is_song_playable(song, song.stems)
    ]


@router.get("/{song_id}/manifest", response_model=SongManifest)
def get_public_manifest(song_id: int, db: Session = Depends(get_db)) -> SongManifest:
    song = db.scalar(select(Song).where(Song.id == song_id).options(selectinload(Song.stems)))
    if song is None or not is_song_playable(song, song.stems):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    settings = get_or_create_app_settings(db)
    db.commit()
    return build_song_manifest(song, settings)

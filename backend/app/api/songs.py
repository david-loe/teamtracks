from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain import StemStatus
from app.models.song import Song
from app.schemas.song import SongCreate, SongListItem, SongRead
from app.services.storage import StorageService, get_storage_service


router = APIRouter(prefix="/api/songs", tags=["songs"])


def get_song_or_404(db: Session, song_id: int) -> Song:
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    return song


@router.get("", response_model=list[SongListItem])
def list_songs(db: Session = Depends(get_db)) -> list[SongListItem]:
    songs = db.scalars(select(Song).options(selectinload(Song.stems)).order_by(Song.created_at.desc())).all()
    return [
        SongListItem(
            id=song.id,
            title=song.title,
            slug=song.slug,
            status=song.status,
            stem_count=len(song.stems),
            ready_stem_count=sum(1 for stem in song.stems if stem.status == StemStatus.READY.value),
            duration_ms=song.target_duration_ms,
        )
        for song in songs
    ]


@router.post("", response_model=SongRead, status_code=status.HTTP_201_CREATED)
def create_song(payload: SongCreate, db: Session = Depends(get_db)) -> Song:
    song = Song(title=payload.title, slug=payload.slug, description=payload.description)
    db.add(song)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Song slug already exists") from exc
    db.refresh(song)
    return song


@router.get("/{song_id}", response_model=SongRead)
def get_song(song_id: int, db: Session = Depends(get_db)) -> Song:
    return get_song_or_404(db, song_id)


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(
    song_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Response:
    song = get_song_or_404(db, song_id)
    db.delete(song)
    db.commit()
    storage.cleanup_song(song_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

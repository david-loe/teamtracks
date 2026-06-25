from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain import StemStatus
from app.models.song import Song
from app.models.song_key import SongKey
from app.schemas.song import SongCreate, SongListItem, SongRead, SongUpdate
from app.services.auth import OrganizationAccessContext, require_organization_admin_access
from app.services.storage import StorageService, get_storage_service


router = APIRouter(
    prefix="/api/organizations/{organization_id}/admin/songs",
    tags=["admin-songs"],
    dependencies=[Depends(require_organization_admin_access)],
)


def get_song_or_404(db: Session, organization_id: int, song_id: int) -> Song:
    song = db.scalar(select(Song).where(Song.id == song_id, Song.organization_id == organization_id))
    if song is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Song not found")
    return song


@router.get("", response_model=list[SongListItem])
def list_songs(organization_id: int, db: Session = Depends(get_db)) -> list[SongListItem]:
    songs = db.scalars(
        select(Song)
        .where(Song.organization_id == organization_id)
        .options(selectinload(Song.stems))
        .order_by(Song.created_at.desc())
    ).all()
    return [
        SongListItem(
            id=song.id,
            title=song.title,
            artist=song.artist,
            slug=song.slug,
            status=song.status,
            original_key=song.original_key,
            stem_count=len(song.stems),
            ready_stem_count=sum(1 for stem in song.stems if stem.status == StemStatus.READY.value),
            duration_ms=song.target_duration_ms,
        )
        for song in songs
    ]


@router.post("", response_model=SongRead, status_code=status.HTTP_201_CREATED)
def create_song(
    organization_id: int,
    payload: SongCreate,
    access_context: OrganizationAccessContext = Depends(require_organization_admin_access),
    db: Session = Depends(get_db),
) -> Song:
    song = Song(
        organization_id=access_context.organization.id,
        title=payload.title,
        artist=payload.artist.strip(),
        slug=payload.slug,
        description=payload.description,
        original_key=payload.original_key,
    )
    db.add(song)
    try:
        db.flush()
        db.add(SongKey(song_id=song.id, semitone_offset=0, is_original=True, status=song.status))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Song slug already exists") from exc
    db.refresh(song)
    return song


@router.get("/{song_id}", response_model=SongRead)
def get_song(organization_id: int, song_id: int, db: Session = Depends(get_db)) -> Song:
    return get_song_or_404(db, organization_id, song_id)


@router.patch("/{song_id}", response_model=SongRead)
def update_song(organization_id: int, song_id: int, payload: SongUpdate, db: Session = Depends(get_db)) -> Song:
    song = get_song_or_404(db, organization_id, song_id)
    if payload.title is not None:
        song.title = payload.title.strip()
    if payload.artist is not None:
        song.artist = payload.artist.strip()
    if payload.original_key is not None:
        song.original_key = payload.original_key
        original_key = db.scalar(select(SongKey).where(SongKey.song_id == song.id, SongKey.semitone_offset == 0))
        if original_key is None:
            original_key = SongKey(song_id=song.id, semitone_offset=0, is_original=True, status=song.status)
            db.add(original_key)
            db.flush()
        for key_variant in db.scalars(select(SongKey).where(SongKey.song_id == song.id)):
            key_variant.is_original = key_variant.id == original_key.id
    db.commit()
    db.refresh(song)
    return song


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(
    organization_id: int,
    song_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Response:
    song = get_song_or_404(db, organization_id, song_id)
    db.delete(song)
    db.commit()
    storage.cleanup_song(organization_id, song_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

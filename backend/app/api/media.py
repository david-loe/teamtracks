from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.domain import StemStatus
from app.models.song import Song
from app.models.stem import Stem
from app.services.manifest import is_song_playable
from app.services.storage import StorageService, get_storage_service


router = APIRouter(tags=["media"])

CACHE_CONTROL = "public, max-age=31536000, immutable"


@router.get("/media/songs/{song_id}/stems/{stem_id}.m4a")
def get_stem_media(
    song_id: int,
    stem_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> FileResponse:
    stem = db.get(Stem, stem_id)
    if stem is None or stem.song_id != song_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")
    if stem.status != StemStatus.READY.value or stem.converted_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    song = db.scalar(select(Song).where(Song.id == song_id).options(selectinload(Song.stems)))
    if song is None or not is_song_playable(song, song.stems):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    media_path = Path(stem.converted_path)
    expected_path = storage.converted_path(song_id, stem_id).resolve()
    if media_path.resolve() != expected_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")
    if not media_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    return FileResponse(
        media_path,
        media_type="audio/mp4",
        filename=f"{stem.id}.m4a",
        headers={
            "Cache-Control": CACHE_CONTROL,
            "Accept-Ranges": "bytes",
        },
    )

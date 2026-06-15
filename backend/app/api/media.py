from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.domain import StemStatus
from app.models.song_key import SongKey
from app.models.stem_key_asset import StemKeyAsset
from app.services.storage import StorageService, get_storage_service


router = APIRouter(tags=["media"])


@router.get("/media/songs/{song_id}/keys/{song_key_id}/stems/{stem_id}.m4a")
def get_stem_media(
    song_id: int,
    song_key_id: int,
    stem_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    song_key = db.get(SongKey, song_key_id)
    if song_key is None or song_key.song_id != song_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    asset = db.query(StemKeyAsset).filter_by(song_key_id=song_key_id, stem_id=stem_id).one_or_none()
    if asset is None or asset.status != StemStatus.READY.value or asset.file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")
    if asset.stem.song_id != song_id or asset.stem.status != StemStatus.READY.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    media_path = Path(asset.file_path)
    if not storage.is_inside_storage(media_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")
    if not media_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found")

    return FileResponse(
        media_path,
        media_type="audio/mp4",
        filename=f"{asset.stem_id}.m4a",
        headers={
            "Cache-Control": f"public, max-age={settings.stem_cache_max_age_seconds}, immutable",
            "Accept-Ranges": "bytes",
        },
    )

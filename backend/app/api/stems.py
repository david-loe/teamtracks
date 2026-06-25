from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.songs import get_song_or_404
from app.db.session import get_db
from app.domain import StemRole, StemStatus
from app.models.song import Song
from app.models.stem import Stem
from app.schemas.stem import StemRead
from app.services.auth import require_organization_admin_access
from app.services.storage import StorageService, get_storage_service


router = APIRouter(
    prefix="/api/organizations/{organization_id}/admin",
    tags=["admin-stems"],
    dependencies=[Depends(require_organization_admin_access)],
)


def get_stem_or_404(db: Session, organization_id: int, stem_id: int) -> Stem:
    stem = db.scalar(
        select(Stem).join(Song).where(Stem.id == stem_id, Song.organization_id == organization_id)
    )
    if stem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stem not found")
    return stem


@router.get("/songs/{song_id}/stems", response_model=list[StemRead])
def list_stems(organization_id: int, song_id: int, db: Session = Depends(get_db)) -> list[Stem]:
    get_song_or_404(db, organization_id, song_id)
    return list(db.scalars(select(Stem).where(Stem.song_id == song_id).order_by(Stem.created_at.asc())))


@router.post("/songs/{song_id}/stems/upload", response_model=StemRead, status_code=status.HTTP_201_CREATED)
def upload_stem(
    organization_id: int,
    song_id: int,
    name: str = Form(..., min_length=1, max_length=200),
    role: StemRole = Form(...),
    key: int | None = Form(default=None, ge=0, le=11),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Stem:
    get_song_or_404(db, organization_id, song_id)
    stem = Stem(
        song_id=song_id,
        name=name,
        role=role.value,
        key=key,
        status=StemStatus.UPLOADED.value,
        source_filename=file.filename,
        source_format="wav",
    )
    db.add(stem)
    db.flush()
    source_path = storage.save_upload(organization_id, song_id, stem.id, file)
    stem.source_path = str(source_path)
    stem.file_size_bytes = source_path.stat().st_size
    db.commit()
    db.refresh(stem)
    return stem


@router.delete("/stems/{stem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stem(
    organization_id: int,
    stem_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Response:
    stem = get_stem_or_404(db, organization_id, stem_id)
    storage.cleanup_stem(stem)
    db.delete(stem)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

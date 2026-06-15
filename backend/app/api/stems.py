from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.songs import get_song_or_404
from app.db.session import get_db
from app.domain import StemRole, StemStatus
from app.models.stem import Stem
from app.schemas.stem import StemImport, StemRead
from app.services.storage import StorageService, get_storage_service
from app.services.auth import require_admin_session


router = APIRouter(tags=["admin-stems"], dependencies=[Depends(require_admin_session)])


def get_stem_or_404(db: Session, stem_id: int) -> Stem:
    stem = db.get(Stem, stem_id)
    if stem is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stem not found")
    return stem


@router.get("/api/songs/{song_id}/stems", response_model=list[StemRead], include_in_schema=False)
@router.get("/api/admin/songs/{song_id}/stems", response_model=list[StemRead])
def list_stems(song_id: int, db: Session = Depends(get_db)) -> list[Stem]:
    get_song_or_404(db, song_id)
    return list(db.scalars(select(Stem).where(Stem.song_id == song_id).order_by(Stem.created_at.asc())))


@router.post("/api/songs/{song_id}/stems/upload", response_model=StemRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/api/admin/songs/{song_id}/stems/upload", response_model=StemRead, status_code=status.HTTP_201_CREATED)
def upload_stem(
    song_id: int,
    name: str = Form(..., min_length=1, max_length=200),
    role: StemRole = Form(...),
    key: int | None = Form(default=None, ge=0, le=11),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Stem:
    get_song_or_404(db, song_id)

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

    source_path = storage.save_upload(song_id, stem.id, file)
    stem.source_path = str(source_path)
    stem.file_size_bytes = source_path.stat().st_size

    db.commit()
    db.refresh(stem)
    return stem


@router.post("/api/songs/{song_id}/stems/import", response_model=StemRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/api/admin/songs/{song_id}/stems/import", response_model=StemRead, status_code=status.HTTP_201_CREATED)
def import_stem(
    song_id: int,
    payload: StemImport,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Stem:
    get_song_or_404(db, song_id)

    stem = Stem(
        song_id=song_id,
        name=payload.name,
        role=payload.role.value,
        key=payload.key,
        status=StemStatus.UPLOADED.value,
        source_filename=storage.resolve_import_path(payload.source_path).name,
        source_format="wav",
    )
    db.add(stem)
    db.flush()

    source_path = storage.import_source(song_id, stem.id, payload.source_path)
    stem.source_path = str(source_path)
    stem.file_size_bytes = source_path.stat().st_size

    db.commit()
    db.refresh(stem)
    return stem


@router.delete("/api/stems/{stem_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
@router.delete("/api/admin/stems/{stem_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stem(
    stem_id: int,
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Response:
    stem = get_stem_or_404(db, stem_id)
    storage.cleanup_stem(stem)
    db.delete(stem)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

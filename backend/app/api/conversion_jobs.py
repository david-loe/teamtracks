from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.songs import get_song_or_404
from app.db.session import get_db
from app.domain import ConversionJobStatus, StemStatus
from app.models.conversion_job import ConversionJob
from app.models.stem import Stem
from app.schemas.conversion_job import ConversionJobBatchRead, ConversionJobCreate, ConversionJobRead
from app.services.auth import require_admin_session
from app.services.settings import get_or_create_app_settings


router = APIRouter(tags=["admin-conversion-jobs"], dependencies=[Depends(require_admin_session)])


@router.post(
    "/api/songs/{song_id}/conversion-jobs",
    response_model=ConversionJobBatchRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post(
    "/api/admin/songs/{song_id}/conversion-jobs",
    response_model=ConversionJobBatchRead,
    status_code=status.HTTP_201_CREATED,
)
def create_conversion_jobs(
    song_id: int,
    payload: ConversionJobCreate | None = None,
    db: Session = Depends(get_db),
) -> ConversionJobBatchRead:
    get_song_or_404(db, song_id)
    payload = payload or ConversionJobCreate()
    stems = _select_stems_for_jobs(db, song_id, payload.stem_ids)
    if not stems:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No stems available for conversion")

    settings = get_or_create_app_settings(db)
    jobs = [
        ConversionJob(
            song_id=song_id,
            stem_id=stem.id,
            status=ConversionJobStatus.QUEUED.value,
            requested_by=payload.requested_by,
            mono_bitrate_kbps=settings.mono_bitrate_kbps,
            stereo_bitrate_kbps=settings.stereo_bitrate_kbps,
            target_sample_rate=settings.target_sample_rate,
            duration_tolerance_ms=settings.duration_tolerance_ms,
        )
        for stem in stems
    ]
    db.add_all(jobs)
    db.commit()
    for job in jobs:
        db.refresh(job)

    return ConversionJobBatchRead(
        job_ids=[job.id for job in jobs],
        status=ConversionJobStatus.QUEUED,
    )


@router.get("/api/conversion-jobs/{job_id}", response_model=ConversionJobRead, include_in_schema=False)
@router.get("/api/admin/conversion-jobs/{job_id}", response_model=ConversionJobRead)
def get_conversion_job(job_id: int, db: Session = Depends(get_db)) -> ConversionJob:
    job = db.get(ConversionJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversion job not found")
    return job


@router.get("/api/songs/{song_id}/conversion-jobs", response_model=list[ConversionJobRead], include_in_schema=False)
@router.get("/api/admin/songs/{song_id}/conversion-jobs", response_model=list[ConversionJobRead])
def list_conversion_jobs(song_id: int, db: Session = Depends(get_db)) -> list[ConversionJob]:
    get_song_or_404(db, song_id)
    return list(
        db.scalars(
            select(ConversionJob)
            .where(ConversionJob.song_id == song_id)
            .order_by(ConversionJob.created_at.desc(), ConversionJob.id.desc())
        )
    )


def _select_stems_for_jobs(db: Session, song_id: int, stem_ids: list[int] | None) -> list[Stem]:
    if stem_ids is not None:
        if not stem_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="stemIds must not be empty")

        stems = list(db.scalars(select(Stem).where(Stem.song_id == song_id, Stem.id.in_(stem_ids))))
        stems_by_id = {stem.id: stem for stem in stems}
        missing_ids = [stem_id for stem_id in stem_ids if stem_id not in stems_by_id]
        if missing_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stem not found for song")
        ordered_stems = [stems_by_id[stem_id] for stem_id in stem_ids]
    else:
        ordered_stems = list(
            db.scalars(
                select(Stem)
                .where(
                    Stem.song_id == song_id,
                    Stem.source_path.is_not(None),
                    Stem.status.in_([StemStatus.UPLOADED.value, StemStatus.ERROR.value]),
                )
                .order_by(Stem.created_at.asc(), Stem.id.asc())
            )
        )

    if any(stem.source_path is None for stem in ordered_stems):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All conversion stems need source files")
    return ordered_stems

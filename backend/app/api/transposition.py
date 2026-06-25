from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.api.songs import get_song_or_404
from app.db.session import get_db
from app.domain import ConversionJobStatus, ConversionJobType, SongStatus
from app.models.conversion_job import ConversionJob
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset
from app.schemas.conversion_job import ConversionJobBatchRead
from app.schemas.transposition import StemKeyAssetInventoryItemRead, StemKeyAssetVariantRead, TransposeSongRequest
from app.services.auth import require_organization_admin_access
from app.services.conversion import ConversionError, semitone_offset_for_target, unique_keys
from app.services.settings import get_or_create_app_settings


router = APIRouter(
    prefix="/api/organizations/{organization_id}/admin/songs",
    tags=["admin-transposition"],
    dependencies=[Depends(require_organization_admin_access)],
)


@router.post("/{song_id}/transpose", response_model=ConversionJobBatchRead)
def transpose_song(
    organization_id: int,
    song_id: int,
    payload: TransposeSongRequest,
    db: Session = Depends(get_db),
) -> ConversionJobBatchRead:
    song = get_song_or_404(db, organization_id, song_id)
    settings = get_or_create_app_settings(db, organization_id)
    try:
        target_keys = unique_keys(payload.target_keys)
    except ConversionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    jobs = [
        ConversionJob(
            song_id=song.id,
            job_type=ConversionJobType.SONG_TRANSPOSITION.value,
            target_key=target_key,
            semitone_offset=semitone_offset_for_target(song.original_key, target_key),
            status=ConversionJobStatus.QUEUED.value,
            requested_by="admin-ui-transpose",
            mono_bitrate_kbps=settings.mono_bitrate_kbps,
            stereo_bitrate_kbps=settings.stereo_bitrate_kbps,
            target_sample_rate=settings.target_sample_rate,
            duration_tolerance_ms=settings.duration_tolerance_ms,
        )
        for target_key in target_keys
    ]
    db.add_all(jobs)
    db.commit()
    for job in jobs:
        db.refresh(job)

    return ConversionJobBatchRead(job_ids=[job.id for job in jobs], status=ConversionJobStatus.QUEUED)


@router.get("/{song_id}/key-assets", response_model=list[StemKeyAssetInventoryItemRead])
def list_key_assets(
    organization_id: int, song_id: int, db: Session = Depends(get_db)
) -> list[StemKeyAssetInventoryItemRead]:
    song = get_song_or_404(db, organization_id, song_id)
    stems = list(db.scalars(select(Stem).where(Stem.song_id == song_id).order_by(Stem.created_at.asc(), Stem.id.asc())))
    song_keys = list(
        db.scalars(
            select(SongKey)
            .where(SongKey.song_id == song_id)
            .options(selectinload(SongKey.stem_assets))
            .order_by(SongKey.semitone_offset.asc(), SongKey.id.asc())
        )
    )
    assets = list(
        db.scalars(
            select(StemKeyAsset)
            .join(SongKey, StemKeyAsset.song_key_id == SongKey.id)
            .where(SongKey.song_id == song_id)
        )
    )
    assets_by_key_and_stem = {(asset.song_key_id, asset.stem_id): asset for asset in assets}

    inventory: list[StemKeyAssetInventoryItemRead] = []
    for stem in stems:
        variants: list[StemKeyAssetVariantRead] = []
        if stem.key is not None:
            for song_key in song_keys:
                asset = assets_by_key_and_stem.get((song_key.id, stem.id))
                if asset is None and song_key.status != SongStatus.ERROR.value:
                    continue
                target_key = (song.original_key + song_key.semitone_offset) % 12
                variants.append(
                    StemKeyAssetVariantRead(
                        song_key_id=song_key.id,
                        semitone_offset=song_key.semitone_offset,
                        target_key=target_key,
                        status=asset.status if asset is not None else song_key.status,
                        error_message=(asset.error_message if asset is not None else None) or song_key.error_message,
                    )
                )
        inventory.append(
            StemKeyAssetInventoryItemRead(
                stem_id=stem.id,
                stem_name=stem.name,
                stem_role=stem.role,
                variants=variants,
            )
        )
    return inventory

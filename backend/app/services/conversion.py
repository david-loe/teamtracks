import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import ConversionJobStatus, ConversionJobType, SongStatus, StemStatus
from app.models.conversion_job import ConversionJob
from app.models.song import Song, utc_now
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset
from app.services.manifest import resolve_stem_asset
from app.services.probing import AudioMetadata, FFprobeService, ProbeError
from app.services.storage import StorageService

MAX_PROCESS_ERROR_LENGTH = 2000


class ConversionError(Exception):
    """Raised when a stem cannot be converted into an playback asset."""


@dataclass(frozen=True, slots=True)
class ConversionTargets:
    sample_rate: int
    duration_ms: int


class ConversionService:
    def __init__(
        self,
        storage: StorageService,
        probe_service: FFprobeService | None = None,
        ffmpeg_binary: str = "ffmpeg",
    ) -> None:
        self.storage = storage
        self.probe_service = probe_service or FFprobeService()
        self.ffmpeg_binary = ffmpeg_binary

    def process_job(self, db: Session, job_id: int) -> ConversionJob:
        job = db.scalar(
            select(ConversionJob)
            .where(ConversionJob.id == job_id)
            .options(
                selectinload(ConversionJob.song),
                selectinload(ConversionJob.stem),
                selectinload(ConversionJob.song_key).selectinload(SongKey.stem_assets),
            )
        )
        if job is None:
            raise ConversionError("Conversion job not found")
        if job.status != ConversionJobStatus.QUEUED.value:
            return job

        job.status = ConversionJobStatus.RUNNING.value
        job.started_at = utc_now()
        job.error_message = None
        db.commit()
        db.refresh(job)

        try:
            if job.job_type == ConversionJobType.STEM_CONVERSION.value:
                if job.stem is None:
                    raise ConversionError("Conversion job has no stem")
                self.convert_stem(
                    db,
                    job.song,
                    job.stem,
                    target_sample_rate=job.target_sample_rate,
                    duration_tolerance_ms=job.duration_tolerance_ms,
                    mono_bitrate_kbps=job.mono_bitrate_kbps,
                    stereo_bitrate_kbps=job.stereo_bitrate_kbps,
                )
            elif job.job_type == ConversionJobType.SONG_TRANSPOSITION.value:
                self.transpose_song_key(
                    db,
                    job,
                    target_sample_rate=job.target_sample_rate,
                    duration_tolerance_ms=job.duration_tolerance_ms,
                    mono_bitrate_kbps=job.mono_bitrate_kbps,
                    stereo_bitrate_kbps=job.stereo_bitrate_kbps,
                )
            else:
                raise ConversionError(f"Unsupported conversion job type: {job.job_type}")
        except Exception as exc:
            message = truncate_process_error(str(exc))
            job.status = ConversionJobStatus.FAILED.value
            job.finished_at = utc_now()
            job.error_message = message
            if job.stem is not None:
                job.stem.status = StemStatus.ERROR.value
                job.stem.error_message = message
            if job.song_key_id is not None:
                song_key = db.get(SongKey, job.song_key_id)
                if song_key is not None:
                    song_key.status = SongStatus.ERROR.value
                    song_key.error_message = message
                    mark_key_assets_error(db, song_key, message)
            db.flush()
            recalculate_song_status(db, job.song_id)
            db.commit()
        else:
            job.status = ConversionJobStatus.SUCCEEDED.value
            job.finished_at = utc_now()
            job.error_message = None
            recalculate_song_status(db, job.song_id)
            db.commit()

        db.refresh(job)
        return job

    def convert_stem(
        self,
        db: Session,
        song: Song,
        stem: Stem,
        *,
        target_sample_rate: int = 48000,
        duration_tolerance_ms: int = 100,
        mono_bitrate_kbps: int = 96,
        stereo_bitrate_kbps: int = 160,
    ) -> None:
        if stem.source_path is None:
            raise ConversionError("Stem has no source file")

        source_path = Path(stem.source_path)
        if not source_path.is_file():
            raise ConversionError("Stem source file not found")

        stem.status = StemStatus.CONVERTING.value
        stem.error_message = None
        db.commit()

        metadata = self.probe_service.probe_wav(source_path)
        targets = self.ensure_song_targets(db, song, target_sample_rate)
        self.validate_duration(metadata, targets, duration_tolerance_ms, stem)

        song_key = ensure_song_key(db, song, 0, is_original=True)
        output_path = self.storage.key_asset_path(song.organization_id, song.id, song_key.id, stem.id)
        bitrate_kbps = bitrate_kbps_for_channels(
            metadata.channels,
            mono_bitrate_kbps=mono_bitrate_kbps,
            stereo_bitrate_kbps=stereo_bitrate_kbps,
        )
        pitch_semitones = semitone_delta(stem.key, song.original_key)
        self.run_ffmpeg(source_path, output_path, targets, metadata.channels, bitrate_kbps, pitch_semitones=pitch_semitones)

        stem.converted_path = str(output_path)
        stem.source_format = "wav"
        stem.codec = "aac-lc"
        stem.sample_rate = targets.sample_rate
        stem.channels = metadata.channels
        stem.duration_ms = targets.duration_ms
        stem.file_size_bytes = output_path.stat().st_size
        stem.bitrate_kbps = bitrate_kbps
        stem.error_message = None
        stem.status = StemStatus.READY.value
        upsert_stem_key_asset(
            db,
            song_key=song_key,
            stem=stem,
            file_path=output_path,
            codec=stem.codec,
            sample_rate=stem.sample_rate,
            channels=stem.channels,
            duration_ms=stem.duration_ms,
            file_size_bytes=stem.file_size_bytes,
            bitrate_kbps=stem.bitrate_kbps,
        )
        if stem.key is None:
            key_variants = db.scalars(select(SongKey).where(SongKey.song_id == song.id)).all()
            for key_variant in key_variants:
                sync_song_key_status(db, song, key_variant)
        else:
            sync_song_key_status(db, song, song_key)
        db.flush()

    def transpose_song_key(
        self,
        db: Session,
        job: ConversionJob,
        *,
        target_sample_rate: int = 48000,
        duration_tolerance_ms: int = 100,
        mono_bitrate_kbps: int = 96,
        stereo_bitrate_kbps: int = 160,
    ) -> SongKey:
        song = job.song
        target_key = validate_target_key(job.target_key)
        semitone_offset = semitone_offset_for_target(song.original_key, target_key)
        song_key = ensure_song_key(db, song, semitone_offset, is_original=semitone_offset == 0)
        song_key.status = SongStatus.DRAFT.value
        song_key.error_message = None
        job.song_key_id = song_key.id
        job.semitone_offset = semitone_offset
        db.flush()

        if song.status != SongStatus.READY.value:
            raise ConversionError("Song must be ready before transposition")

        stems = list(
            db.scalars(
                select(Stem)
                .where(Stem.song_id == song.id)
                .order_by(Stem.created_at.asc(), Stem.id.asc())
            )
        )
        if not stems:
            raise ConversionError("Song has no stems to transpose")
        if any(stem.status != StemStatus.READY.value for stem in stems):
            raise ConversionError("All stems must be ready before transposition")
        if any(stem.key is not None and stem.source_path is None for stem in stems):
            raise ConversionError("All key-dependent stems need source files before transposition")

        targets = self.ensure_song_targets(db, song, target_sample_rate)
        original_song_key = ensure_song_key(db, song, 0, is_original=True)
        for stem in stems:
            if stem.key is None:
                original_asset = get_stem_key_asset(db, original_song_key.id, stem.id)
                if (
                    original_asset is None
                    or original_asset.status != StemStatus.READY.value
                    or original_asset.file_path is None
                    or not Path(original_asset.file_path).is_file()
                ):
                    raise ConversionError(f"Original asset missing for key-independent stem {stem.id}")
                continue
            self.convert_stem_for_key(
                db,
                song=song,
                song_key=song_key,
                stem=stem,
                targets=targets,
                target_key=target_key,
                duration_tolerance_ms=duration_tolerance_ms,
                mono_bitrate_kbps=mono_bitrate_kbps,
                stereo_bitrate_kbps=stereo_bitrate_kbps,
            )
        song_key.status = SongStatus.READY.value
        song_key.error_message = None
        db.flush()
        return song_key

    def convert_stem_for_key(
        self,
        db: Session,
        *,
        song: Song,
        song_key: SongKey,
        stem: Stem,
        targets: ConversionTargets,
        target_key: int,
        duration_tolerance_ms: int,
        mono_bitrate_kbps: int,
        stereo_bitrate_kbps: int,
    ) -> StemKeyAsset:
        if stem.source_path is None:
            raise ConversionError("Stem has no source file")

        source_path = Path(stem.source_path)
        if not source_path.is_file():
            raise ConversionError("Stem source file not found")

        metadata = self.probe_service.probe_wav(source_path)
        self.validate_duration(metadata, targets, duration_tolerance_ms, stem)
        bitrate_kbps = bitrate_kbps_for_channels(
            metadata.channels,
            mono_bitrate_kbps=mono_bitrate_kbps,
            stereo_bitrate_kbps=stereo_bitrate_kbps,
        )
        output_path = self.storage.key_asset_path(song.organization_id, song.id, song_key.id, stem.id)
        self.run_ffmpeg(
            source_path,
            output_path,
            targets,
            metadata.channels,
            bitrate_kbps,
            pitch_semitones=semitone_delta(stem.key, target_key),
        )
        return upsert_stem_key_asset(
            db,
            song_key=song_key,
            stem=stem,
            file_path=output_path,
            codec="aac-lc",
            sample_rate=targets.sample_rate,
            channels=metadata.channels,
            duration_ms=targets.duration_ms,
            file_size_bytes=output_path.stat().st_size,
            bitrate_kbps=bitrate_kbps,
        )

    def validate_duration(
        self,
        metadata: AudioMetadata,
        targets: ConversionTargets,
        duration_tolerance_ms: int,
        stem: Stem,
    ) -> None:
        duration_delta = abs(metadata.duration_ms - targets.duration_ms)
        if duration_delta > duration_tolerance_ms:
            stem.duration_ms = metadata.duration_ms
            stem.sample_rate = metadata.sample_rate
            stem.channels = metadata.channels
            raise ConversionError(
                f"Stem duration differs from song target by {duration_delta} ms; maximum allowed is "
                f"{duration_tolerance_ms} ms"
            )

    def ensure_song_targets(self, db: Session, song: Song, target_sample_rate: int) -> ConversionTargets:
        valid_metadata = self._probe_song_sources(db, song.id)
        if not valid_metadata:
            raise ConversionError("No valid WAV stems available to determine song targets")

        song.target_sample_rate = target_sample_rate
        if song.target_duration_ms is None:
            song.target_duration_ms = max(metadata.duration_ms for metadata in valid_metadata)

        db.flush()
        return ConversionTargets(sample_rate=song.target_sample_rate, duration_ms=song.target_duration_ms)

    def run_ffmpeg(
        self,
        source_path: Path,
        output_path: Path,
        targets: ConversionTargets,
        channels: int,
        bitrate_kbps: int,
        *,
        pitch_semitones: int = 0,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")
        temporary_path.unlink(missing_ok=True)

        command = build_ffmpeg_command(
            ffmpeg_binary=self.ffmpeg_binary,
            source_path=source_path,
            output_path=temporary_path,
            target_sample_rate=targets.sample_rate,
            target_duration_ms=targets.duration_ms,
            channels=channels,
            bitrate_kbps=bitrate_kbps,
            pitch_semitones=pitch_semitones,
        )
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            temporary_path.unlink(missing_ok=True)
            message = truncate_process_error(result.stderr or result.stdout or "ffmpeg failed")
            raise ConversionError(message)

        temporary_path.replace(output_path)

    def _probe_song_sources(self, db: Session, song_id: int) -> list[AudioMetadata]:
        stems = db.scalars(
            select(Stem)
            .where(Stem.song_id == song_id, Stem.source_path.is_not(None))
            .order_by(Stem.created_at.asc(), Stem.id.asc())
        ).all()

        metadata: list[AudioMetadata] = []
        for stem in stems:
            if stem.source_path is None:
                continue
            try:
                metadata.append(self.probe_service.probe_wav(Path(stem.source_path)))
            except ProbeError:
                continue
        return metadata


def build_ffmpeg_command(
    *,
    ffmpeg_binary: str,
    source_path: Path,
    output_path: Path,
    target_sample_rate: int,
    target_duration_ms: int,
    channels: int,
    bitrate_kbps: int | None = None,
    pitch_semitones: int = 0,
) -> list[str]:
    duration_seconds = f"{target_duration_ms / 1000:.3f}"
    bitrate = f"{bitrate_kbps if bitrate_kbps is not None else bitrate_kbps_for_channels(channels)}k"
    audio_filters = []
    if pitch_semitones != 0:
        pitch_ratio = 2 ** (pitch_semitones / 12)
        audio_filters.append(f"rubberband=pitch={pitch_ratio:.8f}")
    audio_filters.append(f"aresample=async=1:first_pts=0,apad,atrim=0:{duration_seconds}")
    return [
        ffmpeg_binary,
        "-y",
        "-i",
        str(source_path),
        "-map",
        "0:a:0",
        "-vn",
        "-c:a",
        "aac",
        "-profile:a",
        "aac_low",
        "-ar",
        str(target_sample_rate),
        "-ac",
        str(channels),
        "-b:a",
        bitrate,
        "-af",
        ",".join(audio_filters),
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def semitone_delta(source_key: int | None, target_key: int) -> int:
    if source_key is None:
        return 0
    delta = (target_key - source_key) % 12
    if delta > 6:
        delta -= 12
    return delta


def unique_keys(keys: list[int]) -> list[int]:
    result: list[int] = []
    for key in keys:
        validate_target_key(key)
        if key not in result:
            result.append(key)
    if not result:
        raise ConversionError("At least one target key is required")
    return result


def validate_target_key(target_key: int | None) -> int:
    if target_key is None or target_key < 0 or target_key > 11:
        raise ConversionError("Target keys must be between 0 and 11")
    return target_key


def semitone_offset_for_target(original_key: int, target_key: int) -> int:
    return (target_key - original_key) % 12


def ensure_song_key(db: Session, song: Song, semitone_offset: int, *, is_original: bool) -> SongKey:
    song_key = db.scalar(
        select(SongKey).where(SongKey.song_id == song.id, SongKey.semitone_offset == semitone_offset)
    )
    if song_key is None:
        song_key = SongKey(
            song_id=song.id,
            semitone_offset=semitone_offset,
            is_original=is_original,
            status=SongStatus.DRAFT.value,
        )
        db.add(song_key)
        db.flush()
    if is_original:
        key_variants = db.scalars(select(SongKey).where(SongKey.song_id == song.id)).all()
        for key_variant in key_variants:
            key_variant.is_original = key_variant.id == song_key.id
        db.flush()
    return song_key


def get_stem_key_asset(db: Session, song_key_id: int, stem_id: int) -> StemKeyAsset | None:
    return db.scalar(
        select(StemKeyAsset).where(StemKeyAsset.song_key_id == song_key_id, StemKeyAsset.stem_id == stem_id)
    )


def upsert_stem_key_asset(
    db: Session,
    *,
    song_key: SongKey,
    stem: Stem,
    file_path: Path,
    codec: str | None,
    sample_rate: int | None,
    channels: int | None,
    duration_ms: int | None,
    file_size_bytes: int | None,
    bitrate_kbps: int | None,
) -> StemKeyAsset:
    asset = get_stem_key_asset(db, song_key.id, stem.id)
    if asset is None:
        asset = StemKeyAsset(song_key_id=song_key.id, stem_id=stem.id)
        db.add(asset)
    asset.status = StemStatus.READY.value
    asset.file_path = str(file_path)
    asset.codec = codec
    asset.sample_rate = sample_rate
    asset.channels = channels
    asset.duration_ms = duration_ms
    asset.file_size_bytes = file_size_bytes
    asset.bitrate_kbps = bitrate_kbps
    asset.error_message = None
    asset.updated_at = utc_now()
    db.flush()
    return asset


def mark_key_assets_error(db: Session, song_key: SongKey, message: str) -> None:
    for asset in song_key.stem_assets:
        asset.status = StemStatus.ERROR.value
        asset.error_message = message
    db.flush()


def sync_song_key_status(db: Session, song: Song, song_key: SongKey) -> None:
    stems = list(db.scalars(select(Stem).where(Stem.song_id == song.id)))
    if not stems:
        song_key.status = SongStatus.DRAFT.value
        return
    if all(
        stem.status == StemStatus.READY.value
        and (asset := resolve_stem_asset(song, song_key, stem)) is not None
        and asset.status == StemStatus.READY.value
        and asset.file_path is not None
        for stem in stems
    ):
        song_key.status = SongStatus.READY.value
        song_key.error_message = None
    else:
        song_key.status = SongStatus.DRAFT.value
    db.flush()


def bitrate_kbps_for_channels(
    channels: int,
    *,
    mono_bitrate_kbps: int = 96,
    stereo_bitrate_kbps: int = 160,
) -> int:
    if channels == 1:
        return mono_bitrate_kbps
    if channels == 2:
        return stereo_bitrate_kbps
    raise ConversionError("Only mono and stereo WAV files are supported")


def recalculate_song_status(db: Session, song_id: int) -> None:
    song = db.get(Song, song_id)
    if song is None:
        return

    statuses = list(db.scalars(select(Stem.status).where(Stem.song_id == song_id)))
    if not statuses:
        song.status = SongStatus.DRAFT.value
    elif any(status == StemStatus.ERROR.value for status in statuses):
        song.status = SongStatus.ERROR.value
    elif all(status == StemStatus.READY.value for status in statuses):
        song.status = SongStatus.READY.value
    else:
        song.status = SongStatus.DRAFT.value
    db.flush()


def truncate_process_error(message: str) -> str:
    cleaned = message.strip()
    if len(cleaned) <= MAX_PROCESS_ERROR_LENGTH:
        return cleaned
    return f"{cleaned[:MAX_PROCESS_ERROR_LENGTH]}..."

import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import ConversionJobStatus, SongStatus, StemStatus
from app.models.conversion_job import ConversionJob
from app.models.song import Song, utc_now
from app.models.stem import Stem
from app.services.probing import AudioMetadata, FFprobeService, ProbeError
from app.services.storage import StorageService


DURATION_TOLERANCE_MS = 100
MAX_PROCESS_ERROR_LENGTH = 2000
PREFERRED_SAMPLE_RATES = {44100, 48000}


class ConversionError(Exception):
    """Raised when a stem cannot be converted into an MVP playback asset."""


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
            .options(selectinload(ConversionJob.song), selectinload(ConversionJob.stem))
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
            if job.stem is None:
                raise ConversionError("Conversion job has no stem")
            self.convert_stem(db, job.song, job.stem)
        except Exception as exc:
            message = truncate_process_error(str(exc))
            job.status = ConversionJobStatus.FAILED.value
            job.finished_at = utc_now()
            job.error_message = message
            if job.stem is not None:
                job.stem.status = StemStatus.ERROR.value
                job.stem.error_message = message
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

    def convert_stem(self, db: Session, song: Song, stem: Stem) -> None:
        if stem.source_path is None:
            raise ConversionError("Stem has no source file")

        source_path = Path(stem.source_path)
        if not source_path.is_file():
            raise ConversionError("Stem source file not found")

        stem.status = StemStatus.CONVERTING.value
        stem.error_message = None
        db.commit()

        metadata = self.probe_service.probe_wav(source_path)
        targets = self.ensure_song_targets(db, song)
        duration_delta = abs(metadata.duration_ms - targets.duration_ms)
        if duration_delta > DURATION_TOLERANCE_MS:
            stem.duration_ms = metadata.duration_ms
            stem.sample_rate = metadata.sample_rate
            stem.channels = metadata.channels
            raise ConversionError(
                f"Stem duration differs from song target by {duration_delta} ms; maximum allowed is "
                f"{DURATION_TOLERANCE_MS} ms"
            )

        output_path = self.storage.converted_path(song.id, stem.id)
        self.run_ffmpeg(source_path, output_path, targets, metadata.channels)

        stem.converted_path = str(output_path)
        stem.source_format = "wav"
        stem.codec = "aac-lc"
        stem.sample_rate = targets.sample_rate
        stem.channels = metadata.channels
        stem.duration_ms = targets.duration_ms
        stem.file_size_bytes = output_path.stat().st_size
        stem.bitrate_kbps = bitrate_kbps_for_channels(metadata.channels)
        stem.error_message = None
        stem.status = StemStatus.READY.value
        db.flush()

    def ensure_song_targets(self, db: Session, song: Song) -> ConversionTargets:
        if song.target_sample_rate is not None and song.target_duration_ms is not None:
            return ConversionTargets(sample_rate=song.target_sample_rate, duration_ms=song.target_duration_ms)

        valid_metadata = self._probe_song_sources(db, song.id)
        if not valid_metadata:
            raise ConversionError("No valid WAV stems available to determine song targets")

        if song.target_sample_rate is None:
            first_sample_rate = valid_metadata[0].sample_rate
            song.target_sample_rate = first_sample_rate if first_sample_rate in PREFERRED_SAMPLE_RATES else 48000
        if song.target_duration_ms is None:
            song.target_duration_ms = max(metadata.duration_ms for metadata in valid_metadata)

        db.flush()
        return ConversionTargets(sample_rate=song.target_sample_rate, duration_ms=song.target_duration_ms)

    def run_ffmpeg(self, source_path: Path, output_path: Path, targets: ConversionTargets, channels: int) -> None:
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
) -> list[str]:
    duration_seconds = f"{target_duration_ms / 1000:.3f}"
    bitrate = f"{bitrate_kbps_for_channels(channels)}k"
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
        f"aresample=async=1:first_pts=0,apad,atrim=0:{duration_seconds}",
        "-movflags",
        "+faststart",
        str(output_path),
    ]


def bitrate_kbps_for_channels(channels: int) -> int:
    if channels == 1:
        return 96
    if channels == 2:
        return 160
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

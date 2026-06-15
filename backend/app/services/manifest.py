from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import SongStatus, StemStatus
from app.models.song import Song
from app.models.stem import Stem
from app.schemas.manifest import ManifestSong, ManifestStem, SongManifest


def build_song_manifest(song: Song) -> SongManifest:
    stems = sorted(song.stems, key=lambda stem: (stem.created_at, stem.id))
    manifest_stems = [build_manifest_stem(song.id, stem) for stem in stems]
    playable = is_song_playable(song, stems)

    return SongManifest(
        song=ManifestSong(
            id=song.id,
            title=song.title,
            slug=song.slug,
            duration_ms=song.target_duration_ms,
            sample_rate=song.target_sample_rate,
        ),
        playable=playable,
        stems=manifest_stems,
    )


def get_song_for_manifest(db: Session, song_id: int) -> Song | None:
    return db.scalar(select(Song).where(Song.id == song_id).options(selectinload(Song.stems)))


def build_manifest_stem(song_id: int, stem: Stem) -> ManifestStem:
    is_playback_stem = stem.status == StemStatus.READY.value and stem.converted_path is not None
    return ManifestStem(
        id=stem.id,
        name=stem.name,
        role=stem.role,
        status=stem.status,
        url=f"/media/songs/{song_id}/stems/{stem.id}.m4a" if is_playback_stem else None,
        codec=stem.codec if is_playback_stem else None,
        container="m4a" if is_playback_stem else None,
        channels=stem.channels if is_playback_stem else None,
        sample_rate=stem.sample_rate if is_playback_stem else None,
        duration_ms=stem.duration_ms if is_playback_stem else None,
        file_size_bytes=stem.file_size_bytes if is_playback_stem else None,
        bitrate_kbps=stem.bitrate_kbps if is_playback_stem else None,
        error_message=stem.error_message,
    )


def is_song_playable(song: Song, stems: list[Stem]) -> bool:
    if song.status != SongStatus.READY.value:
        return False
    if song.target_duration_ms is None or song.target_sample_rate is None:
        return False
    if not stems:
        return False
    return all(stem.status == StemStatus.READY.value and stem.converted_path is not None for stem in stems)

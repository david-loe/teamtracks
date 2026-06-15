from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import SongStatus, StemStatus
from app.models.song import Song
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset
from app.models.app_settings import AppSettings
from app.schemas.manifest import ManifestKeyVariant, ManifestSong, ManifestStem, SongManifest


def build_song_manifest(song: Song, settings: AppSettings, selected_key_id: int | None = None) -> SongManifest:
    stems = sorted(song.stems, key=lambda stem: (stem.created_at, stem.id))
    key_variants = sorted(song.key_variants, key=lambda key: (not key.is_original, key.semitone_offset, key.id))
    selected_key = select_manifest_key(key_variants, selected_key_id)
    assets_by_stem_id = assets_for_key(selected_key)
    manifest_stems = [build_manifest_stem(song.id, selected_key, stem, assets_by_stem_id.get(stem.id)) for stem in stems]
    playable = selected_key is not None and is_song_key_playable(song, selected_key, stems)

    return SongManifest(
        song=ManifestSong(
            id=song.id,
            title=song.title,
            artist=song.artist,
            slug=song.slug,
            original_key=song.original_key,
            duration_ms=song.target_duration_ms,
            sample_rate=song.target_sample_rate,
        ),
        key_variants=[
            ManifestKeyVariant(
                id=key_variant.id,
                semitone_offset=key_variant.semitone_offset,
                is_original=key_variant.is_original,
                status=key_variant.status,
                error_message=key_variant.error_message,
            )
            for key_variant in key_variants
        ],
        selected_key_id=selected_key.id if selected_key is not None else None,
        playable=playable,
        stems=manifest_stems,
        player_settings=settings,
    )


def get_song_for_manifest(db: Session, song_id: int) -> Song | None:
    return db.scalar(
        select(Song)
        .where(Song.id == song_id)
        .options(
            selectinload(Song.stems).selectinload(Stem.key_assets),
            selectinload(Song.key_variants).selectinload(SongKey.stem_assets),
        )
    )


def build_manifest_stem(
    song_id: int,
    song_key: SongKey | None,
    stem: Stem,
    asset: StemKeyAsset | None,
) -> ManifestStem:
    is_playback_stem = (
        song_key is not None
        and asset is not None
        and stem.status == StemStatus.READY.value
        and asset.status == StemStatus.READY.value
        and asset.file_path is not None
    )
    return ManifestStem(
        id=stem.id,
        name=stem.name,
        role=stem.role,
        key=stem.key,
        focusable=stem.role != "click_cue",
        status=asset.status if asset is not None else stem.status,
        url=f"/media/songs/{song_id}/keys/{song_key.id}/stems/{stem.id}.m4a" if is_playback_stem else None,
        codec=asset.codec if is_playback_stem else None,
        container="m4a" if is_playback_stem else None,
        channels=asset.channels if is_playback_stem else None,
        sample_rate=asset.sample_rate if is_playback_stem else None,
        duration_ms=asset.duration_ms if is_playback_stem else None,
        file_size_bytes=asset.file_size_bytes if is_playback_stem else None,
        bitrate_kbps=asset.bitrate_kbps if is_playback_stem else None,
        error_message=asset.error_message if asset is not None else stem.error_message,
    )


def select_manifest_key(key_variants: list[SongKey], selected_key_id: int | None) -> SongKey | None:
    if selected_key_id is not None:
        return next((key_variant for key_variant in key_variants if key_variant.id == selected_key_id), None)
    return next((key_variant for key_variant in key_variants if key_variant.is_original), key_variants[0] if key_variants else None)


def assets_for_key(song_key: SongKey | None) -> dict[int, StemKeyAsset]:
    if song_key is None:
        return {}
    return {asset.stem_id: asset for asset in song_key.stem_assets}


def is_song_key_playable(song: Song, song_key: SongKey, stems: list[Stem]) -> bool:
    if song.status != SongStatus.READY.value:
        return False
    if song_key.status != SongStatus.READY.value:
        return False
    if song.target_duration_ms is None or song.target_sample_rate is None:
        return False
    if not stems:
        return False

    assets = assets_for_key(song_key)
    return all(
        stem.status == StemStatus.READY.value
        and (asset := assets.get(stem.id)) is not None
        and asset.status == StemStatus.READY.value
        and asset.file_path is not None
        for stem in stems
    )

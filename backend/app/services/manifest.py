from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import StemStatus
from app.models.app_settings import AppSettings
from app.models.song import Song
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset
from app.schemas.manifest import ManifestKeyVariant, ManifestSong, ManifestStem, SongManifest


def build_song_manifest(song: Song, settings: AppSettings, selected_key_id: int | None = None) -> SongManifest:
    stems = sorted(song.stems, key=lambda stem: (stem.created_at, stem.id))
    key_variants = sorted(song.key_variants, key=lambda key: (not key.is_original, key.semitone_offset, key.id))
    selected_key = select_manifest_key(key_variants, selected_key_id)
    manifest_stems = [build_manifest_stem(song, selected_key, stem) for stem in stems]
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
                playable=is_song_key_playable(song, key_variant, stems),
                error_message=key_variant.error_message,
            )
            for key_variant in key_variants
        ],
        selected_key_id=selected_key.id if selected_key is not None else None,
        playable=playable,
        stems=manifest_stems,
        player_settings=settings,
    )


def get_song_for_manifest(db: Session, organization_id: int, song_id: int) -> Song | None:
    return db.scalar(
        select(Song)
        .where(Song.id == song_id, Song.organization_id == organization_id)
        .options(
            selectinload(Song.stems).selectinload(Stem.key_assets),
            selectinload(Song.key_variants).selectinload(SongKey.stem_assets),
        )
    )


def build_manifest_stem(
    song: Song,
    song_key: SongKey | None,
    stem: Stem,
) -> ManifestStem:
    asset = resolve_stem_asset(song, song_key, stem)
    is_playback_stem = song_key is not None and is_stem_asset_playable(stem, asset)
    media_url = None
    if is_playback_stem:
        asset_version = asset.updated_at.strftime("%Y%m%d%H%M%S%f")
        media_url = (
            f"/media/organizations/{song.organization_id}/songs/{song.id}"
            f"/keys/{asset.song_key_id}/stems/{stem.id}.m4a?v={asset_version}"
        )

    return ManifestStem(
        id=stem.id,
        name=stem.name,
        role=stem.role,
        key=stem.key,
        focusable=stem.role != "click_cue",
        status=asset.status if asset is not None else stem.status,
        url=media_url,
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


def resolve_stem_asset(song: Song, song_key: SongKey | None, stem: Stem) -> StemKeyAsset | None:
    if song_key is None:
        return None

    asset_key = song_key
    if stem.key is None:
        original_key = next((key_variant for key_variant in song.key_variants if key_variant.is_original), None)
        if original_key is None:
            return None
        asset_key = original_key

    return next((asset for asset in stem.key_assets if asset.song_key_id == asset_key.id), None)


def is_stem_asset_playable(stem: Stem, asset: StemKeyAsset | None) -> bool:
    return (
        stem.status == StemStatus.READY.value
        and asset is not None
        and asset.status == StemStatus.READY.value
        and asset.file_path is not None
    )


def playable_stem_count(song: Song, song_key: SongKey, stems: list[Stem]) -> int:
    if song.target_duration_ms is None or song.target_sample_rate is None:
        return 0

    return sum(is_stem_asset_playable(stem, resolve_stem_asset(song, song_key, stem)) for stem in stems)


def is_song_key_playable(song: Song, song_key: SongKey, stems: list[Stem]) -> bool:
    return playable_stem_count(song, song_key, stems) > 0

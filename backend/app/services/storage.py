import shutil
from pathlib import Path
from typing import BinaryIO

from fastapi import Depends, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.models.stem import Stem


WAV_CONTENT_TYPES = {"audio/wav", "audio/wave", "audio/x-wav", "application/octet-stream"}


class StorageService:
    def __init__(self, storage_root: Path, source_root: Path) -> None:
        self.storage_root = storage_root
        self.source_root = source_root

    def song_dir(self, song_id: int) -> Path:
        return self.storage_root / "songs" / str(song_id)

    def source_path(self, song_id: int, stem_id: int) -> Path:
        return self.song_dir(song_id) / "source" / f"{stem_id}.wav"

    def converted_path(self, song_id: int, stem_id: int) -> Path:
        return self.song_dir(song_id) / "converted" / f"{stem_id}.m4a"

    def key_asset_path(self, song_id: int, song_key_id: int, stem_id: int) -> Path:
        return self.song_dir(song_id) / "keys" / str(song_key_id) / f"{stem_id}.m4a"

    def save_upload(self, song_id: int, stem_id: int, upload: UploadFile) -> Path:
        self.validate_wav_upload(upload)
        destination = self.source_path(song_id, stem_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
        return destination

    def import_source(self, song_id: int, stem_id: int, source_path: str) -> Path:
        source = self.resolve_import_path(source_path)
        if source.suffix.lower() != ".wav":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import source must be a WAV file")
        if not source.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import source file not found")

        destination = self.source_path(song_id, stem_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def cleanup_stem(self, stem: Stem) -> None:
        asset_paths = [asset.file_path for asset in stem.key_assets]
        for raw_path in (stem.source_path, stem.converted_path, *asset_paths):
            if raw_path:
                self._unlink_if_inside_storage(Path(raw_path))

    def cleanup_song(self, song_id: int) -> None:
        shutil.rmtree(self.song_dir(song_id), ignore_errors=True)

    def resolve_import_path(self, source_path: str) -> Path:
        source_root = self.source_root.resolve()
        candidate = Path(source_path)
        if not candidate.is_absolute():
            candidate = source_root / candidate
        resolved = candidate.resolve()

        try:
            resolved.relative_to(source_root)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Import path must stay inside SOURCE_ROOT") from exc

        return resolved

    def validate_wav_upload(self, upload: UploadFile) -> None:
        filename = upload.filename or ""
        if Path(filename).suffix.lower() != ".wav":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only WAV uploads are supported")
        if upload.content_type not in WAV_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload content type must be WAV")

    def _unlink_if_inside_storage(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            resolved.relative_to(self.storage_root.resolve())
        except ValueError:
            return
        resolved.unlink(missing_ok=True)

    def is_inside_storage(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.storage_root.resolve())
        except ValueError:
            return False
        return True


def get_storage_service(settings: Settings = Depends(get_settings)) -> StorageService:
    return StorageService(settings.storage_root, settings.source_root)

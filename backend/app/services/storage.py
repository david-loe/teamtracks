import shutil
from pathlib import Path

from fastapi import Depends, HTTPException, UploadFile, status

from app.config import Settings, get_settings
from app.models.stem import Stem


WAV_CONTENT_TYPES = {"audio/wav", "audio/wave", "audio/x-wav", "application/octet-stream"}
ORGANIZATION_IMAGE_MAX_BYTES = 5 * 1024 * 1024
ORGANIZATION_IMAGE_TYPES = {
    "jpeg": ("jpg", "image/jpeg"),
    "png": ("png", "image/png"),
    "webp": ("webp", "image/webp"),
}


class StorageService:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root

    def song_dir(self, organization_id: int, song_id: int) -> Path:
        return self.organization_dir(organization_id) / "songs" / str(song_id)

    def organization_dir(self, organization_id: int) -> Path:
        return self.storage_root / "organizations" / str(organization_id)

    def source_path(self, organization_id: int, song_id: int, stem_id: int) -> Path:
        return self.song_dir(organization_id, song_id) / "source" / f"{stem_id}.wav"

    def converted_path(self, organization_id: int, song_id: int, stem_id: int) -> Path:
        return self.song_dir(organization_id, song_id) / "converted" / f"{stem_id}.m4a"

    def key_asset_path(self, organization_id: int, song_id: int, song_key_id: int, stem_id: int) -> Path:
        return self.song_dir(organization_id, song_id) / "keys" / str(song_key_id) / f"{stem_id}.m4a"

    def save_upload(self, organization_id: int, song_id: int, stem_id: int, upload: UploadFile) -> Path:
        self.validate_wav_upload(upload)
        destination = self.source_path(organization_id, song_id, stem_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
        return destination

    def cleanup_stem(self, stem: Stem) -> None:
        asset_paths = [asset.file_path for asset in stem.key_assets]
        for raw_path in (stem.source_path, stem.converted_path, *asset_paths):
            if raw_path:
                self._unlink_if_inside_storage(Path(raw_path))

    def cleanup_song(self, organization_id: int, song_id: int) -> None:
        shutil.rmtree(self.song_dir(organization_id, song_id), ignore_errors=True)

    def save_organization_image(self, organization_id: int, upload: UploadFile) -> Path:
        image_bytes = upload.file.read(ORGANIZATION_IMAGE_MAX_BYTES + 1)
        if len(image_bytes) > ORGANIZATION_IMAGE_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="Organization image must not exceed 5 MB",
            )
        image_type = self.detect_organization_image_type(image_bytes)
        extension, _media_type = ORGANIZATION_IMAGE_TYPES[image_type]
        organization_dir = self.organization_dir(organization_id)
        organization_dir.mkdir(parents=True, exist_ok=True)
        destination = organization_dir / f"image.{extension}"
        for existing in organization_dir.glob("image.*"):
            if existing != destination:
                existing.unlink(missing_ok=True)
        destination.write_bytes(image_bytes)
        return destination

    def cleanup_organization(self, organization_id: int) -> None:
        shutil.rmtree(self.organization_dir(organization_id), ignore_errors=True)

    def organization_image_media_type(self, path: Path) -> str:
        media_types = {f".{extension}": media_type for extension, media_type in ORGANIZATION_IMAGE_TYPES.values()}
        media_type = media_types.get(path.suffix.lower())
        if media_type is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization image not found")
        return media_type

    def detect_organization_image_type(self, content: bytes) -> str:
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        if content.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "webp"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization image must be PNG, JPEG, or WebP",
        )

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
    return StorageService(settings.storage_root)

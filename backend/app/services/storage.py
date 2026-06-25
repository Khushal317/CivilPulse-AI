import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Protocol

from google.cloud import storage as gcs  # type: ignore[import-untyped]

from app.core.config import get_settings
from app.core.errors import AppError


@dataclass(frozen=True, slots=True)
class StoredImage:
    key: str
    mime_type: str


class ImageStorage(Protocol):
    def save(self, data: bytes, mime_type: str, extension: str) -> StoredImage: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class LocalImageStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path_for_key(self, key: str) -> Path:
        pure_key = PurePosixPath(key)
        if pure_key.is_absolute() or ".." in pure_key.parts:
            raise AppError(
                code="invalid_image_key",
                message="The image key is invalid.",
                status_code=404,
            )
        path = (self._root / Path(*pure_key.parts)).resolve()
        if self._root not in path.parents:
            raise AppError(
                code="invalid_image_key",
                message="The image key is invalid.",
                status_code=404,
            )
        return path

    def save(self, data: bytes, mime_type: str, extension: str) -> StoredImage:
        key = f"issues/{uuid.uuid4().hex}{extension}"
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_bytes(data)
        temporary.replace(path)
        return StoredImage(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        path = self._path_for_key(key)
        if not path.is_file():
            raise AppError(
                code="image_not_found",
                message="The image was not found.",
                status_code=404,
            )
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path_for_key(key)
        path.unlink(missing_ok=True)


class GoogleCloudImageStorage:
    def __init__(self, bucket_name: str) -> None:
        self._bucket = gcs.Client().bucket(bucket_name)

    def save(self, data: bytes, mime_type: str, extension: str) -> StoredImage:
        key = f"issues/{uuid.uuid4().hex}{extension}"
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=mime_type)
        return StoredImage(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        blob = self._bucket.blob(key)
        if not blob.exists():
            raise AppError(
                code="image_not_found",
                message="The image was not found.",
                status_code=404,
            )
        return bytes(blob.download_as_bytes())

    def delete(self, key: str) -> None:
        self._bucket.blob(key).delete(if_generation_match=None)


@lru_cache
def get_image_storage() -> ImageStorage:
    settings = get_settings()
    if settings.storage_backend == "gcs":
        assert settings.storage_bucket is not None
        return GoogleCloudImageStorage(settings.storage_bucket)
    return LocalImageStorage(settings.local_storage_path)

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

    def list_keys(self, prefix: str = "issues/", limit: int = 500) -> list[str]: ...

    def health_check(self) -> None: ...


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
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(f"{path.suffix}.{uuid.uuid4().hex}.tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
        except OSError as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be stored right now. Please try again.",
                status_code=503,
            ) from exc
        return StoredImage(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        path = self._path_for_key(key)
        if not path.is_file():
            raise AppError(
                code="image_not_found",
                message="The image was not found.",
                status_code=404,
            )
        try:
            return path.read_bytes()
        except OSError as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be loaded right now. Please try again.",
                status_code=503,
            ) from exc

    def delete(self, key: str) -> None:
        path = self._path_for_key(key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be removed right now. Please try again.",
                status_code=503,
            ) from exc

    def list_keys(self, prefix: str = "issues/", limit: int = 500) -> list[str]:
        prefix_path = self._path_for_key(prefix)
        if not prefix_path.exists():
            return []
        keys: list[str] = []
        for path in sorted(prefix_path.rglob("*")):
            if path.is_file():
                keys.append(path.relative_to(self._root).as_posix())
            if len(keys) >= limit:
                break
        return keys

    def health_check(self) -> None:
        probe = self._root / f".civicpulse-health-{uuid.uuid4().hex}.tmp"
        try:
            probe.write_bytes(b"ok")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            raise AppError(
                code="storage_unavailable",
                message="Image storage is unavailable.",
                status_code=503,
            ) from exc


class GoogleCloudImageStorage:
    def __init__(self, bucket_name: str) -> None:
        self._bucket = gcs.Client().bucket(bucket_name)

    def save(self, data: bytes, mime_type: str, extension: str) -> StoredImage:
        key = f"issues/{uuid.uuid4().hex}{extension}"
        blob = self._bucket.blob(key)
        try:
            blob.upload_from_string(data, content_type=mime_type)
        except Exception as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be stored right now. Please try again.",
                status_code=503,
            ) from exc
        return StoredImage(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        blob = self._bucket.blob(key)
        try:
            exists = blob.exists()
        except Exception as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be loaded right now. Please try again.",
                status_code=503,
            ) from exc
        if not exists:
            raise AppError(
                code="image_not_found",
                message="The image was not found.",
                status_code=404,
            )
        try:
            return bytes(blob.download_as_bytes())
        except Exception as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be loaded right now. Please try again.",
                status_code=503,
            ) from exc

    def delete(self, key: str) -> None:
        try:
            self._bucket.blob(key).delete(if_generation_match=None)
        except Exception as exc:
            raise AppError(
                code="storage_unavailable",
                message="The image could not be removed right now. Please try again.",
                status_code=503,
            ) from exc

    def list_keys(self, prefix: str = "issues/", limit: int = 500) -> list[str]:
        try:
            return [blob.name for blob in self._bucket.list_blobs(prefix=prefix, max_results=limit)]
        except Exception as exc:
            raise AppError(
                code="storage_unavailable",
                message="Image storage is unavailable.",
                status_code=503,
            ) from exc

    def health_check(self) -> None:
        try:
            if not self._bucket.exists():
                raise AppError(
                    code="storage_unavailable",
                    message="Image storage is unavailable.",
                    status_code=503,
                )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                code="storage_unavailable",
                message="Image storage is unavailable.",
                status_code=503,
            ) from exc


@lru_cache
def get_image_storage() -> ImageStorage:
    settings = get_settings()
    if settings.storage_backend == "gcs":
        assert settings.storage_bucket is not None
        return GoogleCloudImageStorage(settings.storage_bucket)
    return LocalImageStorage(settings.local_storage_path)

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import Settings
from app.core.errors import AppError
from app.services.images import validate_image
from app.services.storage import LocalImageStorage


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), color=(120, 80, 30)).save(output, format="PNG")
    return output.getvalue()


def test_validates_actual_image_content() -> None:
    validated = validate_image(png_bytes(), Settings())

    assert validated.mime_type == "image/png"
    assert validated.extension == ".png"
    assert validated.width == 8
    assert validated.height == 8


def test_rejects_non_image_content() -> None:
    with pytest.raises(AppError, match="valid JPEG"):
        validate_image(b"not-an-image", Settings())


def test_rejects_image_over_limit_before_decoding() -> None:
    settings = Settings(max_image_size_bytes=1_048_576)

    with pytest.raises(AppError) as caught:
        validate_image(b"x" * (1_048_576 + 1), settings)

    assert caught.value.code == "image_too_large"


def test_local_storage_generates_safe_names_and_blocks_traversal(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path)

    stored = storage.save(png_bytes(), "image/png", ".png")

    assert stored.key.startswith("issues/")
    assert ".." not in stored.key
    assert storage.read(stored.key).startswith(b"\x89PNG")
    with pytest.raises(AppError) as caught:
        storage.read("../secret.png")
    assert caught.value.code == "invalid_image_key"


def test_local_storage_health_and_listing(tmp_path: Path) -> None:
    storage = LocalImageStorage(tmp_path)
    first = storage.save(b"one", "image/png", ".png")
    second = storage.save(b"two", "image/png", ".png")

    storage.health_check()

    assert len(storage.list_keys(limit=1)) == 1
    assert storage.list_keys(limit=10) == sorted([first.key, second.key])

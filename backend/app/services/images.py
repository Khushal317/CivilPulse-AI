from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import AppError

FORMAT_DETAILS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
}


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    data: bytes
    mime_type: str
    extension: str
    width: int
    height: int


def validate_image(data: bytes, settings: Settings) -> ValidatedImage:
    if not data:
        raise AppError(
            code="empty_image",
            message="Please choose an image to upload.",
            status_code=422,
        )
    if len(data) > settings.max_image_size_bytes:
        raise AppError(
            code="image_too_large",
            message=(
                f"The image must be smaller than {settings.max_image_size_bytes // 1_048_576} MB."
            ),
            status_code=413,
        )

    Image.MAX_IMAGE_PIXELS = settings.max_image_pixels
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise AppError(
            code="invalid_image",
            message="Upload a valid JPEG, PNG, or WebP image.",
            status_code=422,
        ) from exc

    if image_format not in FORMAT_DETAILS:
        raise AppError(
            code="unsupported_image_type",
            message="Only JPEG, PNG, and WebP images are supported.",
            status_code=415,
        )

    mime_type, extension = FORMAT_DETAILS[image_format]
    return ValidatedImage(
        data=data,
        mime_type=mime_type,
        extension=extension,
        width=width,
        height=height,
    )

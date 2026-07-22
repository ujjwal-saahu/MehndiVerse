"""Shared image validation, re-encoding, and thumbnailing.

Every uploaded image (avatars, design photos) is decoded and re-saved
through Pillow before it ever reaches storage. This serves two purposes at
once:

1. Validation — a file that Pillow can't decode as one of the allowed
   formats is rejected, regardless of what `Content-Type` the client claimed.
2. Metadata stripping — Pillow's re-encode only copies pixel data, not the
   source file's EXIF/ICC/XMP blocks, so GPS coordinates or device
   identifiers embedded by a phone camera never leave this step. EXIF
   orientation is applied to the pixels first (`exif_transpose`) so the
   image doesn't appear sideways once the orientation tag is gone.

See docs/profile-and-privacy.md#avatar-uploads and
docs/design-catalog.md#image-upload-pipeline.
"""

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_AVATAR_BYTES = 5 * 1024 * 1024  # matches the `avatars` bucket's file_size_limit
MAX_DESIGN_IMAGE_BYTES = 10 * 1024 * 1024  # matches the `portfolio` bucket's file_size_limit
# Phone camera photos run larger than portfolio marketing images — matches
# the `preview-projects` bucket's file_size_limit. See
# docs/hand-foot-preview.md#upload-validation.
MAX_PREVIEW_IMAGE_BYTES = 15 * 1024 * 1024
# A memory/decompression-bomb safeguard (docs/hand-foot-preview.md#memory-
# and-performance-safeguards): a small file can still decode to an enormous
# pixel buffer. Pillow's own default (`Image.MAX_IMAGE_PIXELS`, ~89
# megapixels) already guards every call in this module; this is a tighter,
# preview-specific cap since these images are re-encoded synchronously in
# the request path, not queued for background processing.
MAX_PREVIEW_IMAGE_PIXELS = 24_000_000  # e.g. 6000x4000

_ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class InvalidImageError(Exception):
    """Raised when the uploaded bytes fail validation."""


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    content_type: str
    extension: str
    width: int
    height: int
    checksum_sha256: str


def process_image_upload(
    raw: bytes, *, max_bytes: int, max_pixels: int | None = None
) -> ProcessedImage:
    if not raw:
        raise InvalidImageError("The uploaded file is empty.")
    if len(raw) > max_bytes:
        raise InvalidImageError(f"Image exceeds the {max_bytes // (1024 * 1024)} MB size limit.")

    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("File is not a valid image.") from exc

    # verify() leaves the file object unusable for further decoding — reopen.
    image: Image.Image = Image.open(io.BytesIO(raw))
    source_format = image.format
    if source_format not in _ALLOWED_FORMATS:
        raise InvalidImageError("Unsupported image type. Use JPEG, PNG, or WEBP.")
    if max_pixels is not None and image.width * image.height > max_pixels:
        raise InvalidImageError("Image resolution is too large.")

    image = ImageOps.exif_transpose(image) or image

    output_format = source_format
    if output_format == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    elif output_format in ("PNG", "WEBP") and image.mode not in ("RGB", "RGBA", "L", "LA"):
        image = image.convert("RGBA")

    buffer = io.BytesIO()
    # No `exif=` kwarg is passed, so Pillow's encoder writes no metadata block
    # at all — this is what strips EXIF/ICC/XMP, not an explicit "remove" step.
    image.save(buffer, format=output_format)
    data = buffer.getvalue()

    extension = _ALLOWED_FORMATS[output_format]
    content_type = "image/jpeg" if extension == "jpg" else f"image/{extension}"
    return ProcessedImage(
        data=data,
        content_type=content_type,
        extension=extension,
        width=image.width,
        height=image.height,
        checksum_sha256=hashlib.sha256(data).hexdigest(),
    )


def process_avatar_upload(raw: bytes) -> ProcessedImage:
    return process_image_upload(raw, max_bytes=MAX_AVATAR_BYTES)


def process_preview_photo_upload(raw: bytes) -> ProcessedImage:
    return process_image_upload(
        raw, max_bytes=MAX_PREVIEW_IMAGE_BYTES, max_pixels=MAX_PREVIEW_IMAGE_PIXELS
    )


def generate_thumbnail(processed: ProcessedImage, *, max_dimension: int) -> bytes:
    """Resizes the already-validated/re-encoded image to fit within a
    `max_dimension` x `max_dimension` box, preserving aspect ratio. Since
    `processed.data` has already had metadata stripped and format normalized,
    thumbnails never re-introduce EXIF or re-validate the source format."""
    image = Image.open(io.BytesIO(processed.data))
    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    output_format = "JPEG" if processed.extension == "jpg" else processed.extension.upper()
    image.save(buffer, format=output_format)
    return buffer.getvalue()

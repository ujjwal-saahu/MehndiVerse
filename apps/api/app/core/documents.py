"""Verification-document validation — see
docs/artist-verification.md#document-privacy.

Unlike avatars/design photos (`app/core/images.py`), a verification document
can legitimately be a PDF (a scanned ID or business license), which Pillow
can't decode or re-encode. Images still go through the same
validate-and-re-encode pipeline as everywhere else in the app (so a phone
photo of an ID doesn't leak GPS EXIF data); PDFs are only validated
(magic-byte + size check), never re-encoded — there's no equivalent safe,
lossless way to strip a PDF's metadata without a much heavier dependency,
and PDFs don't carry EXIF-style geolocation the way photos do.
"""

import hashlib
from dataclasses import dataclass

from app.core.images import InvalidImageError, ProcessedImage, process_image_upload

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # matches the `verification-documents` bucket's limit
ALLOWED_DOCUMENT_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}

_PDF_MAGIC_BYTES = b"%PDF-"


class InvalidDocumentError(Exception):
    """Raised when uploaded document bytes fail validation."""


@dataclass(frozen=True)
class ProcessedDocument:
    data: bytes
    content_type: str
    extension: str
    checksum_sha256: str


def process_document_upload(raw: bytes, *, content_type: str) -> ProcessedDocument:
    if not raw:
        raise InvalidDocumentError("The uploaded file is empty.")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise InvalidDocumentError(
            f"File exceeds the {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB size limit."
        )
    if content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise InvalidDocumentError("Unsupported file type. Use JPEG, PNG, or PDF.")

    if content_type == "application/pdf":
        if not raw.startswith(_PDF_MAGIC_BYTES):
            raise InvalidDocumentError("File is not a valid PDF.")
        return ProcessedDocument(
            data=raw,
            content_type="application/pdf",
            extension="pdf",
            checksum_sha256=hashlib.sha256(raw).hexdigest(),
        )

    try:
        processed: ProcessedImage = process_image_upload(raw, max_bytes=MAX_DOCUMENT_BYTES)
    except InvalidImageError as exc:
        raise InvalidDocumentError(str(exc)) from exc
    return ProcessedDocument(
        data=processed.data,
        content_type=processed.content_type,
        extension=processed.extension,
        checksum_sha256=processed.checksum_sha256,
    )

"""Safe handling of uploaded photos.

Every upload is treated as hostile until proven otherwise:
1. The real format is detected from the bytes (not the filename or the
   Content-Type header); only JPEG, PNG, and WebP are accepted.
2. Size and pixel count are capped before full decoding (decompression bombs).
3. Metadata is read *first*, because it is evidence for the photo-authenticity
   check (M5): camera make/model, capture time, editing software, and generator
   hints that AI tools write into PNG text chunks. GPS coordinates are never kept,
   only whether they were present.
4. The image is then re-encoded to a fresh JPEG, which drops all metadata and any
   payload hidden in the original file.
"""

import hashlib
import io
import string
import warnings
from dataclasses import dataclass, field
from typing import Any

from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
OUTPUT_CONTENT_TYPE = "image/jpeg"

# PNG text keys that image generators commonly write.
_GENERATOR_KEYS = {"parameters", "prompt", "workflow", "generator", "ai_generated", "c2pa"}
_PRINTABLE = set(string.printable) - set("\r\n\t\x0b\x0c")


class UploadRejected(ValueError):
    """The upload isn't an acceptable image. The message is safe to show the user."""


@dataclass
class ProcessedPhoto:
    data: bytes
    sha256: str  # of the original upload, to spot the same file being reused
    perceptual_hash: str  # of the image content, to spot near-duplicates
    width: int
    height: int
    metadata: dict[str, Any] = field(default_factory=dict)
    content_type: str = OUTPUT_CONTENT_TYPE


def _clean(value: object, limit: int = 100) -> str:
    text = value.decode(errors="replace") if isinstance(value, bytes) else str(value)
    return "".join(ch for ch in text if ch in _PRINTABLE).strip()[:limit]


def _metadata_summary(
    img: Image.Image, original_format: str, original_bytes: int
) -> dict[str, Any]:
    exif = img.getexif()
    tags = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
    try:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
    except Exception:
        exif_ifd = {}
    captured = exif_ifd.get(ExifTags.Base.DateTimeOriginal) or tags.get("DateTime")

    summary: dict[str, Any] = {
        "original_format": original_format,
        "original_bytes": original_bytes,
        "original_width": img.width,
        "original_height": img.height,
        "has_exif": len(exif) > 0,
        "has_gps": ExifTags.IFD.GPSInfo in exif,  # presence only; coordinates are dropped
    }
    for key, tag in (("camera_make", "Make"), ("camera_model", "Model"), ("software", "Software")):
        if tags.get(tag):
            summary[key] = _clean(tags[tag])
    if captured:
        summary["captured_at"] = _clean(captured, 32)

    text_keys = sorted(_clean(k, 40).lower() for k in getattr(img, "text", {}) or {})
    if text_keys:
        summary["png_text_keys"] = text_keys[:20]
        summary["has_generator_hints"] = any(k in _GENERATOR_KEYS for k in text_keys)
    return summary


def dhash(img: Image.Image, size: int = 8) -> str:
    """64-bit difference hash: near-identical images give near-identical hashes."""
    small = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(small.tobytes())  # mode "L": one byte (0-255) per pixel
    bits = 0
    for row in range(size):
        for col in range(size):
            left = pixels[row * (size + 1) + col]
            right = pixels[row * (size + 1) + col + 1]
            bits = (bits << 1) | (left > right)
    return f"{bits:016x}"


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def process_upload(raw: bytes, *, max_pixels: int, max_side: int) -> ProcessedPhoto:
    if not raw:
        raise UploadRejected("The photo is empty.")

    with warnings.catch_warnings():
        # Pillow warns before it errors on huge images; treat both as bombs.
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            Image.MAX_IMAGE_PIXELS = max_pixels
            probe = Image.open(io.BytesIO(raw))
            fmt = (probe.format or "").upper()
            if fmt not in ALLOWED_FORMATS:
                raise UploadRejected("Please upload a JPEG, PNG, or WebP photo.")
            if probe.width * probe.height > max_pixels:
                raise UploadRejected("That photo is too large. Please upload a smaller one.")
            probe.verify()  # structural check; the object can't be used afterwards

            img = Image.open(io.BytesIO(raw))
            img.load()
        except UploadRejected:
            raise
        except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
            raise UploadRejected("That photo is too large. Please upload a smaller one.") from exc
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
            raise UploadRejected("That file isn't a readable photo.") from exc

    metadata = _metadata_summary(img, fmt, len(raw))

    # Honour the camera's rotation, then rebuild the pixels without any metadata.
    clean = ImageOps.exif_transpose(img).convert("RGB")
    clean.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    clean.save(out, format="JPEG", quality=90, optimize=True)

    return ProcessedPhoto(
        data=out.getvalue(),
        sha256=hashlib.sha256(raw).hexdigest(),
        perceptual_hash=dhash(clean),
        width=clean.width,
        height=clean.height,
        metadata=metadata,
    )

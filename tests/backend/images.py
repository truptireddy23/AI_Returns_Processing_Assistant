"""Builders for test photos with specific formats and metadata."""

import io

from PIL import Image, PngImagePlugin
from PIL.ExifTags import IFD, Base


def jpeg(
    size: tuple[int, int] = (64, 48),
    color: tuple[int, int, int] = (200, 30, 30),
    *,
    make: str | None = None,
    model: str | None = None,
    gps: bool = False,
    orientation: int | None = None,
) -> bytes:
    img = Image.new("RGB", size, color)
    exif = Image.Exif()
    if make:
        exif[Base.Make] = make
    if model:
        exif[Base.Model] = model
    if orientation:
        exif[Base.Orientation] = orientation
    if gps:
        exif[IFD.GPSInfo] = {1: "N", 2: (40.0, 6.0, 0.0)}
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def png(size: tuple[int, int] = (64, 48), *, text: dict[str, str] | None = None) -> bytes:
    img = Image.new("RGB", size, (30, 120, 200))
    info = PngImagePlugin.PngInfo()
    for k, v in (text or {}).items():
        info.add_text(k, v)
    out = io.BytesIO()
    img.save(out, format="PNG", pnginfo=info)
    return out.getvalue()


def gif() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (8, 8)).save(out, format="GIF")
    return out.getvalue()


def huge_png(width: int = 12_000, height: int = 12_000) -> bytes:
    """Few kilobytes on disk, ~144 million pixels when decoded."""
    out = io.BytesIO()
    Image.new("1", (width, height)).save(out, format="PNG", optimize=True)
    return out.getvalue()

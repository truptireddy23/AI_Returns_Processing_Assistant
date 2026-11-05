"""Upload catalog photos to the product-photos bucket.

    make product-photos            # reads ../Photos (the repo's Photos/ folder)

Expected layout: `Photos/<anything>/<product name or SKU>/<images>`, e.g.
`Photos/shoes/Trailrunner Mesh Sneaker/img1.webp`. Images are used in filename
order; the first is the product's main photo.

Each image is decoded, size-capped, rotated per its EXIF, flattened onto white,
scaled to at most 1200 px, and saved as a clean JPEG (no metadata). Re-running
uploads only photos whose source file changed and removes photos that were
deleted from a folder. Keys contain a hash of the content, so a changed photo
gets a new URL and long browser caching is safe.
"""

import asyncio
import hashlib
import io
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import db
from returnguard.config import get_settings
from returnguard.images import dhash
from returnguard.log_config import configure_logging
from returnguard.models import Product, ProductPhoto
from returnguard.storage import Storage, StorageError, get_storage

log = structlog.get_logger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
MAX_SIDE = 1200
MAX_PIXELS = 60_000_000
CONTENT_TYPE = "image/jpeg"


@dataclass
class Prepared:
    data: bytes
    width: int
    height: int
    source_sha256: str
    perceptual_hash: str


@dataclass
class Summary:
    uploaded: int = 0
    unchanged: int = 0
    removed: int = 0
    unmatched_folders: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


def prepare(raw: bytes) -> Prepared:
    """Decode and re-encode one catalog photo. Raises ValueError if it can't be used."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            Image.MAX_IMAGE_PIXELS = MAX_PIXELS
            opened = Image.open(io.BytesIO(raw))
            opened.load()
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:  # fmt: skip
            raise ValueError(f"not a usable image ({type(exc).__name__})") from exc
    img: Image.Image = ImageOps.exif_transpose(opened)
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        flat = Image.new("RGB", rgba.size, (255, 255, 255))
        flat.paste(rgba, mask=rgba.getchannel("A"))
        img = flat
    else:
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True, progressive=True)
    return Prepared(
        data=out.getvalue(),
        width=img.width,
        height=img.height,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        perceptual_hash=dhash(img),
    )


def _key(product: Product, position: int, prepared: Prepared) -> str:
    return f"products/{product.sku}/{position}-{prepared.source_sha256[:12]}.jpg"


def scan(root: Path) -> dict[Path, list[Path]]:
    """Folders that contain images, each with its images in filename order."""
    folders: dict[Path, list[Path]] = {}
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES:
            folders.setdefault(f.parent, []).append(f)
    return folders


def _match(folder: Path, by_name: dict[str, Product], by_sku: dict[str, Product]) -> Product | None:
    name = folder.name.strip().lower()
    return by_name.get(name) or by_sku.get(name.upper())


async def sync_product(
    session: AsyncSession, storage: Storage, product: Product, files: list[Path], summary: Summary
) -> None:
    existing = {
        p.position: p
        for p in await session.scalars(
            select(ProductPhoto).where(ProductPhoto.product_id == product.id)
        )
    }
    stale_keys: list[str] = []
    position = 0
    for path in files:
        try:
            prepared = prepare(await asyncio.to_thread(path.read_bytes))
        except ValueError as exc:
            summary.skipped_files.append(f"{path}: {exc}")
            continue
        current = existing.pop(position, None)
        if current is not None and current.source_sha256 == prepared.source_sha256:
            summary.unchanged += 1
            position += 1
            continue
        key = _key(product, position, prepared)
        await storage.put(key, prepared.data, CONTENT_TYPE)
        if current is not None:
            stale_keys.append(current.storage_key)
            await session.delete(current)
            await session.flush()
        session.add(
            ProductPhoto(
                product_id=product.id,
                position=position,
                storage_key=key,
                content_type=CONTENT_TYPE,
                width=prepared.width,
                height=prepared.height,
                size_bytes=len(prepared.data),
                source_sha256=prepared.source_sha256,
                perceptual_hash=prepared.perceptual_hash,
            )
        )
        summary.uploaded += 1
        position += 1
    # Photos removed from the folder.
    for leftover in existing.values():
        stale_keys.append(leftover.storage_key)
        await session.delete(leftover)
        summary.removed += 1
    await session.commit()
    for key in stale_keys:  # only after the rows no longer point at them
        try:
            await storage.delete(key)
        except StorageError:
            log.warning("product_photos.orphan", key=key)


async def sync_all(session: AsyncSession, root: Path, storage: Storage | None = None) -> Summary:
    storage = storage or get_storage(get_settings().product_photo_bucket)
    products = list(await session.scalars(select(Product)))
    by_name = {p.name.lower(): p for p in products}
    by_sku = {p.sku.upper(): p for p in products}
    summary = Summary()

    for folder, files in (await asyncio.to_thread(scan, root)).items():
        product = _match(folder, by_name, by_sku)
        if product is None:
            summary.unmatched_folders.append(str(folder.relative_to(root)))
            continue
        await sync_product(session, storage, product, files, summary)
        log.info("product_photos.synced", sku=product.sku, photos=len(files))
    return summary


async def _main(root: Path) -> int:
    async for session in db.get_session():
        summary = await sync_all(session, root)
    await db.dispose_engine()
    log.info(
        "product_photos.done",
        uploaded=summary.uploaded,
        unchanged=summary.unchanged,
        removed=summary.removed,
    )
    for folder in summary.unmatched_folders:
        log.warning(
            "product_photos.unmatched_folder", folder=folder, hint="name it after a product or SKU"
        )
    for skipped in summary.skipped_files:
        log.warning("product_photos.skipped_file", detail=skipped)
    return 0


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "../../Photos").resolve()
    if not root.is_dir():
        sys.exit(f"Photos folder not found: {root}")
    sys.exit(asyncio.run(_main(root)))


if __name__ == "__main__":
    main()

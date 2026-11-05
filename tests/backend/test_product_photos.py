"""Catalog photos: preparing, syncing a Photos/ folder, and serving them."""

import io
import uuid
from pathlib import Path

import httpx
import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import product_photos
from returnguard.config import get_settings
from returnguard.models import Product, ProductCategory, ProductPhoto
from returnguard.storage import StorageError, get_storage

from .factories import PASSWORD, make_order, make_user


def encode(fmt: str, size: tuple[int, int] = (300, 200), mode: str = "RGB", **kw: object) -> bytes:
    img = Image.new(mode, size, (200, 30, 30, 128) if mode == "RGBA" else (200, 30, 30))
    out = io.BytesIO()
    img.save(out, format=fmt, **kw)
    return out.getvalue()


# --- Preparing one photo ----------------------------------------------------


@pytest.mark.parametrize("fmt", ["WEBP", "PNG", "JPEG"])
def test_photos_become_clean_jpegs(fmt: str) -> None:
    exif = Image.Exif()
    exif[0x010F] = "SomeCamera"  # Make
    raw = encode(fmt, exif=exif.tobytes()) if fmt in ("JPEG", "WEBP") else encode(fmt)

    prepared = product_photos.prepare(raw)

    img = Image.open(io.BytesIO(prepared.data))
    assert img.format == "JPEG"
    assert len(img.getexif()) == 0
    assert (prepared.width, prepared.height) == (300, 200)


def test_avif_is_accepted_even_with_a_webp_name() -> None:
    try:
        raw = encode("AVIF")
    except (KeyError, OSError, ValueError):
        pytest.skip("this Pillow build can't write AVIF")
    assert Image.open(io.BytesIO(product_photos.prepare(raw).data)).format == "JPEG"


def test_transparency_is_flattened_onto_white() -> None:
    prepared = product_photos.prepare(encode("PNG", mode="RGBA"))
    pixel = Image.open(io.BytesIO(prepared.data)).getpixel((0, 0))
    assert isinstance(pixel, tuple) and all(c > 100 for c in pixel)  # blended, not black


def test_large_photos_are_scaled_to_1200() -> None:
    prepared = product_photos.prepare(encode("JPEG", size=(3000, 1500)))
    assert (prepared.width, prepared.height) == (1200, 600)


def test_non_images_are_refused() -> None:
    with pytest.raises(ValueError, match="not a usable image"):
        product_photos.prepare(b"not an image")


# --- Syncing a folder --------------------------------------------------------


async def make_shoe(
    session: AsyncSession, name: str = "Test Runner", sku: str | None = None
) -> Product:
    product = Product(
        sku=sku or f"T-{uuid.uuid4().hex[:6]}",
        name=name,
        description="A test shoe.",
        category=ProductCategory.FOOTWEAR,
        price_cents=5000,
        photo_key="/products/T.png",
    )
    session.add(product)
    await session.flush()
    return product


def write(folder: Path, name: str, data: bytes) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)


async def photos_of(session: AsyncSession, product: Product) -> list[ProductPhoto]:
    return list(
        await session.scalars(
            select(ProductPhoto)
            .where(ProductPhoto.product_id == product.id)
            .order_by(ProductPhoto.position)
            .execution_options(populate_existing=True)
        )
    )


@pytest.mark.db
async def test_sync_uploads_matches_by_name_or_sku_and_reports_strays(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    by_name = await make_shoe(db_session, name="Trail Tester")
    by_sku = await make_shoe(db_session, name="Something Else", sku="T-SKU1")
    write(tmp_path / "shoes" / "trail tester", "img2.webp", encode("WEBP", (400, 400)))
    write(tmp_path / "shoes" / "trail tester", "img1.webp", encode("WEBP", (500, 300)))
    write(tmp_path / "shoes" / "T-SKU1", "a.png", encode("PNG"))
    write(tmp_path / "shoes" / "Not A Product", "x.jpg", encode("JPEG"))
    write(tmp_path / "shoes" / "trail tester", "notes.txt", b"ignored")

    summary = await product_photos.sync_all(db_session, tmp_path)

    assert summary.uploaded == 3
    assert summary.unmatched_folders == ["shoes/Not A Product"]
    photos = await photos_of(db_session, by_name)
    assert [(p.position, p.width) for p in photos] == [(0, 500), (1, 400)]  # filename order
    assert len(await photos_of(db_session, by_sku)) == 1
    storage = get_storage(get_settings().product_photo_bucket)
    assert (await storage.get(photos[0].storage_key))[:2] == b"\xff\xd8"


@pytest.mark.db
async def test_sync_is_idempotent_and_follows_changes(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    shoe = await make_shoe(db_session, name="Change Tester")
    folder = tmp_path / "shoes" / "Change Tester"
    write(folder, "img1.webp", encode("WEBP", (300, 300)))
    write(folder, "img2.webp", encode("WEBP", (310, 310)))
    await product_photos.sync_all(db_session, tmp_path)
    first = await photos_of(db_session, shoe)

    again = await product_photos.sync_all(db_session, tmp_path)
    assert (again.uploaded, again.unchanged, again.removed) == (0, 2, 0)

    write(folder, "img1.webp", encode("WEBP", (320, 320)))  # replace the main photo
    (folder / "img2.webp").unlink()  # and remove the second
    changed = await product_photos.sync_all(db_session, tmp_path)

    assert (changed.uploaded, changed.removed) == (1, 1)
    now = await photos_of(db_session, shoe)
    assert len(now) == 1 and now[0].width == 320
    assert now[0].storage_key != first[0].storage_key  # new content, new URL
    storage = get_storage(get_settings().product_photo_bucket)
    for old in first:
        with pytest.raises(StorageError):  # old objects are deleted
            await storage.get(old.storage_key)


# --- Serving -----------------------------------------------------------------


@pytest.mark.db
async def test_catalog_lists_photos_and_serves_them_publicly(
    db_client: httpx.AsyncClient, db_session: AsyncSession, tmp_path: Path
) -> None:
    shoe = await make_shoe(db_session, name="Served Shoe")
    plain = await make_shoe(db_session, name="No Photos Shoe")
    write(tmp_path / "x" / "Served Shoe", "1.webp", encode("WEBP"))
    write(tmp_path / "x" / "Served Shoe", "2.webp", encode("WEBP", (200, 300)))
    await product_photos.sync_all(db_session, tmp_path)

    listing = {p["id"]: p for p in (await db_client.get("/api/products")).json()}
    served = listing[str(shoe.id)]
    assert len(served["photos"]) == 2
    assert served["photo_url"] == served["photos"][0]["url"]
    assert listing[str(plain.id)]["photos"] == []
    assert listing[str(plain.id)]["photo_url"] == "/products/T.png"  # illustration fallback

    res = await db_client.get(served["photo_url"])  # no sign-in needed
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert "immutable" in res.headers["cache-control"]
    assert res.content[:2] == b"\xff\xd8"

    wrong_product = served["photo_url"].replace(str(shoe.id), str(plain.id))
    assert (await db_client.get(wrong_product)).status_code == 404


@pytest.mark.db
async def test_orders_and_returns_show_the_main_photo(
    db_client: httpx.AsyncClient, db_session: AsyncSession, tmp_path: Path
) -> None:
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)  # its product is named "Test Sneaker"
    write(tmp_path / "shoes" / "Test Sneaker", "1.webp", encode("WEBP"))
    await product_photos.sync_all(db_session, tmp_path)
    login = await db_client.post(
        "/api/auth/login", json={"email": customer.email, "password": PASSWORD}
    )
    assert login.status_code == 200

    item = (await db_client.get("/api/orders")).json()[0]["items"][0]
    detail = (await db_client.get(f"/api/orders/{order.id}")).json()["items"][0]

    assert item["photo_url"].startswith("/api/products/")
    assert detail["photo_url"] == item["photo_url"]

"""Public: the product catalog. Anyone may browse; buying needs a customer account."""

import uuid

import structlog
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from returnguard.auth import DbSession
from returnguard.config import get_settings
from returnguard.models import Product, ProductCategory, ProductPhoto
from returnguard.storage import StorageError, get_storage

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/products", tags=["catalog"])


class ProductPhotoOut(BaseModel):
    id: str
    url: str
    width: int
    height: int


def photo_url(photo: ProductPhoto) -> str:
    return f"/api/products/{photo.product_id}/photos/{photo.id}"


def main_photo_url(p: Product) -> str | None:
    """The first uploaded photo, else the generated illustration. Needs `photos` loaded."""
    return photo_url(p.photos[0]) if p.photos else p.photo_key


# Load this with every Product whose photo is shown.
WITH_PHOTOS = selectinload(Product.photos)


class ProductOut(BaseModel):
    id: str
    sku: str
    name: str
    description: str
    category: ProductCategory
    price_cents: int
    is_final_sale: bool
    photo_url: str | None
    photos: list[ProductPhotoOut]


def product_out(p: Product) -> ProductOut:
    return ProductOut(
        id=str(p.id),
        sku=p.sku,
        name=p.name,
        description=p.description,
        category=p.category,
        price_cents=p.price_cents,
        is_final_sale=p.is_final_sale,
        photo_url=main_photo_url(p),
        photos=[
            ProductPhotoOut(id=str(ph.id), url=photo_url(ph), width=ph.width, height=ph.height)
            for ph in p.photos
        ],
    )


@router.get("", response_model=list[ProductOut])
async def list_products(db: DbSession, category: ProductCategory | None = None) -> list[ProductOut]:
    query = select(Product).options(WITH_PHOTOS).order_by(Product.category, Product.name)
    if category:
        query = query.where(Product.category == category)
    return [product_out(p) for p in await db.scalars(query)]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: DbSession) -> ProductOut:
    product = await db.scalar(select(Product).where(Product.id == product_id).options(WITH_PHOTOS))
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product_out(product)


@router.get(
    "/{product_id}/photos/{photo_id}",
    responses={200: {"content": {"image/jpeg": {}}}},
    response_class=Response,
)
async def get_product_photo(product_id: uuid.UUID, photo_id: uuid.UUID, db: DbSession) -> Response:
    """Public: catalog photos. Keys change whenever a photo changes, so cache for a year."""
    photo = await db.get(ProductPhoto, photo_id)
    if photo is None or photo.product_id != product_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    try:
        data = await get_storage(get_settings().product_photo_bucket).get(photo.storage_key)
    except StorageError as exc:
        log.error("catalog.photo_read_failed", photo_id=str(photo.id), error=str(exc))
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Photo unavailable") from exc
    return Response(
        content=data,
        media_type=photo.content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )

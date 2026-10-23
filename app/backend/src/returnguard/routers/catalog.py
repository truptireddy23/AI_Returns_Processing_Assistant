"""Public: the product catalog. Anyone may browse; buying needs a customer account."""

import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from returnguard.auth import DbSession
from returnguard.models import Product, ProductCategory

router = APIRouter(prefix="/api/products", tags=["catalog"])


class ProductOut(BaseModel):
    id: str
    sku: str
    name: str
    description: str
    category: ProductCategory
    price_cents: int
    is_final_sale: bool
    photo_url: str | None


def product_out(p: Product) -> ProductOut:
    return ProductOut(
        id=str(p.id),
        sku=p.sku,
        name=p.name,
        description=p.description,
        category=p.category,
        price_cents=p.price_cents,
        is_final_sale=p.is_final_sale,
        # Catalog images ship with the frontend (public/products/), so the key is a URL path.
        photo_url=p.photo_key,
    )


@router.get("", response_model=list[ProductOut])
async def list_products(db: DbSession, category: ProductCategory | None = None) -> list[ProductOut]:
    query = select(Product).order_by(Product.category, Product.name)
    if category:
        query = query.where(Product.category == category)
    return [product_out(p) for p in await db.scalars(query)]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: uuid.UUID, db: DbSession) -> ProductOut:
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product_out(product)

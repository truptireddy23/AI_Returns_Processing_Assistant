"""Fetch the benchmark photos that are not in git (team members only).

    python -m returnguard.benchmark_photos

Read-only: copies catalog reference photos (third-party images) and one uploaded return
photo from the team's private buckets into docs/study_materials/benchmark/. Needs the
team's DATABASE_URL and AWS_* settings in app/.env.
"""

import asyncio
from pathlib import Path

from sqlalchemy import select

from returnguard import db
from returnguard.config import get_settings
from returnguard.models import Product, ProductPhoto, Return, ReturnPhoto
from returnguard.storage import get_storage

BENCH = Path(__file__).resolve().parents[4] / "docs" / "study_materials" / "benchmark"
CATALOG_SKUS = ("FW-002", "HM-003", "EL-001")
COOKWARE_CASE = 223  # a teammate's test upload of a different cookware set


async def main_async() -> None:
    bucket = get_storage(get_settings().product_photo_bucket)
    async for session in db.get_session():
        for sku in CATALOG_SKUS:
            key = await session.scalar(
                select(ProductPhoto.storage_key)
                .join(Product, Product.id == ProductPhoto.product_id)
                .where(Product.sku == sku)
                .order_by(ProductPhoto.position)
                .limit(1)
            )
            if key is None:
                raise SystemExit(f"No catalog photo for {sku}")
            data = await bucket.get(key)
            targets = [BENCH / "catalog" / sku / "1.jpg"]
            if sku == "FW-002":
                targets.append(BENCH / "photos" / "court_shoe_catalog_reused.jpg")
            for target in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        key = await session.scalar(
            select(ReturnPhoto.storage_key)
            .join(Return, Return.id == ReturnPhoto.return_id)
            .where(Return.case_number == COOKWARE_CASE)
        )
        if key is None:
            raise SystemExit(f"No photo on return R-{COOKWARE_CASE}")
        (BENCH / "photos" / "red_cookware_wrong_item.jpg").write_bytes(await get_storage().get(key))
    await db.dispose_engine()
    print(f"fetched {len(CATALOG_SKUS)} catalog photos and 1 return photo")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

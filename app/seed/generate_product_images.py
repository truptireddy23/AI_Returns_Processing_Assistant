"""Generate the catalog's product images (app/frontend/public/products/<SKU>.png).

Simple, license-free illustrations: a category silhouette in a per-product
colour, with the product name. Re-run after adding products:

    cd app/backend && uv run python ../seed/generate_product_images.py
"""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SEED_DIR = Path(__file__).resolve().parent
OUT_DIR = SEED_DIR.parent / "frontend" / "public" / "products"
SIZE = 800

BACKGROUNDS = {
    "footwear": (238, 242, 247),
    "clothing": (245, 240, 235),
    "electronics": (236, 240, 244),
    "home": (241, 243, 237),
}


def accent(sku: str) -> tuple[int, int, int]:
    h = hashlib.sha256(sku.encode()).digest()
    return (60 + h[0] % 140, 60 + h[1] % 140, 60 + h[2] % 140)


def draw_footwear(d: ImageDraw.ImageDraw, c: tuple[int, int, int]) -> None:
    d.rounded_rectangle((150, 470, 650, 520), radius=20, fill=(60, 60, 60))  # sole
    d.polygon([(170, 470), (190, 330), (330, 300), (430, 380), (630, 420), (650, 470)], fill=c)
    for x in range(260, 400, 35):  # laces
        d.line((x, 345, x + 30, 385), fill=(250, 250, 250), width=8)


def draw_clothing(d: ImageDraw.ImageDraw, c: tuple[int, int, int]) -> None:
    d.polygon(
        [
            (300, 220),
            (500, 220),
            (640, 300),
            (590, 380),
            (540, 350),
            (540, 580),
            (260, 580),
            (260, 350),
            (210, 380),
            (160, 300),
        ],
        fill=c,
    )
    d.ellipse((350, 195, 450, 260), fill=BACKGROUNDS["clothing"])


def draw_electronics(d: ImageDraw.ImageDraw, c: tuple[int, int, int]) -> None:
    d.rounded_rectangle((230, 220, 570, 560), radius=40, fill=c)
    d.ellipse((320, 310, 480, 470), fill=(30, 30, 30))
    d.ellipse((365, 355, 435, 425), fill=(90, 90, 90))


def draw_home(d: ImageDraw.ImageDraw, c: tuple[int, int, int]) -> None:
    d.rounded_rectangle((250, 260, 550, 470), radius=30, fill=c)  # body
    d.rectangle((280, 470, 300, 590), fill=(70, 70, 70))  # legs
    d.rectangle((500, 470, 520, 590), fill=(70, 70, 70))
    d.rounded_rectangle((240, 440, 560, 480), radius=12, fill=(70, 70, 70))


DRAW = {
    "footwear": draw_footwear,
    "clothing": draw_clothing,
    "electronics": draw_electronics,
    "home": draw_home,
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    title_font = ImageFont.load_default(size=40)
    small_font = ImageFont.load_default(size=26)
    for product in json.loads((SEED_DIR / "products.json").read_text()):
        img = Image.new("RGB", (SIZE, SIZE), BACKGROUNDS[product["category"]])
        d = ImageDraw.Draw(img)
        DRAW[product["category"]](d, accent(product["sku"]))
        d.text((SIZE / 2, 680), product["name"], font=title_font, fill=(40, 40, 40), anchor="mm")
        d.text((SIZE / 2, 730), product["sku"], font=small_font, fill=(120, 120, 120), anchor="mm")
        img.save(OUT_DIR / f"{product['sku']}.png", optimize=True)
    print(f"Wrote {len(list(OUT_DIR.glob('*.png')))} images to {OUT_DIR}")


if __name__ == "__main__":
    main()

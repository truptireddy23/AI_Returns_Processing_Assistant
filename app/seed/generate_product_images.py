"""Generate the catalog's product images (app/frontend/public/products/<SKU>.png).

Simple, license-free illustrations — no photos, no external assets, nothing
to license. Each SKU gets its own silhouette (a hiking boot looks different
from a court shoe; a chair looks like a chair), two-tone shading for a little
depth, and a soft ground shadow. Re-run after adding or changing products:

    cd app/backend && uv run python ../seed/generate_product_images.py
"""

import hashlib
import json
from pathlib import Path
from typing import Callable

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

RGB = tuple[int, int, int]


def accent(sku: str) -> RGB:
    h = hashlib.sha256(sku.encode()).digest()
    return (60 + h[0] % 140, 60 + h[1] % 140, 60 + h[2] % 140)


def shade(c: RGB, factor: float) -> RGB:
    """`factor` < 1 darkens, > 1 lightens."""
    return (
        max(0, min(255, int(c[0] * factor))),
        max(0, min(255, int(c[1] * factor))),
        max(0, min(255, int(c[2] * factor))),
    )


def ground_shadow(d: ImageDraw.ImageDraw, bg: RGB, cx: int, cy: int, w: int, h: int) -> None:
    d.ellipse((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), fill=shade(bg, 0.92))


# --- Footwear -----------------------------------------------------------


def draw_sneaker(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 560, 460, 50)
    d.rounded_rectangle((150, 475, 650, 525), radius=20, fill=shade(c, 0.55))  # sole
    d.polygon([(170, 475), (190, 335), (330, 305), (430, 385), (630, 425), (650, 475)], fill=c)
    d.polygon([(170, 475), (190, 335), (260, 322), (300, 400), (300, 475)], fill=shade(c, 1.15))
    for x in range(260, 400, 35):  # laces
        d.line((x, 350, x + 30, 390), fill=(250, 250, 250), width=8)


def draw_court_shoe(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 555, 440, 46)
    d.rounded_rectangle((160, 490, 640, 530), radius=16, fill=shade(c, 0.6))  # cupsole
    d.polygon([(180, 490), (195, 380), (340, 330), (450, 370), (620, 430), (640, 490)], fill=c)
    d.line((340, 330, 450, 370), fill=shade(c, 0.7), width=4)  # stitched cupsole seam
    d.ellipse((290, 330, 330, 360), outline=shade(c, 0.6), width=3)  # eyelet detail


def draw_hiking_boot(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 565, 460, 50)
    # lugged outsole: a row of chunky segments
    for i, x in enumerate(range(170, 630, 46)):
        d.rounded_rectangle((x, 500, x + 38, 535), radius=6, fill=shade(c, 0.4 + 0.05 * (i % 2)))
    d.polygon([(180, 500), (195, 300), (260, 250), (420, 260), (460, 340), (610, 400), (630, 500)], fill=c)
    d.rounded_rectangle((200, 255, 400, 300), radius=18, fill=shade(c, 1.2))  # ankle collar
    for y in range(330, 440, 30):  # lace hooks
        d.ellipse((330, y, 350, y + 14), fill=(60, 60, 60))


def draw_slip_on(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 545, 440, 44)
    d.rounded_rectangle((170, 480, 630, 515), radius=18, fill=shade(c, 0.55))
    d.polygon([(190, 480), (215, 370), (380, 320), (480, 360), (610, 420), (630, 480)], fill=c)
    d.arc((380, 330, 480, 420), start=200, end=340, fill=shade(c, 0.6), width=6)  # elastic gusset


def draw_slipper(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 520, 420, 38)
    d.rounded_rectangle((190, 470, 610, 505), radius=16, fill=shade(c, 0.6))
    d.ellipse((200, 370, 600, 490), fill=c)
    d.ellipse((260, 390, 540, 480), fill=shade(c, 1.18))  # soft fuzzy opening


FOOTWEAR: dict[str, Callable] = {
    "FW-001": draw_sneaker,
    "FW-002": draw_court_shoe,
    "FW-003": draw_hiking_boot,
    "FW-004": draw_slip_on,
    "FW-005": draw_slipper,
}


# --- Clothing -------------------------------------------------------------


def _tee_shape(d: ImageDraw.ImageDraw, c: RGB, ox: int, oy: int, scale: float) -> None:
    def p(x: float, y: float) -> tuple[float, float]:
        return (ox + x * scale, oy + y * scale)

    d.polygon(
        [p(0, -80), p(200, -80), p(340, 0), p(290, 80), p(240, 50), p(240, 280), p(-40, 280), p(-40, 50), p(-90, 80), p(-140, 0)],
        fill=c,
    )
    d.ellipse((p(50, -105)[0], p(50, -105)[1], p(150, -45)[0], p(150, -45)[1]), fill=BACKGROUNDS["clothing"])


def draw_sweater(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 610, 440, 36)
    _tee_shape(d, c, 400, 330, 1.0)
    d.line((260, 580, 540, 580), fill=shade(c, 0.6), width=6)  # ribbed hem
    d.line((265, 345, 300, 400), fill=shade(c, 0.6), width=8)  # ribbed cuff, left sleeve edge
    d.line((535, 345, 500, 400), fill=shade(c, 0.6), width=8)  # ribbed cuff, right sleeve edge


def draw_rain_jacket(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 610, 440, 36)
    d.polygon(
        [(350, 260), (355, 190), (400, 155), (445, 190), (450, 260)],
        fill=shade(c, 1.15),
        outline=shade(c, 0.6),
        width=3,
    )  # hood, sitting behind the collar
    _tee_shape(d, c, 400, 340, 1.0)
    d.line((400, 220, 400, 580), fill=shade(c, 0.55), width=5)  # center zip
    for y in range(240, 580, 40):
        d.ellipse((396, y, 404, y + 8), fill=shade(c, 0.4))  # zip teeth
    d.line((270, 560, 310, 600), fill=shade(c, 0.6), width=5)  # drawstring hem
    d.line((530, 560, 490, 600), fill=shade(c, 0.6), width=5)


def draw_trousers(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 610, 400, 34)
    d.rounded_rectangle((300, 200, 500, 280), radius=20, fill=shade(c, 1.1))  # waistband
    d.polygon([(300, 260), (300, 580), (370, 580), (395, 330), (405, 330), (430, 580), (500, 580), (500, 260)], fill=c)
    d.line((400, 260, 400, 560), fill=shade(c, 0.6), width=4)  # center crease
    d.line((340, 290, 340, 560), fill=shade(c, 0.75), width=2)


def draw_tee_3pack(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 580, 460, 40)
    _tee_shape(d, shade(c, 0.75), 330, 420, 0.65)
    _tee_shape(d, shade(c, 0.9), 400, 390, 0.65)
    _tee_shape(d, c, 470, 360, 0.65)


def draw_running_shorts(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 560, 420, 34)
    d.rounded_rectangle((290, 280, 510, 350), radius=20, fill=shade(c, 1.1))  # waistband
    d.polygon([(290, 330), (290, 500), (370, 500), (400, 400), (430, 500), (510, 500), (510, 330)], fill=c)
    d.line((470, 300, 470, 490), fill=shade(c, 0.55), width=6)  # side stripe
    d.rounded_rectangle((460, 360, 500, 400), radius=6, outline=shade(c, 0.5), width=3)  # zip pocket


def draw_button_down(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 610, 440, 36)
    _tee_shape(d, c, 400, 340, 1.0)
    d.polygon([(450, 245), (400, 320), (470, 290)], fill=shade(c, 1.2))  # collar points
    d.polygon([(550, 245), (600, 320), (530, 290)], fill=shade(c, 1.2))
    for y in range(260, 560, 45):  # buttons
        d.ellipse((396, y, 404, y + 8), fill=shade(c, 0.5))


CLOTHING: dict[str, Callable] = {
    "CL-001": draw_sweater,
    "CL-002": draw_rain_jacket,
    "CL-003": draw_trousers,
    "CL-004": draw_tee_3pack,
    "CL-005": draw_running_shorts,
    "CL-006": draw_button_down,
}


# --- Electronics ------------------------------------------------------------


def draw_headphones(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 560, 420, 34)
    d.arc((260, 200, 540, 520), start=180, end=360, fill=c, width=26)  # headband
    for cx in (270, 530):
        d.ellipse((cx - 70, 400, cx + 70, 560), fill=c)
        d.ellipse((cx - 45, 425, cx + 45, 535), fill=shade(c, 0.5))


def draw_speaker(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 580, 380, 34)
    d.rounded_rectangle((260, 260, 540, 560), radius=60, fill=c)
    cx, cy = 400, 410
    for r in (110, 80, 50):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=shade(c, 0.5), width=4)
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=shade(c, 0.4))
    d.rounded_rectangle((370, 530, 430, 545), radius=6, fill=shade(c, 0.5))  # button


def draw_fitness_band(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 570, 420, 30)
    d.arc((230, 230, 570, 650), start=200, end=340, fill=shade(c, 0.6), width=46)  # strap
    d.rounded_rectangle((330, 310, 470, 430), radius=24, fill=c)  # body
    d.rounded_rectangle((350, 330, 450, 410), radius=14, fill=(25, 25, 30))  # screen
    d.rounded_rectangle((365, 345, 435, 365), radius=4, fill=shade(c, 1.3))  # screen highlight


def draw_action_camera(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 560, 360, 32)
    d.rounded_rectangle((280, 300, 520, 500), radius=30, fill=c)
    d.ellipse((345, 330, 455, 440), fill=(30, 30, 30))
    d.ellipse((365, 350, 435, 420), fill=(80, 80, 90))
    d.ellipse((385, 370, 415, 400), fill=(150, 170, 190))  # lens glint
    d.rounded_rectangle((340, 480, 460, 520), radius=10, fill=shade(c, 0.6))  # mount tab


def draw_usb_hub(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 480, 380, 26)
    d.rounded_rectangle((260, 380, 540, 460), radius=24, fill=c)
    for x in range(290, 520, 60):
        d.rounded_rectangle((x, 400, x + 36, 440), radius=6, fill=shade(c, 0.45))  # ports
    d.rounded_rectangle((260, 380, 540, 400), radius=12, fill=shade(c, 1.2))  # top sheen


ELECTRONICS: dict[str, Callable] = {
    "EL-001": draw_headphones,
    "EL-002": draw_speaker,
    "EL-003": draw_fitness_band,
    "EL-004": draw_action_camera,
    "EL-005": draw_usb_hub,
}


# --- Home -------------------------------------------------------------------


def draw_office_chair(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 610, 360, 30)
    d.rounded_rectangle((300, 180, 500, 420), radius=40, fill=c)  # backrest
    d.rounded_rectangle((280, 420, 520, 470), radius=20, fill=shade(c, 1.15))  # seat
    d.line((300, 440, 250, 460), fill=shade(c, 0.6), width=10)  # armrests
    d.line((500, 440, 550, 460), fill=shade(c, 0.6), width=10)
    d.line((400, 470, 400, 540), fill=(90, 90, 90), width=10)  # gas lift
    for angle in range(0, 360, 72):  # star base
        import math

        x2 = 400 + 110 * math.cos(math.radians(angle))
        y2 = 560 + 40 * math.sin(math.radians(angle))
        d.line((400, 560, x2, y2), fill=(90, 90, 90), width=8)
        d.ellipse((x2 - 10, y2 - 6, x2 + 10, y2 + 6), fill=(60, 60, 60))


def draw_pour_over(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 560, 420, 30)
    d.polygon([(330, 300), (470, 300), (430, 400), (370, 400)], fill=c)  # dripper cone
    d.rounded_rectangle((350, 400, 450, 520), radius=10, fill=shade(c, 1.15))  # carafe
    d.polygon([(450, 430), (490, 420), (490, 460), (450, 460)], fill=shade(c, 1.15))  # handle-ish spout
    for cx in (250, 560):  # two cups
        d.rounded_rectangle((cx - 35, 460, cx + 35, 530), radius=8, fill=shade(c, 0.85))
        d.arc((cx + 20, 475, cx + 55, 510), start=260, end=100, fill=shade(c, 0.85), width=6)


def draw_cookware(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 560, 440, 32)
    for i, (w, dy) in enumerate([(360, 0), (300, -70), (240, -130)]):
        cy = 480 + dy
        d.rounded_rectangle((400 - w / 2, cy - 30, 400 + w / 2, cy + 30), radius=16, fill=shade(c, 1.0 - 0.1 * i))
        d.line((400 - w / 2 - 30, cy, 400 - w / 2, cy), fill=(70, 70, 70), width=8)  # handle
        d.line((400 + w / 2, cy, 400 + w / 2 + 30, cy), fill=(70, 70, 70), width=8)


def draw_pillow(d: ImageDraw.ImageDraw, c: RGB, bg: RGB) -> None:
    ground_shadow(d, bg, 400, 540, 440, 34)
    d.rounded_rectangle((220, 320, 580, 500), radius=70, fill=c)
    d.line((230, 410, 570, 410), fill=shade(c, 0.85), width=4)  # seam
    for x in (260, 540):
        d.line((x, 335, x, 485), fill=shade(c, 0.85), width=3)  # corner fold lines


HOME: dict[str, Callable] = {
    "HM-001": draw_office_chair,
    "HM-002": draw_pour_over,
    "HM-003": draw_cookware,
    "HM-004": draw_pillow,
}

DRAW: dict[str, Callable] = {**FOOTWEAR, **CLOTHING, **ELECTRONICS, **HOME}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    title_font = ImageFont.load_default(size=40)
    small_font = ImageFont.load_default(size=26)
    products = json.loads((SEED_DIR / "products.json").read_text())
    for product in products:
        sku, category = product["sku"], product["category"]
        bg = BACKGROUNDS[category]
        img = Image.new("RGB", (SIZE, SIZE), bg)
        d = ImageDraw.Draw(img)
        draw = DRAW.get(sku)
        if draw is None:
            raise SystemExit(f"No illustration for {sku} — add one to generate_product_images.py")
        draw(d, accent(sku), bg)
        d.text((SIZE / 2, 680), product["name"], font=title_font, fill=(40, 40, 40), anchor="mm")
        d.text((SIZE / 2, 730), sku, font=small_font, fill=(120, 120, 120), anchor="mm")
        img.save(OUT_DIR / f"{sku}.png", optimize=True)
    print(f"Wrote {len(products)} images to {OUT_DIR}")


if __name__ == "__main__":
    main()

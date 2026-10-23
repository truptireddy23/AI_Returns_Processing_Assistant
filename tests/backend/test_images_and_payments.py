"""Upload safety and mock payments (no database needed)."""

import io
from datetime import date

import pytest
from PIL import Image

from returnguard.images import UploadRejected, dhash, hamming, process_upload
from returnguard.payments import PaymentDeclined, charge_test_card, luhn_valid

from . import images

LIMITS = {"max_pixels": 40_000_000, "max_side": 3000}


def test_metadata_is_read_then_stripped() -> None:
    raw = images.jpeg(make="Canon", model="EOS R6", gps=True)

    photo = process_upload(raw, **LIMITS)

    assert photo.metadata["has_exif"] is True
    assert photo.metadata["camera_make"] == "Canon"
    assert photo.metadata["camera_model"] == "EOS R6"
    assert photo.metadata["has_gps"] is True
    assert "gps" not in str({k: v for k, v in photo.metadata.items() if k != "has_gps"}).lower()
    stored = Image.open(io.BytesIO(photo.data))
    assert stored.format == "JPEG"
    assert len(stored.getexif()) == 0  # nothing survives re-encoding


def test_a_photo_without_camera_metadata_says_so() -> None:
    photo = process_upload(images.png(), **LIMITS)
    assert photo.metadata["has_exif"] is False
    assert "camera_make" not in photo.metadata


def test_generator_hints_in_png_text_are_recorded() -> None:
    raw = images.png(text={"parameters": "a torn sneaker, photorealistic, 8k"})
    photo = process_upload(raw, **LIMITS)
    assert photo.metadata["has_generator_hints"] is True
    assert photo.metadata["png_text_keys"] == ["parameters"]


def test_camera_rotation_is_applied() -> None:
    raw = images.jpeg(size=(80, 40), orientation=6)  # "rotate 90° clockwise"
    photo = process_upload(raw, **LIMITS)
    assert (photo.width, photo.height) == (40, 80)


def test_large_photos_are_scaled_down() -> None:
    photo = process_upload(images.jpeg(size=(4000, 3000)), max_pixels=40_000_000, max_side=1000)
    assert max(photo.width, photo.height) == 1000


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b"", "empty"),
        (b"%PDF-1.7 not an image", "readable photo"),
        (images.gif(), "JPEG, PNG, or WebP"),
        (images.jpeg()[:200], "readable photo"),  # truncated
        (images.huge_png(), "too large"),  # decompression bomb
    ],
)
def test_unacceptable_files_are_rejected(raw: bytes, message: str) -> None:
    with pytest.raises(UploadRejected, match=message):
        process_upload(raw, **LIMITS)


def test_a_file_renamed_to_jpg_is_judged_by_its_bytes() -> None:
    # The bytes are what count; filenames and Content-Type never reach this function.
    with pytest.raises(UploadRejected):
        process_upload(b"<script>alert(1)</script>", **LIMITS)


def test_perceptual_hash_spots_near_duplicates() -> None:
    base = Image.new("RGB", (200, 200), (255, 255, 255))
    for x in range(0, 200, 20):
        base.paste((0, 0, 0), (x, 0, x + 10, 200))
    slightly_brighter = base.point(lambda v: min(255, v + 10))
    different = base.rotate(90)

    assert hamming(dhash(base), dhash(slightly_brighter)) <= 4
    assert hamming(dhash(base), dhash(different)) > 10


# --- Payments ---------------------------------------------------------------


def test_luhn() -> None:
    assert luhn_valid("4242424242424242")
    assert not luhn_valid("4242424242424241")


def test_test_cards_are_accepted_and_only_last4_is_returned() -> None:
    assert (
        charge_test_card("4242 4242 4242 4242", 12, 2030, "123", today=date(2026, 10, 1)) == "4242"
    )


@pytest.mark.parametrize(
    ("number", "month", "year", "cvc", "message"),
    [
        ("4242424242424241", 12, 2030, "123", "isn't valid"),
        ("4111111111111111", 12, 2030, "123", "only accepts test cards"),  # valid, not ours
        ("4242424242424242", 9, 2026, "123", "expired"),
        ("4242424242424242", 12, 2030, "12a", "security code"),
    ],
)
def test_declines(number: str, month: int, year: int, cvc: str, message: str) -> None:
    with pytest.raises(PaymentDeclined, match=message):
        charge_test_card(number, month, year, cvc, today=date(2026, 10, 1))

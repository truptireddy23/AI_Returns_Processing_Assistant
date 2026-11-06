"""Deterministic minimization for text sent to chat and embedding providers.

Known account/order identifiers are removed before inference. Pattern matching adds
coverage for common contact details and gender cues. This is not general-purpose NER:
unrecognised third-party names and unusual addresses can remain. Photos may contain PII.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from returnguard.models import Order, User

_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
_STREET = re.compile(
    r"\b\d{1,6}\s+(?:[\w.'-]+\s+){0,5}"
    r"(?:street|st|avenue|ave|road|rd|lane|ln|drive|dr|court|ct|boulevard|blvd)\b"
    r"(?:\.?\s*(?:apt|unit|suite|#)\s*[\w-]+)?",
    re.IGNORECASE,
)
_GENDER = re.compile(
    r"\b(?:he|she|him|her|his|hers|himself|herself|mr|mrs|ms|miss|sir|madam|"
    r"male|female|man|woman|men|women|boy|girl|husband|wife|mother|father|"
    r"mom|dad|son|daughter|gentleman|lady)\b\.?",
    re.IGNORECASE,
)
_INTRODUCED_NAME = re.compile(
    r"\b(my name is|customer name[: ]+|name[: ]+)\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"
)


def identity_terms(customer: User, order: Order) -> tuple[str, ...]:
    terms = [customer.display_name, customer.email, order.shipping_name, order.billing_name]
    for name in (customer.display_name, order.shipping_name, order.billing_name):
        if name:
            terms.extend(part for part in name.split() if len(part) > 1)
    for prefix in ("shipping", "billing"):
        terms.extend(
            getattr(order, f"{prefix}_{part}") for part in ("line1", "city", "postal_code")
        )
    return tuple(t for t in terms if t)


def sanitize_text(text: str, identifiers: Iterable[str] = ()) -> str:
    text = unicodedata.normalize("NFKC", text)
    # Longest first avoids leaking the remainder of an address or full name.
    for term in sorted(set(identifiers), key=len, reverse=True):
        term = unicodedata.normalize("NFKC", term).strip()
        if term:
            text = re.sub(r"(?<!\w)" + re.escape(term) + r"(?!\w)", "[identity]", text, flags=re.I)
    text = _EMAIL.sub("[email]", text)
    text = _STREET.sub("[address]", text)
    text = _PHONE.sub("[phone]", text)
    text = _INTRODUCED_NAME.sub("[name]", text)
    return _GENDER.sub("[person]", text)

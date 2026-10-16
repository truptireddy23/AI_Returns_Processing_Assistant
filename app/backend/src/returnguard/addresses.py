"""Address fingerprints: find accounts sharing a shipping address without comparing raw text."""

import hashlib
import re

_PUNCTUATION = re.compile(r"[.,#'\"]")
_WHITESPACE = re.compile(r"\s+")


def normalise(part: str) -> str:
    return _WHITESPACE.sub(" ", _PUNCTUATION.sub("", part.lower())).strip()


def fingerprint(line1: str, city: str, postal_code: str) -> str:
    key = "|".join(normalise(p) for p in (line1, city, postal_code))
    return hashlib.sha256(key.encode()).hexdigest()

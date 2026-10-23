"""Password hashing and session tokens."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Verified against when the email is unknown, so a failed login takes the same
# time whether or not the account exists.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    """A URL-safe random token with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_match(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


MIN_PASSWORD_LENGTH = 10
# The most common passwords that pass the length rule (a short, offline list;
# production would check a breach corpus such as Have I Been Pwned's k-anonymity API).
_COMMON_PASSWORDS = {
    "1234567890",
    "12345678910",
    "0123456789",
    "qwertyuiop",
    "password12",
    "password123",
    "password1234",
    "iloveyou12",
    "123456789a",
    "abcdefghij",
    "qwerty1234",
    "1q2w3e4r5t",
    "letmein123",
    "welcome123",
    "football12",
    "monkey1234",
    "dragon1234",
    "1111111111",
    "aaaaaaaaaa",
    "passw0rd123",
}


def password_problem(password: str, email: str) -> str | None:
    """Why `password` is unacceptable, in words for the user, or None if it's fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if password.lower() in _COMMON_PASSWORDS:
        return "That password is too common. Please choose another."
    if password.lower() == email.lower() or password.lower() == email.split("@")[0].lower():
        return "Your password can't be your email address."
    if len(set(password)) < 4:
        return "Use a mix of characters, not one repeated."
    return None

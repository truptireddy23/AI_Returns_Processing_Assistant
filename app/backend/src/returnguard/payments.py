"""Mock payments. No money moves and no card data is kept.

Only well-known *test* card numbers are accepted, so nobody can type a real card
into the demo shop. Only the last four digits are stored.
"""

from datetime import date

# Published test numbers (Visa, Visa debit, Mastercard, Amex).
TEST_CARDS = {
    "4242424242424242",
    "4000056655665556",
    "5555555555554444",
    "378282246310005",
}


class PaymentDeclined(ValueError):
    """The card can't be used. The message is safe to show the user."""


def luhn_valid(number: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def charge_test_card(
    number: str, exp_month: int, exp_year: int, cvc: str, *, today: date | None = None
) -> str:
    """Validate a test card and "charge" it. Returns the last four digits."""
    digits = "".join(ch for ch in number if not ch.isspace() and ch != "-")
    if not digits.isdigit() or not 13 <= len(digits) <= 19 or not luhn_valid(digits):
        raise PaymentDeclined("That card number isn't valid.")
    if digits not in TEST_CARDS:
        raise PaymentDeclined("This demo shop only accepts test cards, e.g. 4242 4242 4242 4242.")
    today = today or date.today()
    if (exp_year, exp_month) < (today.year, today.month):
        raise PaymentDeclined("That card has expired.")
    if not cvc.isdigit() or len(cvc) not in (3, 4):
        raise PaymentDeclined("The security code should be 3 or 4 digits.")
    return digits[-4:]

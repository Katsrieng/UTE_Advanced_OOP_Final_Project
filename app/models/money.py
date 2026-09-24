"""Shared decimal amount validation."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal("100000000"):
            raise ValueError()
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid non-negative amount within range.")

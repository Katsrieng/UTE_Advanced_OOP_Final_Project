"""Sale record returned by its repository."""

from dataclasses import dataclass
from decimal import Decimal

from .money import money


@dataclass
class Sale:
    id: int
    code: str
    user_id: int
    customer_id: int
    vehicle_id: int
    date: str
    price: Decimal
    discount: Decimal
    total: Decimal
    status: str
    created: str
    updated: str
    staff: str


@dataclass(frozen=True)
class SaleAmounts:
    price: Decimal
    discount: Decimal

    @classmethod
    def calculate(cls, price, discount):
        result = cls(money(price), money(discount))
        if result.discount > result.price:
            raise ValueError("Discount must be between zero and the selling price.")
        return result

    @property
    def total(self):
        return self.price - self.discount

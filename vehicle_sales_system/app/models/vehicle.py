"""Vehicle record returned by its repository."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Vehicle:
    id: int
    code: str
    vin: str | None
    plate: str | None
    brand: str
    model: str
    year: int
    color: str
    purchase_price: Decimal
    price: Decimal
    status: str
    image: str
    mileage: int
    fuel: str
    created: str
    updated: str

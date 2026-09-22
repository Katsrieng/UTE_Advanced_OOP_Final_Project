"""Small domain objects; independent of Flask and the persistence adapter."""
from dataclasses import dataclass, asdict


@dataclass
class Vehicle:
    id: int
    code: str
    brand: str
    model: str
    year: int
    color: str
    vin: str
    plate: str
    purchase_price: float
    price: float
    status: str = 'AVAILABLE'
    mileage: int = 0
    fuel: str = 'Hybrid'
    created: str = '2026-09-01'
    image: str = 'sedan.svg'

    def to_dict(self):
        return asdict(self)

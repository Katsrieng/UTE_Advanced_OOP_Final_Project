"""Invoice record returned by its repository."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Invoice:
    id: int
    code: str
    sale_id: int
    date: str
    total: Decimal
    created: str

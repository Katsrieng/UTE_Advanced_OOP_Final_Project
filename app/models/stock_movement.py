"""StockMovement record returned by its repository."""

from dataclasses import dataclass


@dataclass
class StockMovement:
    id: int
    vehicle_id: int
    user_id: int
    movement: str
    date: str
    reason: str
    quantity: int
    created: str
    staff: str

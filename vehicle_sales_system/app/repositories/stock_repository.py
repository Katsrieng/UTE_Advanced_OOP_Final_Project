"""Persistence operations for stockmovement records."""

from app.models.stock_movement import StockMovement

from .base import EntityRepository


class StockMovementRepository(EntityRepository):
    model = StockMovement
    table = "stock_movements"
    pk = "movement_id"
    fields = dict(
        vehicle_id="vehicle_id",
        user_id="user_id",
        movement="movement_type",
        date="movement_date",
        reason="reason",
        quantity="quantity",
    )

    @property
    def projection(self):
        return (
            super().projection
            + ", (SELECT full_name FROM users WHERE user_id=t.user_id) AS staff"
        )

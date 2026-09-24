"""Persistence operations for sale records."""

from app.models.sale import Sale

from .base import EntityRepository


class SaleRepository(EntityRepository):
    model = Sale
    table = "sales"
    pk = "sale_id"
    fields = dict(
        code="sale_code",
        user_id="user_id",
        customer_id="customer_id",
        vehicle_id="vehicle_id",
        date="sale_date",
        price="sale_price",
        discount="discount_amount",
        total="total_amount",
        status="status",
    )

    @property
    def projection(self):
        return (
            super().projection
            + ", (SELECT full_name FROM users WHERE user_id=t.user_id) AS staff"
        )

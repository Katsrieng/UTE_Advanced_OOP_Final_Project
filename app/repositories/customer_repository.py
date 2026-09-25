"""Persistence operations for customer records."""

from app.models.customer import Customer

from .base import EntityRepository


class CustomerRepository(EntityRepository):
    model = Customer
    table = "customers"
    pk = "customer_id"
    active = True
    fields = dict(
        code="customer_code",
        name="full_name",
        phone="phone",
        email="email",
        address="address",
    )

    @property
    def projection(self):
        return (
            super().projection
            + ",(SELECT COUNT(*) FROM sales s WHERE s.customer_id=t.customer_id AND s.status='COMPLETED') AS purchases"
        )

    def has_history(self, item_id):
        return bool(
            self.db.query(
                "SELECT EXISTS(SELECT 1 FROM sales WHERE customer_id=%s) "
                "OR EXISTS(SELECT 1 FROM invoices i JOIN sales s ON s.sale_id=i.sale_id "
                "WHERE s.customer_id=%s) AS has_history",
                (item_id, item_id),
            )[0]["has_history"]
        )

    def delete(self, item_id):
        self.db.execute("DELETE FROM customers WHERE customer_id=%s", (item_id,))

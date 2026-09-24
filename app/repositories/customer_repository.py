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

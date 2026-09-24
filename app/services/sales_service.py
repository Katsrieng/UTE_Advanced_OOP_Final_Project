"""A sale, stock transition and invoice commit together or not at all."""

from datetime import date
from uuid import uuid4

from app.models.sale import SaleAmounts


class SalesService:
    def __init__(self, repository):
        self.repository = repository

    def complete(self, customer_id, vehicle_id, discount, user_id):
        repo = self.repository
        with repo.transaction():
            user = repo.get("users", user_id, lock=True)
            if not user or user["status"] != "ACTIVE":
                raise ValueError("An active user is required.")
            customer = repo.get("customers", customer_id, lock=True)
            if not customer or customer["status"] != "ACTIVE":
                raise ValueError("Select an active customer.")
            vehicle = repo.get("vehicles", vehicle_id, lock=True)
            if not vehicle or vehicle["status"] != "AVAILABLE":
                raise ValueError(
                    "This vehicle is no longer available. Select another vehicle."
                )
            amounts = SaleAmounts.calculate(vehicle["price"], discount)
            # Temporary unique code lets MySQL allocate an ID without count-based races.
            sale = repo.save(
                "sales",
                dict(
                    code="NEW-" + uuid4().hex,
                    user_id=user_id,
                    customer_id=customer_id,
                    vehicle_id=vehicle_id,
                    date=date.today(),
                    price=amounts.price,
                    discount=amounts.discount,
                    total=amounts.total,
                    status="COMPLETED",
                ),
            )
            sale = repo.save("sales", {"code": f"SAL-{sale['id']:06}"}, sale["id"])
            repo.save("vehicles", {"status": "SOLD"}, vehicle_id)
            repo.save(
                "inventory",
                dict(
                    vehicle_id=vehicle_id,
                    user_id=user_id,
                    date=date.today(),
                    movement="STOCK_OUT",
                    quantity=-1,
                    reason="Sale " + sale["code"],
                ),
            )
            invoice = repo.save(
                "invoices",
                dict(
                    code=f"INV-{sale['id']:06}",
                    sale_id=sale["id"],
                    date=date.today(),
                    total=amounts.total,
                ),
            )
        return sale, invoice

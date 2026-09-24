"""Atomic physical-vehicle inventory transitions."""

from datetime import date


class InventoryService:
    def __init__(self, repo):
        self.repo = repo

    def record(self, vehicle_id, movement, reason, user_id):
        if (
            movement not in ("STOCK_IN", "STOCK_OUT", "ADJUSTMENT")
            or not reason.strip()
        ):
            raise ValueError("Choose a valid movement and enter a reason.")
        with self.repo.transaction():
            user = self.repo.get("users", user_id, lock=True)
            if not user or user["status"] != "ACTIVE":
                raise ValueError("An active user is required.")
            vehicle = self.repo.get("vehicles", vehicle_id, lock=True)
            if not vehicle or vehicle["status"] == "SOLD":
                raise ValueError(
                    "Sold vehicles cannot be changed through stock adjustments."
                )
            if movement == "STOCK_IN" and vehicle["status"] != "INACTIVE":
                raise ValueError(
                    "Stock in requires an inactive vehicle; it is already in stock."
                )
            if movement == "STOCK_OUT" and vehicle["status"] == "INACTIVE":
                raise ValueError("This vehicle is already out of stock.")
            if movement != "ADJUSTMENT":
                self.repo.save(
                    "vehicles",
                    {"status": "AVAILABLE" if movement == "STOCK_IN" else "INACTIVE"},
                    vehicle_id,
                )
            return self.repo.save(
                "inventory",
                dict(
                    vehicle_id=vehicle_id,
                    user_id=user_id,
                    movement=movement,
                    reason=reason,
                    date=date.today(),
                    quantity={"STOCK_IN": 1, "STOCK_OUT": -1, "ADJUSTMENT": 0}[
                        movement
                    ],
                ),
            )

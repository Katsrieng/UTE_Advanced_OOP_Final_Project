"""Persistence operations for vehicle records."""

from app.models.vehicle import Vehicle

from .base import EntityRepository


class VehicleRepository(EntityRepository):
    model = Vehicle
    table = "vehicles"
    pk = "vehicle_id"
    fields = dict(
        code="vehicle_code",
        vin="vin",
        plate="plate_number",
        brand="brand",
        model="model",
        year="vehicle_year",
        color="color",
        purchase_price="purchase_price",
        price="selling_price",
        status="status",
        image="image_path",
        mileage="mileage",
        fuel="fuel",
    )

    def save(self, values, item_id=None):
        values = dict(values)
        if "plate" in values:
            plate = (values["plate"] or "").strip()
            values["plate"] = None if not plate or plate.casefold() == "none" else plate
        return super().save(values, item_id)

    def references_image(self, image):
        return bool(
            self.db.query(
                "SELECT vehicle_id FROM vehicles WHERE image_path=%s LIMIT 1", (image,)
            )
        )

    def has_history(self, item_id):
        return bool(
            self.db.query(
                "SELECT EXISTS(SELECT 1 FROM sales WHERE vehicle_id=%s) "
                "OR EXISTS(SELECT 1 FROM stock_movements WHERE vehicle_id=%s) "
                "OR EXISTS(SELECT 1 FROM invoices i JOIN sales s ON s.sale_id=i.sale_id "
                "WHERE s.vehicle_id=%s) AS has_history",
                (item_id, item_id, item_id),
            )[0]["has_history"]
        )

    def delete(self, item_id):
        self.db.execute("DELETE FROM vehicles WHERE vehicle_id=%s", (item_id,))

    def filter_options(self):
        return self.db.query(
            "SELECT DISTINCT brand,vehicle_year FROM vehicles ORDER BY brand,vehicle_year DESC"
        )

    def featured(self):
        return next(
            iter(
                self.select(
                    "t.status='AVAILABLE'", suffix="ORDER BY t.vehicle_id DESC LIMIT 1"
                )
            ),
            None,
        )

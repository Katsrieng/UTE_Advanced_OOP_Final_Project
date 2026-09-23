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

    def references_image(self, image):
        return bool(
            self.db.query(
                "SELECT vehicle_id FROM vehicles WHERE image_path=%s LIMIT 1", (image,)
            )
        )

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

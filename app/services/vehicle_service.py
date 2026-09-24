"""Vehicle form rules and photo-aware saving."""

from app.database import PersistenceError


class VehicleService:
    def __init__(self, photo_service):
        self.photo_service = photo_service

    @staticmethod
    def validate(values):
        if len(values["vin"]) != 17:
            return {"vin": "Enter a 17-character VIN."}
        return {}

    def save(self, values, item_id=None, upload=None):
        values = dict(values)
        if not item_id:
            values.update(mileage=0, fuel="Not specified")
        return self.photo_service.save_vehicle(values, item_id, upload)

    @staticmethod
    def is_admin(user):
        return bool(
            user and user["status"] == "ACTIVE" and "Admin" in user["role"].split(", ")
        )

    def delete(self, item_id, actor_id, confirmed=False):
        repository = self.photo_service.repository
        history_message = "This vehicle has transaction history. Please deactivate the vehicle instead."
        try:
            with repository.transaction():
                # Use the same role/user lock order as account access changes.
                repository.role_repository.get_by_name("Admin", lock=True)
                actor = repository.get("users", actor_id, lock=True)
                if not self.is_admin(actor):
                    raise PermissionError(
                        "Only an active Admin can permanently delete vehicles."
                    )
                if not confirmed:
                    raise ValueError("Please confirm permanent deletion.")
                vehicle = repository.get("vehicles", item_id, lock=True)
                if not vehicle:
                    raise LookupError("Vehicle not found.")
                if repository.vehicles.has_history(item_id):
                    raise ValueError(history_message)
                repository.vehicles.delete(item_id)
        except PersistenceError as exc:
            raise ValueError(
                "The vehicle could not be deleted. If it has transaction history, please deactivate it instead."
            ) from exc
        self.photo_service.remove_unreferenced(vehicle.get("image"))

"""Vehicle form rules and photo-aware saving."""


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

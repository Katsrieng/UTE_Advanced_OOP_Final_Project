"""Customer validation and persistence."""


class CustomerService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def validate(values):
        if "@" not in values["email"] or "." not in values["email"].split("@")[-1]:
            return {"email": "Enter a valid email address."}
        return {}

    def save(self, values, item_id=None):
        with self.repository.transaction():
            return self.repository.save("customers", values, item_id)

"""Customer validation and persistence."""

from app.database import PersistenceError


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

    @staticmethod
    def is_admin(user):
        return bool(
            user and user["status"] == "ACTIVE" and "Admin" in user["role"].split(", ")
        )

    def delete(self, item_id, actor_id, confirmed=False):
        repository = self.repository
        history_message = "This customer has transaction history. Please deactivate the customer instead."
        try:
            with repository.transaction():
                # Use the same role/user lock order as account access changes.
                repository.role_repository.get_by_name("Admin", lock=True)
                actor = repository.get("users", actor_id, lock=True)
                if not self.is_admin(actor):
                    raise PermissionError(
                        "Only an active Admin can permanently delete customers."
                    )
                if not confirmed:
                    raise ValueError("Please confirm permanent deletion.")
                customer = repository.get("customers", item_id, lock=True)
                if not customer:
                    raise LookupError("Customer not found.")
                if repository.entities["customers"].has_history(item_id):
                    raise ValueError(history_message)
                repository.entities["customers"].delete(item_id)
        except PersistenceError as exc:
            raise ValueError(
                "The customer could not be deleted. If it has transaction history, please deactivate it instead."
            ) from exc

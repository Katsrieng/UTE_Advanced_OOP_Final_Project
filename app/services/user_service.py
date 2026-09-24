"""User operations."""

from werkzeug.security import generate_password_hash


class UserService:
    def __init__(self, repo):
        self.repo = repo

    def save(self, values, item_id=None, actor_id=None):
        values = dict(values)
        password = values.pop("password", "")
        if (not item_id or password) and not 10 <= len(password) <= 250:
            raise ValueError("Use a password of 10 to 250 characters.")
        if (
            "@" not in values.get("email", "")
            or "." not in values["email"].split("@")[-1]
        ):
            raise ValueError("Enter a valid email address.")
        with self.repo.transaction():
            # Serialize access edits on the Admin role before locking individual users.
            admin = self.repo.role_repository.get_by_name("Admin", lock=True)
            role = self.repo.role_repository.get_by_name(values["role"])
            if not role or not role["is_active"]:
                raise ValueError("Choose an active role.")
            old = self.repo.get("users", item_id, lock=True) if item_id else None
            if item_id and not old:
                raise ValueError("User not found.")
            if old:
                role_ids = self.repo.users.role_ids(item_id)
                existing = {r["role_id"] for r in role_ids}
                changing = existing != {role["role_id"]} or values["status"] != "ACTIVE"
                if item_id == actor_id and changing:
                    raise ValueError(
                        "Use another administrator account to change your own access."
                    )
                if admin["role_id"] in existing and changing:
                    count = self.repo.users.active_role_count(admin["role_id"])
                    if count <= 1:
                        raise ValueError("Keep at least one active administrator.")
                self.repo.save("users", values, item_id)
                if password:
                    self.repo.users.set_password(
                        item_id, generate_password_hash(password)
                    )
            else:
                item_id = self.repo.users.create(
                    values, generate_password_hash(password)
                )
            self.repo.users.assign_role(item_id, role["role_id"])
            return self.repo.get("users", item_id)

    def permissions(self, role_name, names):
        with self.repo.transaction():
            role = self.repo.role_repository.get_by_name(role_name, lock=True)
            if not role or not role["is_active"]:
                raise ValueError("Role not found.")
            if role_name == "Admin":
                raise ValueError("Administrator permissions are protected.")
            allowed = {
                p
                for group in self.repo.permission_repository.groups().values()
                for p in group
            }
            if not set(names) <= allowed:
                raise ValueError("Choose valid permissions.")
            self.repo.role_repository.update_permissions(role["role_id"], set(names))

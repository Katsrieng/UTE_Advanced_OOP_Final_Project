"""Auth operations."""

from werkzeug.security import check_password_hash


class AuthService:
    def __init__(self, repo):
        self.repo = repo

    def authenticate(self, username, password):
        row = self.repo.users.credentials(username)
        if (
            row
            and row["is_active"]
            and check_password_hash(row["password_hash"], password)
        ):
            return self.repo.get("users", row["user_id"])
        return None

"""Persistence operations for user records."""

from app.models.user import User

from .base import EntityRepository


class UserRepository(EntityRepository):
    model = User
    table = "users"
    pk = "user_id"
    active = True
    fields = dict(name="full_name", username="username", email="email")

    @property
    def projection(self):
        return (
            super().projection
            + ",COALESCE((SELECT GROUP_CONCAT(r.role_name ORDER BY r.role_id SEPARATOR ', ') FROM user_roles ur JOIN roles r ON r.role_id=ur.role_id AND r.is_active=1 WHERE ur.user_id=t.user_id),'') AS role"
        )
    
    def credentials(self, username):
        rows = self.db.query(
            "SELECT user_id,password_hash,is_active FROM users WHERE username=%s",
            (username,),
        )
        return rows[0] if rows else None

    def permissions(self, user_id):
        return {
            row["permission_name"]
            for row in self.db.query(
                "SELECT DISTINCT p.permission_name FROM users u JOIN user_roles ur ON ur.user_id=u.user_id JOIN roles r ON r.role_id=ur.role_id JOIN role_permissions rp ON rp.role_id=r.role_id JOIN permissions p ON p.permission_id=rp.permission_id WHERE u.user_id=%s AND u.is_active=1 AND r.is_active=1 AND p.is_active=1",
                (user_id,),
            )
        }

    def set_password(self, user_id, password_hash):
        self.db.execute(
            "UPDATE users SET password_hash=%s WHERE user_id=%s",
            (password_hash, user_id),
        )

    def create(self, values, password_hash):
        return self.db.execute(
            "INSERT INTO users (username,full_name,email,password_hash,is_active) VALUES (%s,%s,%s,%s,%s)",
            (
                values["username"],
                values["name"],
                values["email"],
                password_hash,
                values["status"] == "ACTIVE",
            ),
        )

    def assign_role(self, user_id, role_id):
        self.db.execute("DELETE FROM user_roles WHERE user_id=%s", (user_id,))
        self.db.execute(
            "INSERT INTO user_roles (user_id,role_id) VALUES (%s,%s)",
            (user_id, role_id),
        )

    def role_ids(self, user_id):
        return self.db.query(
            "SELECT role_id FROM user_roles WHERE user_id=%s", (user_id,)
        )

    def active_role_count(self, role_id):
        return self.db.query(
            "SELECT COUNT(*) AS n FROM users u JOIN user_roles ur ON ur.user_id=u.user_id WHERE u.is_active=1 AND ur.role_id=%s",
            (role_id,),
        )[0]["n"]

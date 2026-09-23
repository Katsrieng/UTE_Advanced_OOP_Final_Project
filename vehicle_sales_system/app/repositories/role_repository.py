"""Persistence operations for role records."""

from dataclasses import asdict

from app.models.role import Role


class RoleRepository:
    def __init__(self, db):
        self.db = db

    def all(self):
        result = {
            r["role_name"]: []
            for r in self.db.query(
                "SELECT role_name FROM roles WHERE is_active=1 ORDER BY role_id"
            )
        }
        for row in self.db.query(
            "SELECT r.role_name,p.permission_name FROM roles r JOIN role_permissions rp ON rp.role_id=r.role_id JOIN permissions p ON p.permission_id=rp.permission_id WHERE r.is_active=1 AND p.is_active=1"
        ):
            result[row["role_name"]].append(row["permission_name"])
        return result

    def get_by_name(self, name, lock=False):
        rows = self.db.query(
            "SELECT role_id,role_name,is_active FROM roles WHERE role_name=%s"
            + (" FOR UPDATE" if lock else ""),
            (name,),
        )
        return asdict(Role(**rows[0])) if rows else None

    def update_permissions(self, role_id, permissions):
        self.db.execute("DELETE FROM role_permissions WHERE role_id=%s", (role_id,))
        for name in permissions:
            self.db.execute(
                "INSERT INTO role_permissions (role_id,permission_id) SELECT %s,permission_id FROM permissions WHERE permission_name=%s AND is_active=1",
                (role_id, name),
            )

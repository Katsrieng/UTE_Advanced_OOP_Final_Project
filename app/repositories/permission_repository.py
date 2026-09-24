"""Persistence operations for permission records."""

from app.models.permission import Permission


class PermissionRepository:
    def __init__(self, db):
        self.db = db

    def groups(self):
        groups = {}
        for row in self.db.query(
            "SELECT permission_name,module FROM permissions WHERE is_active=1 ORDER BY permission_id"
        ):
            permission = Permission(**row)
            groups.setdefault(permission.module.title(), []).append(
                permission.permission_name
            )
        return groups

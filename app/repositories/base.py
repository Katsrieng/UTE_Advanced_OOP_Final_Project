"""Persistence operations for entity records."""

from dataclasses import asdict
from datetime import date, datetime


class EntityRepository:
    table = ""
    pk = ""
    fields = {}
    active = False
    model = None

    def __init__(self, db):
        self.db = db

    @property
    def projection(self):
        parts = [f"t.{self.pk} AS id"] + [
            f"t.{column} AS `{key}`" for key, column in self.fields.items()
        ]
        if self.active:
            parts.append(
                "CASE WHEN t.is_active THEN 'ACTIVE' ELSE 'INACTIVE' END AS status"
            )
        parts.append("t.created_at AS created")
        if self.table not in ("stock_movements", "invoices"):
            parts.append("t.updated_at AS updated")
        return ",".join(parts)

    def map(self, row):
        if row is None:
            return None
        values = {
            key: (
                value.isoformat()[:10] if isinstance(value, (date, datetime)) else value
            )
            for key, value in row.items()
        }

        return asdict(self.model(**values)) if self.model else values

    def select(self, where="", params=(), suffix=""):
        sql = f"SELECT {self.projection} FROM {self.table} t"
        if where:
            sql += " WHERE " + where
        return [self.map(row) for row in self.db.query(sql + " " + suffix, params)]

    def get(self, item_id, lock=False):
        rows = self.select(f"t.{self.pk}=%s", (item_id,), "FOR UPDATE" if lock else "")
        return rows[0] if rows else None

    def save(self, values, item_id=None):
        data = {
            column: values[key] for key, column in self.fields.items() if key in values
        }
        if self.active and "status" in values:
            data["is_active"] = values["status"] == "ACTIVE"
        for optional in ("vin", "plate_number", "email"):
            if optional in data and data[optional] == "":
                data[optional] = None
        if not data:
            return self.get(item_id)
        if item_id:
            self.db.execute(
                f"UPDATE {self.table} SET "
                + ",".join(f"{k}=%s" for k in data)
                + f" WHERE {self.pk}=%s",
                tuple(data.values()) + (item_id,),
            )
        else:
            item_id = self.db.execute(
                f"INSERT INTO {self.table} ("
                + ",".join(data)
                + ") VALUES ("
                + ",".join(["%s"] * len(data))
                + ")",
                tuple(data.values()),
            )
        return self.get(item_id)

    def exists(self, key, value, exclude=None):
        if key not in self.fields:
            return False
        rows = self.db.query(
            f"SELECT {self.pk} FROM {self.table} WHERE {self.fields[key]}=%s AND (%s IS NULL OR {self.pk}<>%s) LIMIT 1",
            (value, exclude, exclude),
        )
        return bool(rows)

"""Application repository collection; SQL queries retain existing template keys."""

import math
from datetime import date

from app.database import Database
from app.repositories import (
    CustomerRepository,
    InvoiceRepository,
    PermissionRepository,
    RoleRepository,
    SaleRepository,
    StockMovementRepository,
    UserRepository,
    VehicleRepository,
)
from app.repositories.report_repository import ReportRepository


class MySQLRepository:
    def __init__(self, config):
        self.db = Database(config)
        self.reports = ReportRepository(self)
        self.entities = {
            "vehicles": VehicleRepository(self.db),
            "customers": CustomerRepository(self.db),
            "users": UserRepository(self.db),
            "sales": SaleRepository(self.db),
            "invoices": InvoiceRepository(self.db),
            "inventory": StockMovementRepository(self.db),
        }
        self.users = self.entities["users"]
        self.vehicles = self.entities["vehicles"]
        self.role_repository = RoleRepository(self.db)
        self.permission_repository = PermissionRepository(self.db)

    @property
    def roles(self):
        return self.role_repository.all()

    def transaction(self):
        return self.db.transaction()

    def all(self, resource):
        return self.entities[resource].select(
            suffix="ORDER BY t." + self.entities[resource].pk
        )

    def get(self, resource, item_id, lock=False):
        return self.entities[resource].get(item_id, lock)

    def save(self, resource, values, item_id=None):
        return self.entities[resource].save(values, item_id)

    def exists(self, resource, key, value, exclude=None):
        return self.entities[resource].exists(key, value, exclude)

    def image_referenced(self, image):
        return self.vehicles.references_image(image)

    def enrich(self, resource, rows):
        for row in rows:
            if resource in ("sales", "inventory"):
                row["vehicle"] = self.get("vehicles", row["vehicle_id"])
            if resource == "sales":
                row["customer"] = self.get("customers", row["customer_id"])
            if resource == "invoices":
                sale = self.get("sales", row["sale_id"])
                row.update(
                    customer=self.get("customers", sale["customer_id"]),
                    vehicle=self.get("vehicles", sale["vehicle_id"]),
                )
        return rows

    def detail(self, resource, item_id):
        row = self.get(resource, item_id)
        return self.enrich(resource, [row])[0] if row else None

    def history(self, resource, key, item_id):
        entity = self.entities[resource]
        if key not in entity.fields:
            raise ValueError("Invalid history filter")
        return self.enrich(
            resource,
            entity.select(
                "t." + entity.fields[key] + "=%s",
                (item_id,),
                "ORDER BY t." + entity.pk + " DESC",
            ),
        )

    def eligible(self, resource):
        entity = self.entities[resource]
        clause = "t.status='AVAILABLE'" if resource == "vehicles" else "t.is_active=1"
        return entity.select(clause, suffix="ORDER BY t." + entity.pk)

    def page(self, resource, args):
        entity = self.entities[resource]
        clauses = []
        params = []
        for key in ("status", "brand", "year", "movement"):
            value = args.get(key)
            if value:
                if key == "status" and entity.active:
                    clauses.append(
                        "CASE WHEN t.is_active THEN 'ACTIVE' ELSE 'INACTIVE' END=%s"
                    )
                    params.append(value)
                elif key in entity.fields:
                    clauses.append("t." + entity.fields[key] + "=%s")
                    params.append(value)
        date_column = entity.fields.get("date", "created_at")
        for key, op in (("from", ">="), ("to", "<=")):
            if args.get(key):
                try:
                    date.fromisoformat(args[key])
                except ValueError:
                    clauses.append("1=0")
                    continue
                clauses.append(f"DATE(t.{date_column}){op}%s")
                params.append(args[key])
        query = args.get("q", "").strip()
        if query:
            columns = [
                "CAST(t." + c + " AS CHAR)"
                for k, c in entity.fields.items()
                if k not in ("image",)
            ]
            if resource in ("sales", "inventory"):
                columns.append(
                    "(SELECT CONCAT_WS(' ',vehicle_code,brand,model,vin) FROM vehicles WHERE vehicle_id=t.vehicle_id)"
                )
                columns.append("(SELECT full_name FROM users WHERE user_id=t.user_id)")
            if resource == "sales":
                columns.append(
                    "(SELECT full_name FROM customers WHERE customer_id=t.customer_id)"
                )
            if resource == "invoices":
                columns.append(
                    "(SELECT CONCAT_WS(' ',c.full_name,v.vehicle_code,v.brand,v.model) FROM sales s JOIN customers c ON c.customer_id=s.customer_id JOIN vehicles v ON v.vehicle_id=s.vehicle_id WHERE s.sale_id=t.sale_id)"
                )
            clauses.append("CONCAT_WS(' '," + ",".join(columns) + ") LIKE %s")
            params.append("%" + query + "%")
        where = " AND ".join(clauses)
        count = self.db.query(
            f"SELECT COUNT(*) AS total FROM {entity.table} t"
            + (" WHERE " + where if where else ""),
            tuple(params),
        )[0]["total"]
        pages = max(1, math.ceil(count / 8))
        try:
            page = min(max(int(args.get("page", 1)), 1), pages)
        except ValueError:
            page = 1
        rows = entity.select(
            where,
            tuple(params)
            + (
                8,
                (page - 1) * 8,
            ),
            f"ORDER BY t.{date_column} DESC,t.{entity.pk} DESC LIMIT %s OFFSET %s",
        )
        return self.enrich(resource, rows), count, page, pages

    def analytics(self, start=None, end=None):
        return self.reports.analytics(start, end)

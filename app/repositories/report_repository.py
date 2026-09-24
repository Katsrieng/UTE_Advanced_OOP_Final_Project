"""Dashboard and report aggregation queries."""

from datetime import date
from decimal import Decimal


class ReportRepository:
    def __init__(self, repository):
        self.repository = repository
        self.db = repository.db

    def analytics(self, start=None, end=None):
        conditions = ["status='COMPLETED'"]
        params = []
        for value, op in ((start, ">="), (end, "<=")):
            if value:
                conditions.append("sale_date" + op + "%s")
                params.append(value)
        where = " AND ".join(conditions)
        totals = self.db.query(
            "SELECT COUNT(*) AS count,COALESCE(SUM(total_amount),0) AS revenue FROM sales WHERE "
            + where,
            tuple(params),
        )[0]
        counts = dict.fromkeys(("AVAILABLE", "RESERVED", "SOLD", "INACTIVE"), 0)
        for row in self.db.query(
            "SELECT status,COUNT(*) AS count FROM vehicles GROUP BY status"
        ):
            counts[row["status"]] = row["count"]
        grouped = {
            row["month"]: row["amount"]
            for row in self.db.query(
                "SELECT DATE_FORMAT(sale_date,'%Y-%m') AS month,SUM(total_amount) AS amount FROM sales WHERE "
                + where
                + " GROUP BY month",
                tuple(params),
            )
        }
        chart = []
        today = date.today()
        for offset in range(5, -1, -1):
            index = today.year * 12 + today.month - 1 - offset
            month = date(index // 12, index % 12 + 1, 1)
            chart.append(
                dict(
                    label=month.strftime("%b"),
                    value=str(grouped.get(month.strftime("%Y-%m"), Decimal("0.00"))),
                )
            )
        recent = self.repository.entities["sales"].select(
            " AND ".join(
                "t." + c if c.startswith(("status", "sale_date")) else c
                for c in conditions
            ),
            tuple(params),
            "ORDER BY t.sale_date DESC,t.sale_id DESC LIMIT 5",
        )
        mwhere = []
        mparams = []
        for value, op in ((start, ">="), (end, "<=")):
            if value:
                mwhere.append("movement_date" + op + "%s")
                mparams.append(value)
        movement_counts = dict.fromkeys(("STOCK_IN", "STOCK_OUT", "ADJUSTMENT"), 0)
        for row in self.db.query(
            "SELECT movement_type,COUNT(*) AS count FROM stock_movements"
            + (" WHERE " + " AND ".join(mwhere) if mwhere else "")
            + " GROUP BY movement_type",
            tuple(mparams),
        ):
            movement_counts[row["movement_type"]] = row["count"]
        return dict(
            counts=counts,
            total_vehicles=sum(counts.values()),
            revenue=totals["revenue"],
            sales_count=totals["count"],
            chart=chart,
            recent_sales=self.repository.enrich("sales", recent),
            movement_counts=movement_counts,
            movement_count=sum(movement_counts.values()),
        )

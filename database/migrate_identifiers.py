"""Preview or transactionally replace legacy sample identifiers without reseeding."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mysql.connector
from database.identifiers import fictional_vin

from database.common import ROOT, settings

TABLE_KEYS = {
    "vehicles": "vehicle_id",
    "customers": "customer_id",
    "sales": "sale_id",
    "invoices": "invoice_id",
    "stock_movements": "movement_id",
}
UNIQUE_FIELDS = {
    "vehicles": ("vin", "plate_number", "vehicle_code"),
    "sales": ("sale_code",),
    "invoices": ("invoice_number",),
}


def build_plan(records):
    """Match known old formats only; unrelated fields and record IDs stay intact."""
    changes = []

    def change(table, row, field, value):
        if row[field] != value:
            changes.append(
                dict(
                    table=table,
                    id=row[TABLE_KEYS[table]],
                    field=field,
                    old=row[field],
                    new=value,
                )
            )

    for row in records["vehicles"]:
        vin = row["vin"] or ""
        match = re.fullmatch(r"AVDEMO(\d{11})", vin)
        if match:
            change("vehicles", row, "vin", fictional_vin(int(match[1])))
        elif re.fullmatch(r"AVVERIFY[A-Z0-9]{9}", vin):
            change("vehicles", row, "vin", fictional_vin(1000000 + row["vehicle_id"]))
        plate = re.fullmatch(r"DEMO-(\d{4})", row["plate_number"] or "")
        if plate:
            change("vehicles", row, "plate_number", f"1A-{plate[1]}")

    for row in records["customers"]:
        match = re.fullmatch(r"000-DEMO-(\d{4})", row["phone"])
        if match:
            change("customers", row, "phone", f"000-000-{match[1]}")

    for sale in records["sales"]:
        match = re.fullmatch(r"SALE-DEMO-(\d+)", sale["sale_code"])
        if not match:
            continue
        code = f"SALE-{int(match[1]):06}"
        change("sales", sale, "sale_code", code)
        for movement in records["stock_movements"]:
            if (
                movement["vehicle_id"] == sale["vehicle_id"]
                and movement["user_id"] == sale["user_id"]
                and movement["movement_date"] == sale["sale_date"]
                and movement["movement_type"] == "STOCK_OUT"
                and movement["reason"] == "Sale " + sale["sale_code"]
            ):
                change("stock_movements", movement, "reason", "Vehicle sold")

    for row in records["invoices"]:
        match = re.fullmatch(r"INV-DEMO-(\d+)", row["invoice_number"])
        if match:
            change("invoices", row, "invoice_number", f"INV-{int(match[1]):06}")

    reasons = {
        "Development seed: received from supplier": "Received from supplier",
        "Development seed: returned to supplier": "Returned to supplier",
        "Development seed: inspection completed": "Inspection completed",
        "Development seed: inventory adjustment": "Inventory adjustment",
        "VERIFY": "Inventory adjustment",
        "DEMO": "Inventory adjustment",
    }
    for row in records["stock_movements"]:
        if row["reason"] in reasons:
            change("stock_movements", row, "reason", reasons[row["reason"]])

    # Check against untouched records too; never overwrite a conflicting identifier.
    for table, fields in UNIQUE_FIELDS.items():
        for field in fields:
            replacements = {
                c["id"]: c["new"]
                for c in changes
                if c["table"] == table and c["field"] == field
            }
            seen = set()
            for row in records[table]:
                value = replacements.get(row[TABLE_KEYS[table]], row[field])
                if value is None:
                    continue
                value = value.casefold()
                if value in seen:
                    raise ValueError(
                        f"Identifier collision in {table}.{field}; no changes applied."
                    )
                seen.add(value)
    return changes


def migrate(config=None, apply=False, backup_dir=None):
    config = config or settings()
    with mysql.connector.connect(**dict(config, autocommit=False)) as connection:
        try:
            with connection.cursor(dictionary=True) as cursor:
                records = {}
                for table, key in TABLE_KEYS.items():
                    cursor.execute(f"SELECT * FROM {table} ORDER BY {key} FOR UPDATE")
                    records[table] = cursor.fetchall()
                changes = build_plan(records)
                if apply and changes:
                    folder = Path(backup_dir) if backup_dir else ROOT / "instance"
                    folder.mkdir(parents=True, exist_ok=True)
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                    with (folder / f"identifier-migration-{stamp}.json").open(
                        "x"
                    ) as backup:
                        json.dump(
                            dict(database=config["database"], changes=changes),
                            backup,
                            indent=2,
                        )
                    for change in changes:
                        table, field = change["table"], change["field"]
                        preserve_time = (
                            ", updated_at=updated_at"
                            if table in ("vehicles", "customers", "sales")
                            else ""
                        )
                        cursor.execute(
                            f"UPDATE {table} SET {field}=%s{preserve_time} WHERE {TABLE_KEYS[table]}=%s AND {field}=%s",
                            (change["new"], change["id"], change["old"]),
                        )
                        if cursor.rowcount != 1:
                            raise ValueError(
                                "Record changed during migration; transaction rolled back."
                            )
                    connection.commit()
                else:
                    connection.rollback()
                return changes
        except Exception:
            connection.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply after collision checks and save an identifier backup",
    )
    args = parser.parse_args()
    try:
        changes = migrate(apply=args.apply)
        print(
            f"{'Applied' if args.apply else 'Preview'}: {len(changes)} field changes."
        )
        for change in changes:
            print(
                f"{change['table']} #{change['id']} {change['field']}: {change['old']} -> {change['new']}"
            )
    except (ValueError, mysql.connector.Error) as exc:
        print(
            f"Migration stopped ({type(exc).__name__}); no partial changes committed.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Explicit, repeatable development data. Never invoked by Flask startup."""

import argparse
import sys
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mysql.connector
from database.identifiers import fictional_vin
from werkzeug.security import generate_password_hash

from database.common import ROOT, execute_script, settings

# ============================================================
# IGNITE DEVELOPMENT SAMPLE DATA -- EDIT SAMPLE DATA HERE
# Edit the lists below to change demo records before first seed.
# Existing records are preserved on rerun. Use --reset deliberately
# to rebuild a DEVELOPMENT database after editing these definitions.
# Database insertion logic begins later in this file.
# ============================================================
DEMO_USERS = [
    dict(
        username="katsrieng",
        legacy_username="alex",
        full_name="Katsrieng",
        email="katsrieng@example.com",
        role="Admin",
        password="autovault-demo",
    ),
    dict(
        username="sopanha",
        legacy_username="jordan",
        full_name="Chan Sopanha",
        email="sopanha@example.com",
        role="Manager",
        password="autovault-demo",
    ),
    dict(
        username="sovanara",
        legacy_username="sam",
        full_name="Sovanara",
        email="sovanara@example.com",
        role="Sales Staff",
        password="autovault-demo",
    ),
]
# All contacts and identifiers below are fictional presentation records.
DEMO_CUSTOMERS = [
    dict(
        customer_code=f"CUS-{i:03}",
        full_name=name,
        phone=f"000-000-{i:04}",
        email=f"customer{i:02}@example.com",
        address=f"Sample address {i}, Phnom Penh, Cambodia",
        is_active=i != 12,
    )
    for i, name in enumerate(
        [
            "Sok Dara",
            "Chan Sopheak",
            "Kim Sreymom",
            "Heng Vannak",
            "Meas Sophea",
            "Keo Rith",
            "Chea Bopha",
            "Lim Piseth",
            "Long Sreyneang",
            "Seng Makara",
            "Yim Chenda",
            "Vong Rachana",
        ],
        1,
    )
]
# code, brand, model, year, cost, price, initial status, placeholder, powertrain
VEHICLE_SPECS = [
    (
        "VEH-001",
        "AION",
        "i60 REEV",
        2026,
        "28900",
        "32900",
        "AVAILABLE",
        "suv.svg",
        "Range extender",
    ),
    (
        "VEH-002",
        "BYD",
        "Seal Premium",
        2025,
        "36500",
        "41900",
        "AVAILABLE",
        "sedan.svg",
        "Electric",
    ),
    (
        "VEH-003",
        "Toyota",
        "Camry Hybrid",
        2025,
        "29500",
        "34900",
        "RESERVED",
        "sedan.svg",
        "Hybrid",
    ),
    (
        "VEH-004",
        "Honda",
        "CR-V e:HEV",
        2024,
        "31200",
        "36900",
        "AVAILABLE",
        "suv.svg",
        "Hybrid",
    ),
    (
        "VEH-005",
        "Mazda",
        "CX-5 Signature",
        2024,
        "26200",
        "30900",
        "INACTIVE",
        "suv.svg",
        "Petrol",
    ),
    (
        "VEH-006",
        "Toyota",
        "Corolla Cross",
        2025,
        "23100",
        "27900",
        "AVAILABLE",
        "suv.svg",
        "Hybrid",
    ),
    (
        "VEH-007",
        "Kia",
        "EV6 Air",
        2025,
        "35200",
        "42500",
        "AVAILABLE",
        "sedan.svg",
        "Electric",
    ),
    (
        "VEH-008",
        "Hyundai",
        "Tucson Hybrid",
        2025,
        "30100",
        "35700",
        "AVAILABLE",
        "suv.svg",
        "Hybrid",
    ),
    (
        "VEH-009",
        "Ford",
        "Ranger",
        2024,
        "27000",
        "32500",
        "AVAILABLE",
        "suv.svg",
        "Diesel",
    ),
    (
        "VEH-010",
        "Nissan",
        "X-Trail",
        2025,
        "26500",
        "31900",
        "RESERVED",
        "suv.svg",
        "Hybrid",
    ),
    (
        "VEH-011",
        "Mitsubishi",
        "Xpander",
        2025,
        "20500",
        "24900",
        "AVAILABLE",
        "suv.svg",
        "Petrol",
    ),
    (
        "VEH-012",
        "Hyundai",
        "Elantra",
        2024,
        "19500",
        "23900",
        "INACTIVE",
        "sedan.svg",
        "Petrol",
    ),
    (
        "VEH-013",
        "Toyota",
        "Camry",
        2024,
        "25800",
        "30900",
        "AVAILABLE",
        "sedan.svg",
        "Petrol",
    ),
    (
        "VEH-014",
        "Honda",
        "Civic",
        2025,
        "24000",
        "28500",
        "AVAILABLE",
        "sedan.svg",
        "Petrol",
    ),
    (
        "VEH-015",
        "BYD",
        "Atto 3",
        2025,
        "27000",
        "32500",
        "AVAILABLE",
        "suv.svg",
        "Electric",
    ),
    (
        "VEH-016",
        "Kia",
        "Sportage",
        2024,
        "25500",
        "30500",
        "AVAILABLE",
        "suv.svg",
        "Hybrid",
    ),
    (
        "VEH-017",
        "Mazda",
        "Mazda3",
        2024,
        "21000",
        "25900",
        "AVAILABLE",
        "sedan.svg",
        "Petrol",
    ),
    (
        "VEH-018",
        "Nissan",
        "Navara",
        2025,
        "24800",
        "29900",
        "AVAILABLE",
        "suv.svg",
        "Diesel",
    ),
    (
        "VEH-019",
        "Ford",
        "Everest",
        2025,
        "38000",
        "44900",
        "AVAILABLE",
        "suv.svg",
        "Diesel",
    ),
    (
        "VEH-020",
        "Mitsubishi",
        "Pajero Sport",
        2024,
        "31000",
        "36900",
        "AVAILABLE",
        "suv.svg",
        "Diesel",
    ),
]
DEMO_VEHICLES = [
    dict(
        vehicle_code=code,
        brand=brand,
        model=model,
        vehicle_year=year,
        purchase_price=Decimal(cost),
        selling_price=Decimal(price),
        status=status,
        image_path=image,
        fuel=fuel,
        color=("Silver", "White", "Blue", "Gray")[i % 4],
        vin=fictional_vin(i),
        plate_number=f"1A-{i:04}",
        mileage=i * 600,
    )
    for i, (code, brand, model, year, cost, price, status, image, fuel) in enumerate(
        VEHICLE_SPECS, 1
    )
]
DEMO_SALES = [
    dict(
        sale_code=f"SALE-{i:06}",
        invoice_number=f"INV-{i:06}",
        vehicle_code=f"VEH-{12 + i:03}",
        customer_code=f"CUS-{(i - 1) % 6 + 1:03}",
        username="sopanha",
        days_ago=days,
        discount_amount=Decimal("500.00"),
    )
    for i, days in enumerate([0, 2, 6, 18, 35, 65, 95, 125], 1)
]

# ---------------- DATABASE INSERTION LOGIC -------------------


def lookup(cursor, table, key, value, id_column):
    # All identifiers come from the fixed call sites below, never CLI/form input.
    cursor.execute(f"SELECT {id_column} FROM {table} WHERE {key}=%s", (value,))
    row = cursor.fetchone()
    return row[id_column] if row else None


def insert(cursor, table, values):
    columns = ",".join(values)
    cursor.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({','.join(['%s'] * len(values))})",
        tuple(values.values()),
    )
    return cursor.lastrowid


def seed_database(config=None):
    with mysql.connector.connect(**(config or settings())) as connection:
        try:
            with connection.cursor(dictionary=True) as cursor:
                # Serialize repeat seeds without assuming generated IDs.
                cursor.execute(
                    "SELECT GET_LOCK(%s, 10) AS acquired",
                    (
                        "autovault_"
                        + sha256(connection.database.encode()).hexdigest()[:48],
                    ),
                )
                if cursor.fetchone()["acquired"] != 1:
                    raise ValueError("Another seed operation is running.")
                execute_script(connection, ROOT / "database/seed.sql")
                for data in DEMO_USERS:
                    legacy_id = lookup(
                        cursor, "users", "username", data["legacy_username"], "user_id"
                    )
                    current_id = lookup(
                        cursor, "users", "username", data["username"], "user_id"
                    )
                    if legacy_id:
                        if current_id and current_id != legacy_id:
                            raise ValueError(
                                "Both old and new seed usernames exist: "
                                + data["username"]
                            )
                        # Rename in place to preserve passwords, roles and historical references.
                        cursor.execute(
                            "UPDATE users SET username=%s, full_name=%s, email=%s WHERE user_id=%s",
                            (
                                data["username"],
                                data["full_name"],
                                data["email"],
                                legacy_id,
                            ),
                        )
                    if lookup(cursor, "users", "username", data["username"], "user_id"):
                        continue
                    role_id = lookup(
                        cursor, "roles", "role_name", data["role"], "role_id"
                    )
                    user_id = insert(
                        cursor,
                        "users",
                        dict(
                            username=data["username"],
                            full_name=data["full_name"],
                            email=data["email"],
                            password_hash=generate_password_hash(data["password"]),
                        ),
                    )
                    insert(cursor, "user_roles", dict(user_id=user_id, role_id=role_id))
                for data in DEMO_CUSTOMERS:
                    if not lookup(
                        cursor,
                        "customers",
                        "customer_code",
                        data["customer_code"],
                        "customer_id",
                    ):
                        insert(cursor, "customers", data)
                actor = lookup(cursor, "users", "username", "katsrieng", "user_id")
                today = date.today()
                for data in DEMO_VEHICLES:
                    if lookup(
                        cursor,
                        "vehicles",
                        "vehicle_code",
                        data["vehicle_code"],
                        "vehicle_id",
                    ):
                        continue
                    vehicle_id = insert(cursor, "vehicles", data)
                    insert(
                        cursor,
                        "stock_movements",
                        dict(
                            vehicle_id=vehicle_id,
                            user_id=actor,
                            movement_type="STOCK_IN",
                            movement_date=today - timedelta(days=150),
                            reason="Received from supplier",
                            quantity=1,
                        ),
                    )
                    if data["status"] == "INACTIVE":
                        insert(
                            cursor,
                            "stock_movements",
                            dict(
                                vehicle_id=vehicle_id,
                                user_id=actor,
                                movement_type="STOCK_OUT",
                                movement_date=today - timedelta(days=140),
                                reason="Returned to supplier",
                                quantity=-1,
                            ),
                        )
                    if data["vehicle_code"] == "VEH-001":
                        insert(
                            cursor,
                            "stock_movements",
                            dict(
                                vehicle_id=vehicle_id,
                                user_id=actor,
                                movement_type="ADJUSTMENT",
                                movement_date=today - timedelta(days=1),
                                reason="Inspection completed",
                                quantity=0,
                            ),
                        )
                for data in DEMO_SALES:
                    sale_id = lookup(
                        cursor, "sales", "sale_code", data["sale_code"], "sale_id"
                    )
                    if sale_id:
                        # Preserve existing sales, but never silently accept broken seed relations.
                        cursor.execute(
                            """
                            SELECT s.status, s.total_amount, s.sale_date,
                                   v.status AS vehicle_status, v.vehicle_code,
                                   c.customer_code, u.username,
                                   i.invoice_number, i.issue_date, i.total_amount AS invoice_total,
                                   (SELECT COUNT(*) FROM stock_movements m
                                    WHERE m.vehicle_id=s.vehicle_id AND m.user_id=s.user_id
                                      AND m.movement_type='STOCK_OUT' AND m.quantity=-1
                                      AND m.movement_date=s.sale_date AND m.reason=%s) AS stockouts
                            FROM sales s JOIN vehicles v ON v.vehicle_id=s.vehicle_id
                            JOIN customers c ON c.customer_id=s.customer_id
                            JOIN users u ON u.user_id=s.user_id
                            LEFT JOIN invoices i ON i.sale_id=s.sale_id
                            WHERE s.sale_id=%s
                        """,
                            ("Sale " + data["sale_code"], sale_id),
                        )
                        row = cursor.fetchone()
                        if (
                            row["status"] != "COMPLETED"
                            or row["vehicle_status"] != "SOLD"
                            or row["total_amount"] != row["invoice_total"]
                            or row["sale_date"] != row["issue_date"]
                            or row["stockouts"] != 1
                            or any(
                                row[key] != data[key]
                                for key in (
                                    "vehicle_code",
                                    "customer_code",
                                    "username",
                                    "invoice_number",
                                )
                            )
                        ):
                            raise ValueError(
                                "Existing seed sale is inconsistent: "
                                + data["sale_code"]
                            )
                        continue
                    vehicle_id = lookup(
                        cursor,
                        "vehicles",
                        "vehicle_code",
                        data["vehicle_code"],
                        "vehicle_id",
                    )
                    customer_id = lookup(
                        cursor,
                        "customers",
                        "customer_code",
                        data["customer_code"],
                        "customer_id",
                    )
                    user_id = lookup(
                        cursor, "users", "username", data["username"], "user_id"
                    )
                    cursor.execute(
                        "SELECT selling_price, status FROM vehicles WHERE vehicle_id=%s FOR UPDATE",
                        (vehicle_id,),
                    )
                    vehicle = cursor.fetchone()
                    if not vehicle or vehicle["status"] != "AVAILABLE":
                        raise ValueError(
                            "Seed sale vehicle is unavailable: " + data["vehicle_code"]
                        )
                    cursor.execute(
                        "SELECT is_active FROM customers WHERE customer_id=%s",
                        (customer_id,),
                    )
                    customer = cursor.fetchone()
                    cursor.execute(
                        "SELECT is_active FROM users WHERE user_id=%s", (user_id,)
                    )
                    user = cursor.fetchone()
                    if (
                        not customer
                        or not customer["is_active"]
                        or not user
                        or not user["is_active"]
                    ):
                        raise ValueError(
                            "Seed sale requires an active customer and user."
                        )
                    sold_date = today - timedelta(days=data["days_ago"])
                    price = vehicle["selling_price"]
                    discount = data["discount_amount"]
                    total = price - discount
                    sale_id = insert(
                        cursor,
                        "sales",
                        dict(
                            sale_code=data["sale_code"],
                            user_id=user_id,
                            customer_id=customer_id,
                            vehicle_id=vehicle_id,
                            sale_date=sold_date,
                            sale_price=price,
                            discount_amount=discount,
                            total_amount=total,
                            status="COMPLETED",
                        ),
                    )
                    cursor.execute(
                        "UPDATE vehicles SET status='SOLD' WHERE vehicle_id=%s",
                        (vehicle_id,),
                    )
                    insert(
                        cursor,
                        "stock_movements",
                        dict(
                            vehicle_id=vehicle_id,
                            user_id=user_id,
                            movement_type="STOCK_OUT",
                            movement_date=sold_date,
                            reason="Sale " + data["sale_code"],
                            quantity=-1,
                        ),
                    )
                    insert(
                        cursor,
                        "invoices",
                        dict(
                            invoice_number=data["invoice_number"],
                            sale_id=sale_id,
                            issue_date=sold_date,
                            total_amount=total,
                        ),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        # Connection close releases the named seed lock, even after an exception.


def reset_database(config):
    if (
        input(
            f"DEVELOPMENT ONLY: delete all records in {config['database']}? Type its name: "
        )
        != config["database"]
    ):
        raise ValueError("Reset cancelled.")
    with mysql.connector.connect(**config) as connection:
        try:
            with connection.cursor() as cursor:
                for table in (
                    "invoices",
                    "sales",
                    "stock_movements",
                    "user_roles",
                    "role_permissions",
                    "vehicles",
                    "customers",
                    "users",
                    "permissions",
                    "roles",
                ):
                    cursor.execute("DELETE FROM " + table)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="DESTRUCTIVE: delete all configured database records after confirmation",
    )
    args = parser.parse_args()
    config = settings()
    try:
        if args.reset:
            reset_database(config)
        seed_database(config)
        print("Development seed complete; existing records preserved.")
    except ValueError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    except mysql.connector.Error as exc:
        print(
            f"Seed failed ({type(exc).__name__}); changes rolled back. Check schema, conflicts and database settings.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Identifier cleanup preserves records, links, money and user changes."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import mysql.connector
from database.identifiers import fictional_vin
from database.migrate_identifiers import TABLE_KEYS, migrate
from mysql_support import MySQLTestCase

from database.seed import DEMO_SALES, DEMO_VEHICLES


class SeedIdentifierTests(TestCase):
    def test_clean_unique_fictional_identifiers(self):
        vins = [row["vin"] for row in DEMO_VEHICLES]
        self.assertEqual(len(vins), len(set(vins)))
        for vin in vins:
            self.assertRegex(vin, r"^[A-HJ-NPR-Z0-9]{17}$")
            self.assertFalse(re.search(r"AV|DEMO|IGNITE", vin))
        for index, sale in enumerate(DEMO_SALES, 1):
            self.assertEqual(sale["sale_code"], f"SALE-{index:06}")
            self.assertEqual(sale["invoice_number"], f"INV-{index:06}")


class IdentifierMigrationTests(MySQLTestCase):
    def snapshot(self):
        with mysql.connector.connect(**self.db_config) as connection:
            with connection.cursor(dictionary=True) as cursor:
                result = {}
                for table, key in TABLE_KEYS.items():
                    cursor.execute(f"SELECT * FROM {table} ORDER BY {key}")
                    result[table] = cursor.fetchall()
                return result

    def legacy_records(self):
        with mysql.connector.connect(**self.db_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE vehicles SET vin='AVDEMO00000000001',plate_number='DEMO-0001' WHERE vehicle_id=1"
                )
                cursor.execute(
                    "UPDATE vehicles SET vin='AVVERIFY000000002' WHERE vehicle_id=2"
                )
                cursor.execute(
                    "UPDATE customers SET phone='000-DEMO-0001' WHERE customer_id=1"
                )
                cursor.execute(
                    "UPDATE sales SET sale_code='SALE-DEMO-001' WHERE sale_id=1"
                )
                cursor.execute(
                    "UPDATE invoices SET invoice_number='INV-DEMO-0001' WHERE sale_id=1"
                )
                cursor.execute(
                    "UPDATE stock_movements SET reason='Sale SALE-DEMO-001' WHERE reason='Sale SALE-000001'"
                )
                cursor.execute(
                    "UPDATE stock_movements SET reason='Development seed: inspection completed' WHERE vehicle_id=1 AND movement_type='ADJUSTMENT'"
                )
                cursor.execute(
                    "UPDATE vehicles SET color='User edited color' WHERE vehicle_id=1"
                )
            connection.commit()

    def test_preview_apply_preserve_all_other_fields_and_repeat(self):
        self.legacy_records()
        before = self.snapshot()
        changes = migrate(self.db_config)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(len(changes), 8)
        with TemporaryDirectory() as folder:
            self.assertEqual(
                changes, migrate(self.db_config, apply=True, backup_dir=folder)
            )
            self.assertEqual(len(list(Path(folder).glob("*.json"))), 1)
            self.assertEqual(migrate(self.db_config, apply=True, backup_dir=folder), [])
        after = self.snapshot()
        for change in changes:
            row = next(
                row
                for row in before[change["table"]]
                if row[TABLE_KEYS[change["table"]]] == change["id"]
            )
            row[change["field"]] = change["new"]
        self.assertEqual(before, after)
        self.assertEqual(after["vehicles"][0]["vin"], fictional_vin(1))
        self.assertTrue(
            any(row["reason"] == "Vehicle sold" for row in after["stock_movements"])
        )
        from database.seed import seed_database

        seed_database(self.db_config)
        self.assertEqual(after, self.snapshot())

    def test_reason_cleanup_preserves_custom_text_and_seed_repeat(self):
        from database.seed import seed_database

        with mysql.connector.connect(**self.db_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE stock_movements SET reason='Development seed: inspection completed' WHERE vehicle_id=1 AND movement_type='ADJUSTMENT'"
                )
                cursor.execute(
                    "UPDATE stock_movements SET reason='VERIFY' WHERE vehicle_id=2 AND movement_type='STOCK_IN'"
                )
                cursor.execute(
                    "UPDATE stock_movements SET reason='Customer requested DEMO inspection' WHERE vehicle_id=3 AND movement_type='STOCK_IN'"
                )
            connection.commit()
        with TemporaryDirectory() as folder:
            changes = migrate(self.db_config, apply=True, backup_dir=folder)
        self.assertEqual(
            {change["new"] for change in changes},
            {"Inspection completed", "Inventory adjustment"},
        )
        rows = self.snapshot()["stock_movements"]
        self.assertTrue(
            any(row["reason"] == "Customer requested DEMO inspection" for row in rows)
        )
        seed_database(self.db_config)
        self.assertEqual(rows, self.snapshot()["stock_movements"])

    def test_collision_rolls_back_without_touching_records(self):
        self.legacy_records()
        with mysql.connector.connect(**self.db_config) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE sales SET sale_code='SALE-000001' WHERE sale_id=2"
                )
            connection.commit()
        before = self.snapshot()
        with TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "collision"):
                migrate(self.db_config, apply=True, backup_dir=folder)
            self.assertEqual(list(Path(folder).iterdir()), [])
        self.assertEqual(before, self.snapshot())

    def test_clean_database_is_untouched(self):
        before = self.snapshot()
        self.assertEqual(migrate(self.db_config, apply=True), [])
        self.assertEqual(before, self.snapshot())

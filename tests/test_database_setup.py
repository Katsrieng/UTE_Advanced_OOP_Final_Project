"""Database setup contract; database integration tests use a separate opt-in database."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DatabaseSetupTests(unittest.TestCase):
    def test_setup_entrypoint_exists(self):
        self.assertTrue(
            (ROOT / "database" / "setup.py").is_file(),
            "Missing explicit database setup command",
        )

    def test_schema_creates_database_before_tables(self):
        path = ROOT / "database" / "schema.sql"
        self.assertTrue(path.is_file(), "Missing database schema")
        sql = path.read_text().upper()
        self.assertLess(
            sql.index("CREATE DATABASE IF NOT EXISTS"),
            sql.index("CREATE TABLE IF NOT EXISTS"),
        )
        self.assertNotIn("DROP DATABASE", sql)

    def test_seed_definitions_are_editable_and_consistent(self):
        path = ROOT / "database" / "seed.py"
        self.assertTrue(path.is_file(), "Missing development seed command")
        spec = importlib.util.spec_from_file_location("seed_data", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertGreaterEqual(len(module.DEMO_VEHICLES), 15)
        self.assertGreaterEqual(len(module.DEMO_CUSTOMERS), 10)
        self.assertGreaterEqual(len(module.DEMO_SALES), 6)
        sold = [s["vehicle_code"] for s in module.DEMO_SALES]
        self.assertEqual(len(sold), len(set(sold)))
        self.assertTrue(set(sold) <= {v["vehicle_code"] for v in module.DEMO_VEHICLES})


if __name__ == "__main__":
    unittest.main()


class SetupSafetyTests(unittest.TestCase):
    def test_connects_without_selecting_nonexistent_database(self):
        from unittest.mock import MagicMock, patch

        from database.common import create_schema

        connection = MagicMock()
        connection.__enter__.return_value = connection
        with patch(
            "database.common.mysql.connector.connect", return_value=connection
        ) as connect:
            create_schema(
                dict(
                    host="localhost",
                    user="tester",
                    password="not-a-real-secret",
                    database="ignite_test_setup",
                )
            )
        self.assertNotIn("database", connect.call_args.kwargs)
        statements = [
            call.args[0]
            for call in connection.cursor.return_value.__enter__.return_value.execute.call_args_list
        ]
        self.assertIn(
            "CREATE DATABASE IF NOT EXISTS `ignite_test_setup`", statements[0]
        )
        self.assertIn("USE `ignite_test_setup`", statements[1])
        self.assertEqual(
            sum("CREATE TABLE IF NOT EXISTS" in sql for sql in statements), 10
        )

    def test_unsafe_database_identifier_rejected_before_sql(self):
        from unittest.mock import MagicMock

        from database.common import execute_script

        connection = MagicMock()
        with self.assertRaises(ValueError):
            execute_script(
                connection, ROOT / "database/schema.sql", "bad`; DROP DATABASE other;--"
            )
        connection.cursor.assert_not_called()

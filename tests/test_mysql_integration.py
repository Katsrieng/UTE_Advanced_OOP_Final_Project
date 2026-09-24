from mysql_support import MySQLTestCase

from app import create_app


class MySQLIntegrationTests(MySQLTestCase):
    def test_factory_uses_mysql_and_data_survives_new_app(self):
        app = create_app(self.app_config())
        repo = app.extensions["repository"]
        self.assertEqual(type(repo).__name__, "MySQLRepository")
        vehicle = repo.all("vehicles")[0]
        repo.save("vehicles", {"color": "Persistent blue"}, vehicle["id"])
        fresh = create_app(self.app_config()).extensions["repository"]
        self.assertEqual(
            fresh.get("vehicles", vehicle["id"])["color"], "Persistent blue"
        )
        client = app.test_client()
        client.get("/login")
        with client.session_transaction() as session:
            csrf = session["csrf_token"]
        response = client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "username": "katsrieng",
                "password": "Ignite1234",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/").status_code, 200)

    def test_sale_rollback_at_invoice_failure(self):
        from unittest.mock import patch

        from app.services.sales_service import SalesService

        repo = create_app(self.app_config()).extensions["repository"]
        counts = {k: len(repo.all(k)) for k in ("sales", "inventory", "invoices")}
        execute = repo.db.execute

        def fail(sql, params=()):
            if sql.startswith("INSERT INTO invoices"):
                raise RuntimeError("injected invoice outage")
            return execute(sql, params)

        with patch.object(repo.db, "execute", side_effect=fail):
            with self.assertRaises(RuntimeError):
                SalesService(repo).complete(1, 1, "50.25", 1)
        self.assertEqual(repo.get("vehicles", 1)["status"], "AVAILABLE")
        self.assertEqual(counts, {k: len(repo.all(k)) for k in counts})

    def test_seed_repeat_does_not_duplicate_or_restore_removed_grants(self):
        from app.services.user_service import UserService

        from database.seed import seed_database

        repo = create_app(self.app_config()).extensions["repository"]
        counts = {k: len(repo.all(k)) for k in repo.entities}
        UserService(repo).permissions("Sales Staff", ["vehicles.view"])
        seed_database(self.db_config)
        self.assertEqual(counts, {k: len(repo.all(k)) for k in counts})
        self.assertEqual(repo.users.permissions(3), {"vehicles.view"})
        self.assertEqual(
            repo.db.query(
                "SELECT COUNT(*) AS n FROM invoices i JOIN sales s ON s.sale_id=i.sale_id WHERE i.total_amount<>s.total_amount"
            )[0]["n"],
            0,
        )

    def test_hash_login_inactive_logout_and_multi_role_rbac(self):
        from app.services.auth_service import AuthService

        repo = create_app(self.app_config()).extensions["repository"]
        auth = AuthService(repo)
        self.assertIsNotNone(auth.authenticate("katsrieng", "Ignite1234"))
        self.assertIsNone(auth.authenticate("katsrieng", "' OR 1=1 --"))
        self.assertNotIn("password_hash", repo.get("users", 1))
        self.assertNotEqual(
            repo.users.credentials("katsrieng")["password_hash"], "Ignite1234"
        )
        repo.save("users", {"status": "INACTIVE"}, 1)
        self.assertIsNone(auth.authenticate("katsrieng", "Ignite1234"))
        manager = repo.role_repository.get_by_name("Manager")["role_id"]
        repo.db.execute(
            "INSERT INTO user_roles (user_id,role_id) VALUES (%s,%s)", (3, manager)
        )
        self.assertIn("reports.view", repo.users.permissions(3))
        self.assertNotIn("users.manage", repo.users.permissions(3))

    def test_unique_values_and_sql_injection_search(self):
        from app.database import PersistenceError

        repo = create_app(self.app_config()).extensions["repository"]
        for key in ("vin", "plate", "code"):
            with self.subTest(key=key):
                with self.assertRaises(PersistenceError):
                    repo.save("vehicles", {key: repo.get("vehicles", 1)[key]}, 2)
        rows, total, _, _ = repo.page("vehicles", {"q": "' OR 1=1 --"})
        self.assertEqual(total, 0)
        self.assertEqual(len(repo.all("vehicles")), 20)

    def test_decimal_sale_report_and_invoice(self):
        from decimal import Decimal

        from app.services.sales_service import SalesService

        repo = create_app(self.app_config()).extensions["repository"]
        before = repo.analytics()["revenue"]
        sale, invoice = SalesService(repo).complete(1, 1, "0.10", 1)
        self.assertIsInstance(sale["total"], Decimal)
        self.assertEqual(sale["total"], Decimal("32899.90"))
        self.assertEqual(invoice["total"], sale["total"])
        self.assertEqual(repo.analytics()["revenue"], before + sale["total"])
        self.assertEqual(repo.analytics("1900-01-01", "1900-01-02")["sales_count"], 0)

    def test_last_admin_protected(self):
        from app.services.user_service import UserService

        repo = create_app(self.app_config()).extensions["repository"]
        user = dict(repo.get("users", 1), role="Sales Staff", status="INACTIVE")
        with self.assertRaisesRegex(ValueError, "administrator"):
            UserService(repo).save(user, 1, 2)
        self.assertEqual(repo.get("users", 1)["status"], "ACTIVE")

    def test_database_outage_is_friendly_503(self):
        from unittest.mock import patch

        from app.database import DatabaseUnavailable

        app = create_app(self.app_config())
        with patch.object(
            app.extensions["repository"],
            "get",
            side_effect=DatabaseUnavailable("private details"),
        ):
            response = app.test_client().get("/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private details", response.text)

    def test_schema_length_validation_preserves_form(self):
        app = create_app(self.app_config())
        client = app.test_client()
        client.get("/login")
        with client.session_transaction() as session:
            session["user_id"] = 1
            csrf = session["csrf_token"]
        response = client.post(
            "/customers/new",
            data=dict(
                csrf_token=csrf,
                code="X" * 81,
                name="Length check",
                phone="000",
                email="length@example.com",
                address="",
                status="ACTIVE",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("80 characters", response.text)
        self.assertIn("Length check", response.text)

    def test_seed_rejects_missing_stockout(self):
        from database.seed import seed_database

        repo = create_app(self.app_config()).extensions["repository"]
        repo.db.execute("DELETE FROM stock_movements WHERE reason='Sale SALE-000001'")
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            seed_database(self.db_config)

    def test_seed_user_rename_preserves_identity_passwords_and_grants(self):
        from database.seed import DEMO_USERS, seed_database

        repo = create_app(self.app_config()).extensions["repository"]
        before = repo.db.query(
            "SELECT user_id,password_hash FROM users ORDER BY user_id"
        )
        grants = repo.db.query(
            "SELECT user_id,role_id FROM user_roles ORDER BY user_id,role_id"
        )
        for data in DEMO_USERS:
            repo.db.execute(
                "UPDATE users SET username=%s WHERE username=%s",
                (data["legacy_username"], data["username"]),
            )
        seed_database(self.db_config)
        self.assertEqual(
            before,
            repo.db.query("SELECT user_id,password_hash FROM users ORDER BY user_id"),
        )
        self.assertEqual(
            grants,
            repo.db.query(
                "SELECT user_id,role_id FROM user_roles ORDER BY user_id,role_id"
            ),
        )
        self.assertEqual(
            [u["name"] for u in repo.all("users")],
            ["Katsrieng", "Chan Sopanha", "Sovanara"],
        )

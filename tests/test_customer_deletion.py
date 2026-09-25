"""Customer deletion never removes transaction history."""

from unittest.mock import patch
from mysql_support import MySQLTestCase
from app import create_app
from app.database import PersistenceError
from app.services.customer_service import CustomerService


class CustomerDeletionTests(MySQLTestCase):
    def setUp(self):
        super().setUp()
        self.app = create_app(self.app_config())
        self.repo = self.app.extensions["repository"]
        self.customer = self.repo.save(
            "customers",
            dict(
                code="DELETE-CUSTOMER",
                name="Delete Test",
                phone="000",
                email="delete@example.com",
                address="",
                status="ACTIVE",
            ),
        )
        self.url = f"/customers/{self.customer['id']}/delete"
        self.service = CustomerService(self.repo)
        self.client = self.app.test_client()
        self.client.get("/login")
        self.as_user(1)

    def as_user(self, user_id):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            self.csrf = session["csrf_token"]

    def post(self, confirmed=True):
        return self.client.post(
            self.url,
            data={
                "csrf_token": self.csrf,
                "confirm_delete": "yes" if confirmed else "",
            },
        )

    def test_admin_confirmation_and_delete(self):
        self.assertIn(
            self.url, self.client.get(f"/customers/{self.customer['id']}").text
        )
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.post(False).status_code, 400)
        self.assertIsNotNone(self.repo.get("customers", self.customer["id"]))
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/customers"))
        self.assertIsNone(self.repo.get("customers", self.customer["id"]))
        self.assertEqual(self.post().status_code, 404)

    def test_non_admin_and_inactive_admin_rejected(self):
        for user_id in (2, 3):
            self.as_user(user_id)
            self.assertNotIn(
                self.url, self.client.get(f"/customers/{self.customer['id']}").text
            )
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.post().status_code, 403)
            with self.assertRaises(PermissionError):
                self.service.delete(self.customer["id"], user_id, confirmed=True)
        self.as_user(1)
        self.repo.save("users", {"status": "INACTIVE"}, 1)
        self.assertEqual(self.post().status_code, 403)
        with self.assertRaises(PermissionError):
            self.service.delete(self.customer["id"], 1, confirmed=True)

    def test_history_blocks_delete_and_preserves_all_records(self):
        before = {
            key: self.repo.all(key)
            for key in ("customers", "sales", "invoices", "inventory", "vehicles")
        }
        self.url = "/customers/1/delete"
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.assertIn("deactivate", self.client.get(response.location).text.lower())
        self.assertEqual(before, {key: self.repo.all(key) for key in before})

    def test_pending_and_cancelled_sales_without_invoices_block_delete(self):
        sale = self.repo.save(
            "sales",
            dict(
                code="DELETE-TEST-SALE",
                user_id=1,
                customer_id=self.customer["id"],
                vehicle_id=1,
                date="2026-09-25",
                price=100,
                discount=0,
                total=100,
                status="PENDING",
            ),
        )
        for status in ("PENDING", "CANCELLED"):
            self.repo.save("sales", {"status": status}, sale["id"])
            with self.assertRaisesRegex(ValueError, "deactivate"):
                self.service.delete(self.customer["id"], 1, confirmed=True)
        self.assertIsNotNone(self.repo.get("customers", self.customer["id"]))

    def test_csrf_service_confirmation_and_rollback(self):
        self.assertEqual(
            self.client.post(self.url, data={"confirm_delete": "yes"}).status_code, 403
        )
        with self.assertRaisesRegex(ValueError, "confirm"):
            self.service.delete(self.customer["id"], 1)
        execute = self.repo.db.execute

        def fail(sql, params=()):
            result = execute(sql, params)
            if sql.startswith("DELETE FROM customers"):
                raise PersistenceError("injected failure")
            return result

        with patch.object(self.repo.db, "execute", side_effect=fail):
            response = self.post()
            self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self.repo.get("customers", self.customer["id"]))

    def test_concurrent_sale_and_delete(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from app.services.sales_service import SalesService

        barrier = Barrier(2)
        before = {
            key: len(self.repo.all(key)) for key in ("sales", "invoices", "inventory")
        }

        def sell():
            barrier.wait(timeout=10)
            try:
                SalesService(self.repo).complete(self.customer["id"], 1, 0, 2)
                return True
            except ValueError:
                return False

        def delete():
            barrier.wait(timeout=10)
            try:
                self.service.delete(self.customer["id"], 1, confirmed=True)
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            sale, deletion = pool.submit(sell), pool.submit(delete)
            sold, deleted = sale.result(timeout=20), deletion.result(timeout=20)
        self.assertNotEqual(sold, deleted)
        self.assertEqual(
            self.repo.get("customers", self.customer["id"]) is not None, sold
        )
        for key, count in before.items():
            self.assertEqual(len(self.repo.all(key)), count + int(sold))

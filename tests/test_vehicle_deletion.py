"""Permanent deletion uses isolated MySQL records and temporary photo storage."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mysql_support import MySQLTestCase

from app import create_app
from app.database import PersistenceError
from app.services.vehicle_photo_service import VehiclePhotoService
from app.services.vehicle_service import VehicleService


class VehicleDeletionTests(MySQLTestCase):
    def setUp(self):
        super().setUp()
        self.app = create_app(self.app_config())
        self.repo = self.app.extensions["repository"]
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app.static_folder = self.temp.name
        self.service = VehicleService(VehiclePhotoService(self.repo, self.temp.name))
        self.vehicle = self.repo.save(
            "vehicles",
            dict(
                code="DELETE-001",
                brand="Toyota",
                model="Delete test",
                year=2025,
                color="Blue",
                vin="9ZZ1K8R2000000099",
                plate=None,
                purchase_price=20000,
                price=25000,
                status="AVAILABLE",
                image="uploads/vehicles/vehicle_" + "a" * 32 + ".png",
                mileage=0,
                fuel="Petrol",
            ),
        )
        self.photo = Path(self.temp.name) / self.vehicle["image"]
        self.photo.parent.mkdir(parents=True)
        self.photo.write_bytes(b"test photo")
        self.url = f"/vehicles/{self.vehicle['id']}/delete"
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

    def test_admin_confirmation_and_permanent_delete(self):
        details = self.client.get(f"/vehicles/{self.vehicle['id']}")
        self.assertIn(self.url, details.text)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.post(False).status_code, 400)
        self.assertIsNotNone(self.repo.get("vehicles", self.vehicle["id"]))
        response = self.post()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/vehicles"))
        self.assertIsNone(self.repo.get("vehicles", self.vehicle["id"]))
        self.assertFalse(self.photo.exists())
        self.assertEqual(self.post().status_code, 404)

    def test_non_admin_cannot_delete_even_with_delete_permission(self):
        role = self.repo.role_repository.get_by_name("Manager")
        self.repo.db.execute(
            "INSERT IGNORE INTO role_permissions (role_id,permission_id) "
            "SELECT %s,permission_id FROM permissions WHERE permission_name='vehicles.delete'",
            (role["role_id"],),
        )
        for user_id in (2, 3):
            with self.subTest(user_id=user_id):
                self.as_user(user_id)
                self.assertNotIn(
                    self.url, self.client.get(f"/vehicles/{self.vehicle['id']}").text
                )
                self.assertEqual(self.client.get(self.url).status_code, 403)
                self.assertEqual(self.post().status_code, 403)
                with self.assertRaises(PermissionError):
                    self.service.delete(self.vehicle["id"], user_id, confirmed=True)
        self.assertIsNotNone(self.repo.get("vehicles", self.vehicle["id"]))

    def test_missing_csrf_and_inactive_admin_are_rejected(self):
        self.assertEqual(
            self.client.post(self.url, data={"confirm_delete": "yes"}).status_code, 403
        )
        self.repo.save("users", {"status": "INACTIVE"}, 1)
        self.assertEqual(self.post().status_code, 403)
        with self.assertRaises(PermissionError):
            self.service.delete(self.vehicle["id"], 1, confirmed=True)
        self.assertTrue(self.photo.exists())

    def test_history_blocks_delete_without_changing_records(self):
        for vehicle_id in (1, 13):
            with self.subTest(vehicle_id=vehicle_id):
                self.url = f"/vehicles/{vehicle_id}/delete"
                before = {
                    table: self.repo.all(table)
                    for table in ("vehicles", "sales", "invoices", "inventory")
                }
                response = self.post()
                self.assertEqual(response.status_code, 302)
                self.assertIn(
                    "deactivate", self.client.get(response.location).text.lower()
                )
                self.assertEqual(
                    before, {table: self.repo.all(table) for table in before}
                )

    def test_sale_without_invoice_or_stock_also_blocks_delete(self):
        self.repo.save(
            "sales",
            dict(
                code="DELETE-SALE",
                user_id=1,
                customer_id=1,
                vehicle_id=self.vehicle["id"],
                date="2026-09-24",
                price=25000,
                discount=0,
                total=25000,
                status="PENDING",
            ),
        )
        with self.assertRaisesRegex(ValueError, "deactivate"):
            self.service.delete(self.vehicle["id"], 1, confirmed=True)
        self.assertIsNotNone(self.repo.get("vehicles", self.vehicle["id"]))
        self.assertTrue(self.photo.exists())

    def test_service_requires_confirmation_and_rolls_back_failure(self):
        with self.assertRaisesRegex(ValueError, "confirm"):
            self.service.delete(self.vehicle["id"], 1, confirmed=False)
        execute = self.repo.db.execute

        def fail_after_delete(sql, params=()):
            result = execute(sql, params)
            if sql.startswith("DELETE FROM vehicles"):
                raise PersistenceError("injected failure")
            return result

        with patch.object(self.repo.db, "execute", side_effect=fail_after_delete):
            with self.assertRaises(ValueError):
                self.service.delete(self.vehicle["id"], 1, confirmed=True)
        self.assertIsNotNone(self.repo.get("vehicles", self.vehicle["id"]))
        self.assertTrue(self.photo.exists())

    def test_concurrent_sale_and_delete_preserve_history(self):
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
                SalesService(self.repo).complete(1, self.vehicle["id"], 0, 2)
                return True
            except ValueError:
                return False

        def delete():
            barrier.wait(timeout=10)
            try:
                self.service.delete(self.vehicle["id"], 1, confirmed=True)
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            sale = pool.submit(sell)
            deletion = pool.submit(delete)
            sold, deleted = sale.result(timeout=20), deletion.result(timeout=20)
        self.assertNotEqual(sold, deleted)
        vehicle = self.repo.get("vehicles", self.vehicle["id"])
        if sold:
            self.assertEqual(vehicle["status"], "SOLD")
            self.assertTrue(self.photo.exists())
        else:
            self.assertIsNone(vehicle)
            self.assertFalse(self.photo.exists())
        for key, count in before.items():
            self.assertEqual(len(self.repo.all(key)), count + int(sold))

    def test_inactive_admin_role_blocks_delete(self):
        self.repo.db.execute("UPDATE roles SET is_active=0 WHERE role_name='Admin'")
        self.assertEqual(self.post().status_code, 403)
        with self.assertRaises(PermissionError):
            self.service.delete(self.vehicle["id"], 1, confirmed=True)
        self.assertIsNotNone(self.repo.get("vehicles", self.vehicle["id"]))

    def test_shared_photo_is_preserved(self):
        self.repo.save("vehicles", {"image": self.vehicle["image"]}, 1)
        self.assertEqual(self.post().status_code, 302)
        self.assertIsNone(self.repo.get("vehicles", self.vehicle["id"]))
        self.assertTrue(self.photo.exists())

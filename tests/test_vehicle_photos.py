"""Photo lifecycle tests use generated images and an isolated temporary static root."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mysql_support import MySQLTestCase
from PIL import Image

from app import create_app


class VehiclePhotoTests(MySQLTestCase):
    def setUp(self):
        super().setUp()
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        placeholders = self.root / "images" / "vehicles"
        placeholders.mkdir(parents=True)
        for name in ("sedan.svg", "suv.svg"):
            (placeholders / name).write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"/>'
            )
        self.app = create_app(self.app_config())
        self.app.static_folder = str(self.root)
        self.client = self.app.test_client()
        self.repo = self.app.extensions["repository"]
        self.client.get("/login")
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            self.token = session["csrf_token"]

    def image(self, format="PNG", filename=None):
        stream = BytesIO()
        Image.new("RGB", (24, 16), "navy").save(stream, format=format)
        stream.seek(0)
        return stream, filename or (
            "car." + {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[format]
        )

    def fields(self, vehicle=None):
        if vehicle:
            return {
                key: vehicle[key]
                for key in (
                    "code",
                    "brand",
                    "model",
                    "year",
                    "color",
                    "vin",
                    "plate",
                    "purchase_price",
                    "price",
                    "status",
                )
            }
        return dict(
            code="PHOTO-001",
            brand="AION",
            model="Photo Test",
            year=2026,
            color="Blue",
            vin="PHOTO000000000001",
            plate="",
            purchase_price=20000,
            price=25000,
            status="AVAILABLE",
        )

    def post(self, path, data):
        response = self.client.post(
            path,
            data=dict(data, csrf_token=self.token),
            content_type="multipart/form-data",
        )
        # Werkzeug's multipart test builder may spool large request bodies to disk.
        response.request.close()
        response.request.environ["wsgi.input"].close()
        return response

    def upload_existing(self, format="PNG"):
        response = self.post(
            "/vehicles/1/edit",
            dict(self.fields(self.repo.get("vehicles", 1)), photo=self.image(format)),
        )
        self.assertEqual(response.status_code, 302)
        stored = self.repo.get("vehicles", 1)["image"]
        self.assertTrue(stored.startswith("uploads/vehicles/"), stored)
        self.assertTrue((self.root / stored).is_file())
        return stored

    def uploaded_files(self):
        return list((self.root / "uploads" / "vehicles").glob("vehicle_*"))

    def test_create_without_photo_uses_placeholder(self):
        response = self.post("/vehicles/new", self.fields())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.repo.all("vehicles")[-1]["image"], "sedan.svg")
        self.assertEqual(self.uploaded_files(), [])

    def test_blank_plate_stays_null_through_edit_and_validation(self):
        response = self.post("/vehicles/new", self.fields())
        self.assertEqual(response.status_code, 302)
        vehicle = self.repo.all("vehicles")[-1]
        item_id = vehicle["id"]
        self.assertIsNone(vehicle["plate"])
        for plate in ("", "  ", "None", " none "):
            with self.subTest(plate=plate):
                page = self.client.get(f"/vehicles/{item_id}/edit")
                self.assertRegex(page.text, r'id="plate"[^>]*value=""')
                fields = dict(self.fields(vehicle), plate=plate, purchase_price=0)
                invalid = self.post(f"/vehicles/{item_id}/edit", dict(fields, brand=""))
                self.assertEqual(invalid.status_code, 200)
                self.assertRegex(invalid.text, r'id="plate"[^>]*value=""')
                self.assertRegex(invalid.text, r'id="purchase_price"[^>]*value="0.00"')
                saved = self.post(f"/vehicles/{item_id}/edit", fields)
                self.assertEqual(saved.status_code, 302)
                self.assertIsNone(self.repo.get("vehicles", item_id)["plate"])
                self.assertIn("Not assigned", self.client.get(f"/vehicles/{item_id}").text)
        for plate in (None, "None", " "):
            self.repo.save("vehicles", {"plate": plate}, item_id)
            self.assertIsNone(self.repo.get("vehicles", item_id)["plate"])
        self.repo.save("vehicles", {"plate": "1A-1234"}, item_id)
        self.assertEqual(self.repo.get("vehicles", item_id)["plate"], "1A-1234")

    def test_create_with_each_supported_format(self):
        for i, (format, filename) in enumerate(
            (("PNG", "car.png"), ("JPEG", "car.jpg"), ("JPEG", "car.jpeg"), ("WEBP", "car.webp"))
        ):
            with self.subTest(format=format, filename=filename):
                fields = dict(
                    self.fields(),
                    code=f"PHOTO-{i}",
                    vin=f"PHOTO{i:012}",
                    photo=self.image(format, filename),
                )
                response = self.post("/vehicles/new", fields)
                self.assertEqual(response.status_code, 302)
                vehicle = self.repo.all("vehicles")[-1]
                self.assertRegex(
                    vehicle["image"],
                    r"^uploads/vehicles/vehicle_[a-f0-9]{32}\.(png|jpe?g|webp)$",
                )
                with Image.open(self.root / vehicle["image"]) as image:
                    self.assertEqual(image.format, format)

    def test_invalid_extension_and_disguised_content_rejected(self):
        for upload in (
            self.image(filename="car.svg"),
            (BytesIO(b"<script>bad</script>"), "car.png"),
            self.image(filename="car.jpg"),
        ):
            response = self.post("/vehicles/new", dict(self.fields(), photo=upload))
            self.assertEqual(response.status_code, 200)
            self.assertIn("photo-error", response.text)
            self.assertEqual(len(self.repo.all("vehicles")), 20)
            self.assertEqual(self.uploaded_files(), [])

    def test_edit_without_upload_preserves_photo(self):
        old = self.upload_existing()
        response = self.post(
            "/vehicles/1/edit",
            dict(self.fields(self.repo.get("vehicles", 1)), color="Silver"),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.repo.get("vehicles", 1)["image"], old)
        self.assertTrue((self.root / old).exists())

    def test_replace_removes_old_upload_only_after_save(self):
        old = self.upload_existing()
        new = self.upload_existing("WEBP")
        self.assertNotEqual(new, old)
        self.assertFalse((self.root / old).exists())
        self.assertTrue((self.root / new).exists())

    def test_remove_keeps_vehicle_and_restores_placeholder(self):
        old = self.upload_existing()
        count = len(self.repo.all("vehicles"))
        response = self.post("/vehicles/1/photo/remove", {"confirm_remove": "yes"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.repo.all("vehicles")), count)
        self.assertEqual(self.repo.get("vehicles", 1)["image"], "sedan.svg")
        self.assertFalse((self.root / old).exists())

    def test_removal_requires_confirmation_permission_and_csrf(self):
        old = self.upload_existing()
        self.assertEqual(self.post("/vehicles/1/photo/remove", {}).status_code, 400)
        self.assertEqual(
            self.client.post(
                "/vehicles/1/photo/remove", data={"confirm_remove": "yes"}
            ).status_code,
            403,
        )
        with self.client.session_transaction() as session:
            session["user_id"] = 3
        self.assertEqual(
            self.post(
                "/vehicles/1/photo/remove", {"confirm_remove": "yes"}
            ).status_code,
            403,
        )
        self.assertTrue((self.root / old).exists())

    def test_bundled_and_outside_files_are_never_deleted(self):
        outside = self.root / "do-not-delete.png"
        outside.write_bytes(b"protected")
        for path in (
            "sedan.svg",
            "suv.svg",
            "../../do-not-delete.png",
            "uploads/vehicles/../../do-not-delete.png",
            str(outside),
        ):
            self.repo.save("vehicles", {"image": path}, 1)
            self.post("/vehicles/1/photo/remove", {"confirm_remove": "yes"})
        self.assertTrue(outside.exists())
        self.assertTrue((self.root / "images/vehicles/sedan.svg").exists())
        self.assertTrue((self.root / "images/vehicles/suv.svg").exists())

    def test_original_filename_cannot_control_path(self):
        response = self.post(
            "/vehicles/new",
            dict(self.fields(), photo=self.image(filename="../../outside.png")),
        )
        self.assertEqual(response.status_code, 302)
        path = self.repo.all("vehicles")[-1]["image"]
        self.assertRegex(path, r"^uploads/vehicles/vehicle_[a-f0-9]{32}\.png$")
        self.assertFalse((self.root / "outside.png").exists())

    def test_invalid_form_keeps_old_photo_and_creates_no_orphans(self):
        old = self.upload_existing()
        response = self.post(
            "/vehicles/1/edit",
            dict(
                self.fields(self.repo.get("vehicles", 1)),
                vin="bad",
                photo=self.image("WEBP"),
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repo.get("vehicles", 1)["image"], old)
        self.assertEqual(len(self.uploaded_files()), 1)
        self.assertIn("/static/" + old, response.text)

    def test_repository_failure_keeps_old_photo_and_cleans_new_file(self):
        old = self.upload_existing()
        # Inject a persistence outage; exercise the real file lifecycle around it.
        with patch.object(
            self.repo, "save", side_effect=OSError("storage unavailable")
        ):
            response = self.post(
                "/vehicles/1/edit",
                dict(
                    self.fields(self.repo.get("vehicles", 1)), photo=self.image("WEBP")
                ),
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("photo-error", response.text)
        self.assertEqual(self.repo.get("vehicles", 1)["image"], old)
        self.assertEqual(len(self.uploaded_files()), 1)

    def test_shared_upload_not_deleted_while_referenced(self):
        old = self.upload_existing()
        self.repo.save("vehicles", {"image": old}, 2)
        self.post("/vehicles/1/photo/remove", {"confirm_remove": "yes"})
        self.assertTrue((self.root / old).exists())
        self.post("/vehicles/2/photo/remove", {"confirm_remove": "yes"})
        self.assertFalse((self.root / old).exists())

    def test_photo_urls_render_on_all_vehicle_surfaces(self):
        stored = self.upload_existing()
        self.repo.db.execute(
            "UPDATE vehicles SET status='INACTIVE' WHERE vehicle_id<>1 AND status='AVAILABLE'"
        )
        for url in (
            "/",
            "/vehicles?status=AVAILABLE",
            "/vehicles/1",
            "/vehicles/1/edit",
            "/sales/new",
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn("/static/" + stored, response.text, url)
        with self.client.get("/static/" + stored) as response:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "image/png")

    def test_default_and_missing_photos_use_one_fallback(self):
        for image in (
            "sedan.svg",
            "suv.svg",
            "",
            "unknown.svg",
            "uploads/vehicles/vehicle_" + "a" * 32 + ".png",
        ):
            with self.subTest(image=image):
                self.repo.save("vehicles", {"image": image}, 1)
                response = self.client.get("/vehicles/1")
                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    'src="/static/images/vehicles/white-sports-car.svg"', response.text
                )
                self.assertIn(
                    'data-image-fallback="/static/images/vehicles/white-sports-car.svg"',
                    response.text,
                )
                self.assertNotIn('src="/static/uploads/', response.text)
                self.assertNotIn("/static/images/vehicles/sedan.svg", response.text)
                self.assertNotIn("/static/images/vehicles/suv.svg", response.text)

    def test_oversized_upload_has_friendly_error_and_keeps_record(self):
        response = self.post(
            "/vehicles/1/edit",
            dict(
                self.fields(self.repo.get("vehicles", 1)),
                photo=(BytesIO(b"x" * (5 * 1024 * 1024 + 1)), "large.png"),
            ),
        )
        self.assertIn("5 MB", response.text)
        self.assertEqual(self.repo.get("vehicles", 1)["image"], "suv.svg")
        self.assertEqual(self.uploaded_files(), [])

    def test_huge_request_has_branded_error(self):
        response = self.post(
            "/vehicles/1/edit",
            {"photo": (BytesIO(b"x" * (7 * 1024 * 1024)), "large.png")},
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("IGNITE", response.text)
        self.assertIn("5 MB", response.text)

    def test_upload_form_is_multipart_and_shows_current_photo(self):
        old = self.upload_existing()
        html = self.client.get("/vehicles/1/edit").text
        self.assertIn('enctype="multipart/form-data"', html)
        self.assertIn('name="photo"', html)
        self.assertIn("Remove Photo", html)
        self.assertIn("/static/" + old, html)

    def test_filename_collision_does_not_delete_existing_file(self):
        from types import SimpleNamespace

        relative = "uploads/vehicles/vehicle_" + "a" * 32 + ".png"
        existing = self.root / relative
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"previous file")
        with patch(
            "app.services.vehicle_photo_service.uuid4",
            return_value=SimpleNamespace(hex="a" * 32),
        ):
            response = self.post(
                "/vehicles/new", dict(self.fields(), photo=self.image())
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(existing.read_bytes(), b"previous file")

    def test_partial_write_failure_cleans_new_file_and_keeps_old(self):
        old = self.upload_existing()
        upload = self.image("WEBP")

        def fail_save(image, destination, **kwargs):
            destination.write(b"partial")
            raise OSError("disk full")

        with patch.object(Image.Image, "save", fail_save):
            response = self.post(
                "/vehicles/1/edit",
                dict(self.fields(self.repo.get("vehicles", 1)), photo=upload),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.repo.get("vehicles", 1)["image"], old)
        self.assertEqual(self.uploaded_files(), [self.root / old])

    def test_commit_failure_rolls_back_photo_and_preserves_old_file(self):
        from app.services.vehicle_photo_service import PhotoError, VehiclePhotoService
        from flask import g
        from werkzeug.datastructures import FileStorage

        old = self.upload_existing()
        stream, filename = self.image("WEBP")
        with self.app.test_request_context():
            self.repo.get("vehicles", 1)  # Open the request-owned connection.
            with patch.object(
                g.database_connection,
                "commit",
                side_effect=OSError("injected commit failure"),
            ):
                with self.assertRaises(PhotoError):
                    VehiclePhotoService(
                        self.repo, self.root, 5 * 1024 * 1024
                    ).save_vehicle({}, 1, FileStorage(stream=stream, filename=filename))
        self.assertEqual(self.repo.get("vehicles", 1)["image"], old)
        self.assertEqual(self.uploaded_files(), [self.root / old])

"""Common for the existing web endpoints."""

import secrets
from functools import wraps

from flask import Blueprint, abort, current_app, g, redirect, request, session, url_for

from app.services.vehicle_photo_service import VehiclePhotoService

bp = Blueprint("web", __name__)


navigation = [
    ("Main", [("dashboard", "Dashboard", "grid", None)]),
    (
        "Management",
        [
            ("vehicles", "Vehicles", "car", "vehicles.view"),
            ("inventory", "Inventory", "box", "inventory.view"),
            ("customers", "Customers", "people", "customers.view"),
            ("sales", "Sales", "chart", "sales.view"),
            ("invoices", "Invoices", "file", "invoices.view"),
        ],
    ),
    ("Analytics", [("reports", "Reports", "chart", "reports.view")]),
    (
        "Administration",
        [
            ("users", "Users", "people", "users.manage"),
            ("roles", "Roles & Permissions", "shield", "roles.manage"),
        ],
    ),
]


def repo():
    return current_app.extensions["repository"]


def photo_service():
    return VehiclePhotoService(
        repo(), current_app.static_folder, current_app.config["MAX_PHOTO_BYTES"]
    )


def vehicle_image_url(vehicle):
    return url_for("static", filename=photo_service().image_path(vehicle))


def current_user():
    if not hasattr(g, "current_user"):
        g.current_user = repo().get("users", session.get("user_id", 0))
    return g.current_user


def can(permission):
    user = current_user()
    if not user or user["status"] != "ACTIVE":
        return False
    if not hasattr(g, "permissions"):
        g.permissions = repo().users.permissions(user["id"])
    return permission is None or permission in g.permissions


def require(permission=None):
    def decorator(fn):
        @wraps(fn)
        def protected(*args, **kwargs):
            if not current_user():
                return redirect(url_for("web.login"))
            if not can(permission):
                abort(403)
            return fn(*args, **kwargs)

        return protected

    return decorator


@bp.before_request
def csrf_protection():
    if request.method == "POST" and not secrets.compare_digest(
        request.form.get("csrf_token", ""), session.get("csrf_token", "missing")
    ):
        abort(403)

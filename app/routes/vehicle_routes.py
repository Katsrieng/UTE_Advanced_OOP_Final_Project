"""Vehicle routes for the existing web endpoints."""

from datetime import date

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.services.vehicle_photo_service import PhotoError
from app.services.vehicle_service import VehicleService

from .common import bp, current_user, photo_service, repo, require


@bp.route("/vehicles/<int:item_id>/delete", methods=["GET", "POST"])
@require()
def delete_vehicle(item_id):
    if not VehicleService.is_admin(current_user()):
        abort(403)
    vehicle = repo().get("vehicles", item_id)
    if not vehicle:
        abort(404)
    if request.method == "GET" or request.form.get("confirm_delete") != "yes":
        return render_template(
            "vehicles/delete.html",
            row=vehicle,
            active="vehicles",
            title="Confirm permanent deletion",
        ), 200 if request.method == "GET" else 400
    try:
        VehicleService(photo_service()).delete(
            item_id, current_user()["id"], confirmed=True
        )
    except PermissionError:
        abort(403)
    except LookupError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.details", resource="vehicles", item_id=item_id))
    flash("Vehicle permanently deleted.", "success")
    return redirect(url_for("web.listing", resource="vehicles"))


@bp.post("/vehicles/<int:item_id>/photo/remove")
@require("vehicles.update")
def remove_vehicle_photo(item_id):
    if not repo().get("vehicles", item_id):
        abort(404)
    if request.form.get("confirm_remove") != "yes":
        return render_template(
            "errors/photo_confirmation.html",
            title="Confirm photo removal",
            active="vehicles",
            item_id=item_id,
        ), 400
    try:
        photo_service().save_vehicle(
            {"updated": str(date.today())}, item_id, remove=True
        )
    except PhotoError as exc:
        flash(str(exc), "error")
    else:
        flash(
            "Photo removed. The vehicle is unchanged and now uses the default image.",
            "success",
        )
    return redirect(url_for("web.form", resource="vehicles", item_id=item_id))


def save_vehicle(values, item_id=None):
    return VehicleService(photo_service()).save(
        values, item_id, request.files.get("photo")
    )


def vehicle_context(row):
    return {
        "history": repo().history("inventory", "vehicle_id", row["id"]),
        "can_delete_vehicle": VehicleService.is_admin(current_user()),
    }

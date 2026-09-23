"""Shared routes for the existing web endpoints."""

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from .common import bp, can, repo, require
from .customer_routes import customer_context, save_customer
from .form_helpers import form_options, validate_form
from .inventory_routes import save_movement
from .invoice_routes import invoice_context
from .resource_config import FIELDS, RESOURCES
from .sale_routes import new_sale, sale_context
from .user_routes import save_user
from .vehicle_routes import save_vehicle, vehicle_context

SAVE_HANDLERS = {
    "vehicles": save_vehicle,
    "customers": save_customer,
    "inventory": save_movement,
    "users": save_user,
}

DETAIL_CONTEXT = {
    "vehicles": vehicle_context,
    "customers": customer_context,
    "sales": sale_context,
    "invoices": invoice_context,
}


@bp.get("/<resource>")
@require()
def listing(resource):
    config = RESOURCES.get(resource)
    if not config:
        abort(404)
    if not can(config["permission"]):
        abort(403)
    rows, total, page, pages = repo().page(resource, request.args)
    statuses = {
        "vehicles": ["AVAILABLE", "RESERVED", "SOLD", "INACTIVE"],
        "sales": ["PENDING", "COMPLETED", "CANCELLED"],
        "customers": ["ACTIVE", "INACTIVE"],
        "users": ["ACTIVE", "INACTIVE"],
    }.get(resource, [])

    def page_url(n):
        args = request.args.to_dict()
        args["page"] = n
        return url_for("web.listing", resource=resource, **args)

    return render_template(
        "shared/list.html",
        **config,
        active=resource,
        resource=resource,
        rows=rows,
        total=total,
        page=page,
        pages=pages,
        page_url=page_url,
        statuses=statuses,
        brands=sorted({v["brand"] for v in repo().vehicles.filter_options()}),
        years=sorted(
            {v["vehicle_year"] for v in repo().vehicles.filter_options()}, reverse=True
        ),
    )


@bp.route("/<resource>/new", methods=["GET", "POST"])
@bp.route("/<resource>/<int:item_id>/edit", methods=["GET", "POST"])
@require()
def form(resource, item_id=None):
    if resource == "sales" and item_id is None:
        return new_sale()
    if resource not in FIELDS or (resource == "inventory" and item_id):
        abort(404)
    permission = {"users": "users.manage", "inventory": "inventory.create"}.get(
        resource, f"{resource}.{'update' if item_id else 'create'}"
    )
    if not can(permission):
        abort(403)
    original = repo().get(resource, item_id) if item_id else {}
    if item_id and not original:
        abort(404)
    values = dict(original or {})
    errors = {}
    options = form_options(resource, original)
    if request.method == "POST":
        values, errors = validate_form(resource, item_id, original, options)
        if not errors:
            try:
                row = SAVE_HANDLERS[resource](values, item_id)
            except ValueError as exc:
                error_field = {
                    "vehicles": "photo",
                    "inventory": "reason",
                    "users": "password",
                }.get(resource, "code")
                errors[error_field] = str(exc)
            else:
                flash(
                    f"{RESOURCES[resource]['singular']} {'updated' if item_id else 'added'} successfully.",
                    "success",
                )
                return redirect(
                    url_for("web.listing", resource=resource)
                    if resource in ("inventory", "users")
                    else url_for("web.details", resource=resource, item_id=row["id"])
                )
        values.pop("password", None)
    if (
        resource == "inventory"
        and request.args.get("vehicle_id")
        and not request.method == "POST"
    ):
        values["vehicle_id"] = request.args["vehicle_id"]
    return render_template(
        "shared/form.html",
        title=f"{'Edit' if item_id else 'Add'} {RESOURCES[resource]['singular']}",
        active=resource,
        resource=resource,
        fields=FIELDS[resource],
        values=values,
        errors=errors,
        options=options,
        photo_vehicle=original or {},
        item_id=item_id,
    )


@bp.get("/<resource>/<int:item_id>")
@require()
def details(resource, item_id):
    if resource not in ("vehicles", "customers", "sales", "invoices"):
        abort(404)
    if not can(RESOURCES[resource]["permission"]):
        abort(403)
    row = repo().detail(resource, item_id)
    if not row:
        abort(404)
    context = DETAIL_CONTEXT[resource](row)
    return render_template(
        f"{resource}/details.html",
        title=row.get("code", "Details"),
        active=resource,
        row=row,
        **context,
    )

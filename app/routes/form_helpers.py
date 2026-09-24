"""Shared form choices, parsing, and validation for resource handlers."""

from datetime import date
from decimal import Decimal, InvalidOperation

from flask import request, session

from app.models.money import money
from app.services.customer_service import CustomerService
from app.services.vehicle_service import VehicleService

from .common import repo
from .resource_config import FIELDS, TEXT_LIMITS


def form_options(resource, original):
    options = {
        "status": [("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
        "role": [(r, r) for r in repo().roles],
        "movement": [
            ("STOCK_IN", "Stock in — activate vehicle"),
            ("STOCK_OUT", "Stock out — remove from stock"),
            ("ADJUSTMENT", "Adjustment — record an inventory note"),
        ],
        "vehicle_id": [
            (v["id"], f"{v['code']} · {v['brand']} {v['model']}")
            for v in repo().all("vehicles")
            if v["status"] != "SOLD"
        ],
    }
    if resource == "vehicles":
        options["status"] = [
            (s, s.title()) for s in ["AVAILABLE", "RESERVED", "INACTIVE"]
        ]
        if original and original["status"] == "SOLD":
            options["status"] = [("SOLD", "Sold — historical record")]
    return options


def validate_form(resource, item_id, original, options):
    errors = {}
    values = {
        key: request.form.get(key, "").strip()
        for _, fields in FIELDS[resource]
        for key, _, _, _ in fields
    }
    for _, fields in FIELDS[resource]:
        for key, label, kind, required in fields:
            if required and not values[key]:
                errors[key] = f"{label} is required."
            elif len(values[key]) > TEXT_LIMITS.get(key, 250):
                errors[key] = f"Use {TEXT_LIMITS.get(key, 250)} characters or fewer."
            elif kind == "select" and values[key] not in [
                str(k) for k, _ in options[key]
            ]:
                errors[key] = "Choose a valid option."
            elif kind == "number":
                try:
                    number = Decimal(values[key])
                    if not number.is_finite() or number < 0 or number > 100000000:
                        raise ValueError()
                    if key == "year" and (
                        number != number.to_integral_value()
                        or not 1900 <= number <= date.today().year + 2
                    ):
                        raise ValueError()
                    values[key] = int(number) if key == "year" else money(number)
                except (ValueError, InvalidOperation):
                    errors[key] = "Enter a valid positive number within range."
    for key in ("code", "vin", "plate", "username", "email"):
        if (
            values.get(key)
            and (key != "email" or resource == "users")
            and repo().exists(resource, key, values[key], item_id)
        ):
            errors[key] = f"This {key} is already in use."
    if resource == "vehicles":
        errors.update(VehicleService.validate(values))
    if resource == "customers":
        errors.update(CustomerService.validate(values))
    if (
        resource == "users"
        and item_id == session["user_id"]
        and (values["status"] != "ACTIVE" or values["role"] != original["role"])
    ):
        errors["role"] = "Use another administrator account to change your own access."
    if resource == "users" and not item_id and not values.get("password"):
        errors["password"] = "A password is required for a new user."
    return values, errors

"""Customer request orchestration for shared resource routes."""

from flask import abort, flash, redirect, render_template, request, url_for

from app.services.customer_service import CustomerService

from .common import bp, current_user, repo, require


def save_customer(values, item_id=None):
    return CustomerService(repo()).save(values, item_id)


def customer_context(row):
    return {
        "history": repo().history("sales", "customer_id", row["id"]),
        "can_delete_customer": CustomerService.is_admin(current_user()),
    }


@bp.route("/customers/<int:item_id>/delete", methods=["GET", "POST"])
@require()
def delete_customer(item_id):
    if not CustomerService.is_admin(current_user()):
        abort(403)
    customer = repo().get("customers", item_id)
    if not customer:
        abort(404)
    if request.method == "GET" or request.form.get("confirm_delete") != "yes":
        return render_template(
            "customers/delete.html",
            row=customer,
            active="customers",
            title="Confirm permanent deletion",
        ), 200 if request.method == "GET" else 400
    try:
        CustomerService(repo()).delete(item_id, current_user()["id"], confirmed=True)
    except PermissionError:
        abort(403)
    except LookupError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("web.details", resource="customers", item_id=item_id))
    flash("Customer permanently deleted.", "success")
    return redirect(url_for("web.listing", resource="customers"))

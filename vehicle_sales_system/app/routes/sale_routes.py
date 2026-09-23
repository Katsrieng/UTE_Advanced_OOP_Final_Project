"""Sale routes for the existing web endpoints."""

from flask import abort, redirect, render_template, request, url_for

from app.services.sales_service import SalesService

from .common import bp, can, current_user, repo, require


@require("sales.create")
def new_sale():
    error = None
    if request.method == "POST":
        if not can("sales.complete"):
            abort(403)
        try:
            sale, invoice = SalesService(repo()).complete(
                int(request.form.get("customer_id", 0)),
                int(request.form.get("vehicle_id", 0)),
                request.form.get("discount", "0"),
                current_user()["id"],
            )
            return redirect(url_for("web.sale_success", item_id=sale["id"]))
        except (ValueError, TypeError) as exc:
            error = str(exc)
    return render_template(
        "sales/create.html",
        title="New Sale",
        active="sales",
        customers=repo().eligible("customers"),
        vehicles=repo().eligible("vehicles"),
        error=error,
    )


@bp.get("/sales/<int:item_id>/success")
@require("sales.view")
def sale_success(item_id):
    sale = repo().get("sales", item_id)
    if not sale:
        abort(404)
    invoice = repo().entities["invoices"].for_sale(item_id)
    return render_template(
        "sales/success.html",
        title="Sale Completed",
        active="sales",
        sale=sale,
        invoice=invoice,
    )


def sale_context(row):
    return {"invoice": repo().entities["invoices"].for_sale(row["id"])}

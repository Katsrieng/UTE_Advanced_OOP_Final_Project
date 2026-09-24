"""Role routes for the existing web endpoints."""

from flask import abort, flash, redirect, render_template, request, url_for

from app.services.user_service import UserService

from .common import bp, repo, require


@bp.route("/roles", methods=["GET", "POST"])
@require("roles.manage")
def roles():
    selected = request.args.get("role", "Admin")
    if selected not in repo().roles:
        abort(404)
    groups = repo().permission_repository.groups()
    if request.method == "POST":
        try:
            UserService(repo()).permissions(
                selected, request.form.getlist("permissions")
            )
        except ValueError as exc:
            flash(str(exc), "warning")
        else:
            flash("Role permissions updated.", "success")
        return redirect(url_for("web.roles", role=selected))
    return render_template(
        "roles/index.html",
        title="Roles & Permissions",
        active="roles",
        roles=repo().roles,
        selected=selected,
        groups=groups,
    )

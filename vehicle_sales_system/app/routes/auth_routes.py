"""Auth routes for the existing web endpoints."""

from flask import redirect, render_template, request, session, url_for

from app.services.auth_service import AuthService

from .common import bp, repo


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        user = AuthService(repo()).authenticate(
            username, request.form.get("password", "")
        )
        if user:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("web.dashboard"))
        error = "The username or password is incorrect, or this account is inactive."
    return render_template("auth/login.html", error=error)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("web.login"))

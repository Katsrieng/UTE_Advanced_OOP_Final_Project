"""Dashboard routes for the existing web endpoints."""

from datetime import date

from flask import (
    render_template,
)

from app.services.report_service import ReportService

from .common import bp, repo, require


@bp.get("/")
@require()
def dashboard():
    return render_template(
        "dashboard/index.html",
        title="Dashboard",
        active="dashboard",
        featured=repo().vehicles.featured(),
        today=date.today(),
        **ReportService(repo()).analytics(),
    )

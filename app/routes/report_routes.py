"""Report routes for the existing web endpoints."""

from flask import render_template, request

from app.services.report_service import ReportService

from .common import bp, repo, require


@bp.get("/reports")
@require("reports.view")
def reports():
    period = ReportService.period(request.args)
    return render_template(
        "reports/index.html",
        title="Reports",
        active="reports",
        **period,
        **ReportService(repo()).analytics(period["start"], period["end"]),
    )

"""Register feature handlers on one blueprint to preserve web.* endpoints."""

from importlib import import_module

from .common import bp

for module in (
    "auth_routes",
    "dashboard_routes",
    "shared_routes",
    "vehicle_routes",
    "sale_routes",
    "report_routes",
    "role_routes",
):
    import_module(f"{__name__}.{module}")

__all__ = ["bp"]

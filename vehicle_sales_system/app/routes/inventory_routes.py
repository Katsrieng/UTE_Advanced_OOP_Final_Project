"""Inventory request orchestration for shared resource routes."""

from app.services.inventory_service import InventoryService

from .common import current_user, repo


def save_movement(values, item_id=None):
    return InventoryService(repo()).record(
        int(values["vehicle_id"]),
        values["movement"],
        values["reason"],
        current_user()["id"],
    )

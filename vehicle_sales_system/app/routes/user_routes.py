"""User request orchestration for shared resource routes."""

from app.services.user_service import UserService

from .common import current_user, repo


def save_user(values, item_id=None):
    return UserService(repo()).save(values, item_id, current_user()["id"])

"""Customer request orchestration for shared resource routes."""

from app.services.customer_service import CustomerService

from .common import repo


def save_customer(values, item_id=None):
    return CustomerService(repo()).save(values, item_id)


def customer_context(row):
    return {"history": repo().history("sales", "customer_id", row["id"])}

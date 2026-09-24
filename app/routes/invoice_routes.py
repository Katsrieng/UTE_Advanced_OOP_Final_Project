"""Invoice request orchestration for shared resource routes."""

from .common import repo


def invoice_context(row):
    return {"sale": repo().get("sales", row["sale_id"])}

"""Shared explicit setup utilities; importing this module never connects or writes."""

import os
import re
from pathlib import Path

import mysql.connector
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def settings():
    values = {**dotenv_values(ROOT / ".env"), **os.environ}
    name = values.get("DB_NAME", "VehicleSalesDB")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name):
        raise ValueError(
            "DB_NAME must start with a letter and contain only letters, numbers and underscores (max 64)."
        )
    return dict(
        host=values.get("DB_HOST", "localhost"),
        port=int(values.get("DB_PORT", "3307")),
        user=values.get("DB_USER", "root"),
        password=values.get("DB_PASSWORD") or "",
        database=name,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        connection_timeout=5,
        autocommit=False,
    )


def execute_script(connection, path, database=None):
    # Project-owned plain SQL only: no routines, DELIMITER or quoted semicolons.
    sql = "\n".join(
        line
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines()
        if not line.lstrip().startswith("--")
    )
    if database is not None:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", database):
            raise ValueError("Invalid database name.")
        sql = sql.replace("`VehicleSalesDB`", "`" + database + "`")
    with connection.cursor() as cursor:
        for statement in sql.split(";"):
            if statement.strip():
                cursor.execute(statement)


def create_schema(config=None):
    config = dict(config or settings())
    name = config.pop("database")
    # Deliberately connect to the server WITHOUT database: it may not exist yet.
    with mysql.connector.connect(**config) as connection:
        execute_script(connection, ROOT / "database/schema.sql", name)
        connection.commit()
    return name

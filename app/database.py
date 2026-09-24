"""Connection ownership and a transaction shared by participating repositories."""

import logging
from contextlib import contextmanager
from contextvars import ContextVar

import mysql.connector
from flask import g, has_request_context


class PersistenceError(ValueError):
    pass


class DatabaseUnavailable(RuntimeError):
    pass


class Database:
    def __init__(self, config):
        self.config = dict(config, autocommit=True)
        self._active = ContextVar("autovault_connection", default=None)

    @contextmanager
    def connection(self):
        current = self._active.get()
        if current is not None:
            yield current
            return
        try:
            if has_request_context():
                if not hasattr(g, "database_connection"):
                    g.database_connection = mysql.connector.connect(**self.config)
                yield g.database_connection
            else:
                with mysql.connector.connect(**self.config) as connection:
                    yield connection
        except mysql.connector.IntegrityError as exc:
            raise PersistenceError(
                "A unique value is already in use or a related record is invalid."
            ) from exc
        except mysql.connector.Error as exc:
            logging.getLogger(__name__).error(
                "Database operation failed (code %s)", exc.errno
            )
            raise DatabaseUnavailable(
                "Database unavailable. Please try again shortly."
            ) from exc

    @contextmanager
    def transaction(self):
        if self._active.get() is not None:
            raise RuntimeError("Services must not nest transactions.")
        with self.connection() as connection:
            connection.start_transaction(isolation_level="READ COMMITTED")
            token = self._active.set(connection)
            try:
                yield
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                self._active.reset(token)

    def query(self, sql, params=()):
        with self.connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()

    def execute(self, sql, params=()):
        with self.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.lastrowid

"""User record returned by its repository."""

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str
    username: str
    email: str | None
    status: str
    created: str
    updated: str
    role: str

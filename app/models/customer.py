"""Customer record returned by its repository."""

from dataclasses import dataclass


@dataclass
class Customer:
    id: int
    code: str
    name: str
    phone: str
    email: str
    address: str
    status: str
    created: str
    updated: str
    purchases: int

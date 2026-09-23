"""Role record returned by its repository."""

from dataclasses import dataclass


@dataclass
class Role:
    role_id: int
    role_name: str
    is_active: int

"""Permission record returned by its repository."""

from dataclasses import dataclass


@dataclass
class Permission:
    permission_name: str
    module: str

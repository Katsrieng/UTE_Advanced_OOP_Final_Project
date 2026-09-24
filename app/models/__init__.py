from .customer import Customer
from .invoice import Invoice
from .permission import Permission
from .role import Role
from .sale import Sale
from .stock_movement import StockMovement
from .user import User
from .vehicle import Vehicle

__all__ = [
    "User",
    "Role",
    "Permission",
    "Vehicle",
    "Customer",
    "Sale",
    "StockMovement",
    "Invoice",
]

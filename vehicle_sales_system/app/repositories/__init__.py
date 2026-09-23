from .base import EntityRepository
from .customer_repository import CustomerRepository
from .invoice_repository import InvoiceRepository
from .permission_repository import PermissionRepository
from .role_repository import RoleRepository
from .sale_repository import SaleRepository
from .stock_repository import StockMovementRepository
from .user_repository import UserRepository
from .vehicle_repository import VehicleRepository

__all__ = [
    "EntityRepository",
    "VehicleRepository",
    "CustomerRepository",
    "UserRepository",
    "RoleRepository",
    "PermissionRepository",
    "StockMovementRepository",
    "SaleRepository",
    "InvoiceRepository",
]

"""Sales invariants live here, never in browser-only authorization/validation."""
from datetime import date
from decimal import Decimal, InvalidOperation


class SalesService:
    def __init__(self, repository):
        self.repository = repository

    def complete(self, customer_id, vehicle_id, discount, staff):
        repo = self.repository
        with repo.lock:
            customer = repo.get('customers', customer_id)
            vehicle = repo.get('vehicles', vehicle_id)
            if not customer or customer['status'] != 'ACTIVE':
                raise ValueError('Select an active customer.')
            if not vehicle or vehicle['status'] != 'AVAILABLE':
                raise ValueError('This vehicle is no longer available. Select another vehicle.')
            try:
                discount = Decimal(str(discount))
                price = Decimal(str(vehicle['price']))
                if not discount.is_finite() or discount < 0 or discount > price:
                    raise ValueError('Discount must be between zero and the selling price.')
            except InvalidOperation:
                raise ValueError('Enter a valid discount.')
            today = str(date.today())
            number = 1001 + len(repo.all('sales'))
            sale = repo.save('sales', dict(code=f'SAL-{number}', customer_id=customer_id, vehicle_id=vehicle_id, staff=staff, date=today, price=float(price), discount=float(discount.quantize(Decimal('.01'))), total=float((price-discount).quantize(Decimal('.01'))), status='COMPLETED'))
            vehicle['status'] = 'SOLD'
            repo.save('inventory', dict(date=today, vehicle_id=vehicle_id, movement='STOCK_OUT', staff=staff, reason=f"Sale {sale['code']}", quantity=-1))
            invoice = repo.save('invoices', dict(code=f'INV-{number}', sale_id=sale['id'], date=today))
            return sale, invoice

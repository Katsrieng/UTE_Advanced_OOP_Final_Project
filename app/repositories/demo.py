"""Process-local demo adapter. Replace with MySQL repositories for persistence."""
from datetime import date, timedelta
from threading import RLock
from app.models.entities import Vehicle


class DemoRepository:
    def __init__(self):
        self.lock = RLock()
        self.data = {'vehicles': [], 'customers': [], 'sales': [], 'invoices': [], 'inventory': [], 'users': []}
        self.roles = {
            'Admin': ['vehicles.view', 'vehicles.create', 'vehicles.update', 'vehicles.delete', 'customers.view', 'customers.create', 'customers.update', 'inventory.view', 'inventory.create', 'sales.view', 'sales.create', 'sales.complete', 'invoices.view', 'reports.view', 'users.manage', 'roles.manage'],
            'Manager': ['vehicles.view', 'vehicles.create', 'vehicles.update', 'customers.view', 'customers.create', 'customers.update', 'inventory.view', 'inventory.create', 'sales.view', 'sales.create', 'sales.complete', 'invoices.view', 'reports.view'],
            'Sales Staff': ['vehicles.view', 'customers.view', 'customers.create', 'customers.update', 'sales.view', 'sales.create', 'sales.complete', 'invoices.view'],
        }
        self.seed()

    def all(self, resource):
        return self.data[resource]

    def get(self, resource, item_id):
        return next((row for row in self.all(resource) if row['id'] == item_id), None)

    def save(self, resource, values, item_id=None):
        with self.lock:
            if item_id:
                row = self.get(resource, item_id)
                if row is None:
                    raise ValueError('Record not found.')
                row.update(values)
            else:
                row = dict(values, id=max([r['id'] for r in self.all(resource)], default=0) + 1)
                self.all(resource).append(row)
            return row

    def seed(self):
        today = date.today()
        specs = [('AION', 'i60 REEV', 2026, 'Arctic silver', 28900, 32900, 'AVAILABLE', 'suv.svg', 'Range extender'), ('BYD', 'Seal Premium', 2025, 'Glacier blue', 36500, 41900, 'AVAILABLE', 'sedan.svg', 'Electric'), ('Toyota', 'Camry Hybrid', 2025, 'Pearl white', 29500, 34900, 'RESERVED', 'sedan.svg', 'Hybrid'), ('Honda', 'CR-V e:HEV', 2024, 'Lunar silver', 31200, 36900, 'AVAILABLE', 'suv.svg', 'Hybrid'), ('Mazda', 'CX-5 Signature', 2024, 'Graphite gray', 26200, 30900, 'INACTIVE', 'suv.svg', 'Petrol'), ('Toyota', 'Corolla Cross', 2025, 'Pearl white', 23100, 27900, 'AVAILABLE', 'suv.svg', 'Hybrid'), ('Kia', 'EV6 Air', 2025, 'Glacier blue', 35200, 42500, 'AVAILABLE', 'sedan.svg', 'Electric'), ('Hyundai', 'Tucson Hybrid', 2025, 'Arctic silver', 30100, 35700, 'AVAILABLE', 'suv.svg', 'Hybrid')]
        for i, spec in enumerate(specs, 1):
            brand, model, year, color, cost, price, status, image, fuel = spec
            self.data['vehicles'].append(Vehicle(i, f'VH-{i:04}', brand, model, year, color, f'AVDEMO{i:011}', f'AV-{1000+i}', cost, price, status, i * 820, fuel, str(today-timedelta(days=i*3)), image).to_dict())
        for i, (name, email) in enumerate([('Olivia Chen', 'olivia@example.com'), ('James Wilson', 'james@example.com'), ('Sofia Nguyen', 'sofia@example.com'), ('Liam Anderson', 'liam@example.com'), ('Emma Thompson', 'emma@example.com')], 1):
            self.save('customers', dict(code=f'CU-{i:04}', name=name, phone=f'+1 202 555 01{i:02}', email=email, address=f'{20+i} Park Avenue, Springfield', status='ACTIVE', created=str(today-timedelta(days=i*9))))
        for i, (name, username, role) in enumerate([('Alex Morgan', 'alex', 'Admin'), ('Jordan Lee', 'jordan', 'Manager'), ('Sam Taylor', 'sam', 'Sales Staff')], 1):
            self.save('users', dict(name=name, username=username, role=role, status='ACTIVE', created=str(today)))
        # Historical sales use separate physical vehicles, preserving VIN uniqueness.
        for i in range(12):
            original = self.data['vehicles'][i % 4]
            v = self.save('vehicles', dict(original, code=f'VH-{100+i}', vin=f'AVDEMO{100+i:011}', status='SOLD'))
            sold_date = str(today-timedelta(days=i*13))
            sale = self.save('sales', dict(code=f'SAL-{1001+i}', customer_id=i % 5+1, vehicle_id=v['id'], staff='Jordan Lee', date=sold_date, price=v['price'], discount=500, total=v['price']-500, status='COMPLETED'))
            self.save('invoices', dict(code=f'INV-{1001+i}', sale_id=sale['id'], date=sold_date))
            self.save('inventory', dict(date=sold_date, vehicle_id=v['id'], movement='STOCK_OUT', staff='Jordan Lee', reason=f"Sale {sale['code']}", quantity=-1))
        for v in self.data['vehicles'][:8]:
            self.save('inventory', dict(date=v['created'], vehicle_id=v['id'], movement='STOCK_IN', staff='Alex Morgan', reason='Received from supplier', quantity=1))

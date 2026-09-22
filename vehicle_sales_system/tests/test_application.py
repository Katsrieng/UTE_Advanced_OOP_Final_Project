r"""Run with: .venv\Scripts\python.exe -m unittest discover -s tests -v"""
from html.parser import HTMLParser
import unittest
from concurrent.futures import ThreadPoolExecutor

from app import create_app
from app.services.sales import SalesService


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ('href', 'src', 'action'):
            value = values.get(key, '')
            if value.startswith('/'):
                self.links.add(value.split('#')[0])


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only'})
        self.client = self.app.test_client()
        self.repository = self.app.extensions['repository']
        self.client.get('/login')
        self.as_user(1)

    def as_user(self, user_id):
        with self.client.session_transaction() as session:
            session['user_id'] = user_id
            self.csrf = session['csrf_token']

    def post(self, url, data):
        return self.client.post(url, data=dict(data, csrf_token=self.csrf))

    def test_all_pages_and_internal_links_render(self):
        paths = ['/', '/vehicles', '/customers', '/sales', '/invoices', '/inventory', '/reports', '/roles', '/users', '/vehicles/new', '/customers/new', '/users/new', '/inventory/new', '/sales/new', '/vehicles/1', '/customers/1', '/sales/1', '/invoices/1', '/sales/1/success', '/vehicles/1/edit', '/customers/1/edit', '/users/1/edit']
        links = set()
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                parser = LinkParser()
                parser.feed(response.text)
                links |= parser.links
        for link in links - {'/logout'}:
            with self.subTest(link=link):
                with self.client.get(link) as response:
                    self.assertEqual(response.status_code, 200)

    def test_login_and_csrf(self):
        self.post('/logout', {})
        self.assertEqual(self.client.get('/').status_code, 302)
        self.client.get('/login')
        with self.client.session_transaction() as session:
            self.csrf = session['csrf_token']
        self.assertIn('incorrect', self.post('/login', {'username': 'alex', 'password': 'wrong'}).text)
        self.assertEqual(self.post('/login', {'username': 'alex', 'password': 'autovault-demo'}).status_code, 302)
        self.assertEqual(self.client.post('/vehicles/new', data={}).status_code, 403)

    def test_sales_staff_permissions_enforced_on_server(self):
        self.as_user(3)
        for path in ['/users', '/roles', '/reports', '/inventory', '/vehicles/new', '/vehicles/1/edit']:
            self.assertEqual(self.client.get(path).status_code, 403, path)
        self.assertEqual(self.post('/users/new', {'name': 'Unauthorized'}).status_code, 403)
        html = self.client.get('/').text
        self.assertNotIn('href="/users"', html)

    def test_sale_creates_exactly_one_invoice_and_movement(self):
        counts = {key: len(self.repository.all(key)) for key in ('sales', 'invoices', 'inventory')}
        response = self.post('/sales/new', {'customer_id': 1, 'vehicle_id': 1, 'discount': '900'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.repository.get('vehicles', 1)['status'], 'SOLD')
        sale = self.repository.all('sales')[-1]
        self.assertEqual(sale['total'], 32000)
        for key, count in counts.items():
            self.assertEqual(len(self.repository.all(key)), count+1)
        self.assertEqual(self.repository.all('inventory')[-1]['movement'], 'STOCK_OUT')
        self.assertEqual(self.repository.all('invoices')[-1]['sale_id'], sale['id'])
        duplicate = self.post('/sales/new', {'customer_id': 2, 'vehicle_id': 1, 'discount': '0'})
        self.assertIn('no longer available', duplicate.text)
        self.assertEqual(len(self.repository.all('invoices')), counts['invoices']+1)

    def test_concurrent_duplicate_sale_is_rejected(self):
        service = SalesService(self.repository)
        def complete():
            try:
                service.complete(1, 1, 0, 'Test staff')
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _: complete(), range(2))), [False, True])

    def test_invalid_sale_does_not_change_records(self):
        for vehicle, customer, discount in [(3, 1, '0'), (5, 1, '0'), (1, 999, '0'), (1, 1, '-1'), (1, 1, '999999'), (1, 1, 'NaN'), (1, 1, 'Infinity'), (1, 1, 'abc')]:
            response = self.post('/sales/new', {'customer_id': customer, 'vehicle_id': vehicle, 'discount': discount})
            self.assertEqual(response.status_code, 200)
            self.assertIn('role="alert"', response.text)
        self.assertEqual(len(self.repository.all('sales')), 12)
        self.assertEqual(self.repository.get('vehicles', 1)['status'], 'AVAILABLE')

    def test_vehicle_form_validates_and_saves(self):
        data = dict(code='VH-NEW', brand='Test', model='Touring', year='2026', color='Silver', vin='AVTEST00000000001', plate='', purchase_price='20000', price='25000', status='AVAILABLE')
        invalid = self.post('/vehicles/new', dict(data, vin='short', price='-5'))
        self.assertIn('17-character', invalid.text)
        self.assertIn('aria-invalid="true"', invalid.text)
        valid = self.post('/vehicles/new', data)
        self.assertEqual(valid.status_code, 302)
        self.assertIn('Test Touring', self.client.get(valid.location).text)
        duplicate = self.post('/vehicles/new', data)
        self.assertIn('already in use', duplicate.text)

    def test_customer_and_user_forms(self):
        customer = self.post('/customers/new', dict(code='CU-NEW', name='Demo Buyer', email='buyer@example.com', phone='555-0100', address='Demo address', status='ACTIVE'))
        self.assertEqual(customer.status_code, 302)
        self.assertIn('Demo Buyer', self.client.get(customer.location).text)
        user = self.post('/users/new', dict(name='New Staff', username='newstaff', role='Sales Staff', status='ACTIVE'))
        self.assertEqual(user.status_code, 302)
        self.assertEqual(self.repository.all('users')[-1]['role'], 'Sales Staff')

    def test_stock_movement_transitions(self):
        response = self.post('/inventory/new', {'vehicle_id': '5', 'movement': 'STOCK_IN', 'reason': 'Returned from service'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.repository.get('vehicles', 5)['status'], 'AVAILABLE')
        duplicate = self.post('/inventory/new', {'vehicle_id': '5', 'movement': 'STOCK_IN', 'reason': 'Duplicate receipt'})
        self.assertIn('already in stock', duplicate.text)
        self.post('/inventory/new', {'vehicle_id': '5', 'movement': 'STOCK_OUT', 'reason': 'Supplier return'})
        self.assertEqual(self.repository.get('vehicles', 5)['status'], 'INACTIVE')

    def test_filters_pagination_empty_and_errors(self):
        self.assertIn('BYD', self.client.get('/vehicles?brand=BYD&status=AVAILABLE').text)
        self.assertIn('No vehicles match', self.client.get('/vehicles?q=no-such-vehicle').text)
        self.assertIn('Showing 9', self.client.get('/vehicles?page=2').text)
        self.assertIn('Choose a valid start', self.client.get('/reports?period=custom&from=bad&to=bad').text)
        for path in ['/missing', '/vehicles/999', '/customers/999/edit', '/roles?role=missing']:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.repository.data['vehicles'] = []
        self.assertIn('No vehicles yet', self.client.get('/vehicles').text)
        self.assertIn('No available vehicles', self.client.get('/').text)

    def test_role_updates_and_deactivation(self):
        self.post('/roles?role=Sales+Staff', {'permissions': ['vehicles.view']})
        self.as_user(3)
        self.assertEqual(self.client.get('/sales/new').status_code, 403)
        self.as_user(1)
        self.post('/users/3/edit', dict(name='Sam Taylor', username='sam', role='Sales Staff', status='INACTIVE'))
        self.as_user(3)
        self.assertEqual(self.client.get('/').status_code, 403)


if __name__ == '__main__':
    unittest.main()

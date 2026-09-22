from datetime import date, timedelta
from functools import wraps
import math
import secrets
from flask import Blueprint, current_app, render_template, request, redirect, url_for, session, flash, abort
from app.services.sales import SalesService

bp = Blueprint('web', __name__)
navigation = [('Main', [('dashboard', 'Dashboard', 'grid', None)]), ('Management', [('vehicles', 'Vehicles', 'car', 'vehicles.view'), ('inventory', 'Inventory', 'box', 'inventory.view'), ('customers', 'Customers', 'people', 'customers.view'), ('sales', 'Sales', 'chart', 'sales.view'), ('invoices', 'Invoices', 'file', 'invoices.view')]), ('Analytics', [('reports', 'Reports', 'chart', 'reports.view')]), ('Administration', [('users', 'Users', 'people', 'users.manage'), ('roles', 'Roles & Permissions', 'shield', 'roles.manage')])]


def repo():
    return current_app.extensions['repository']


def current_user():
    return repo().get('users', session.get('user_id', 0))


def can(permission):
    user = current_user()
    return bool(user and user['status'] == 'ACTIVE' and (permission is None or permission in repo().roles.get(user['role'], [])))


def require(permission=None):
    def decorator(fn):
        @wraps(fn)
        def protected(*args, **kwargs):
            if not current_user():
                return redirect(url_for('web.login'))
            if not can(permission):
                abort(403)
            return fn(*args, **kwargs)
        return protected
    return decorator


@bp.before_request
def csrf_protection():
    if request.method == 'POST' and not secrets.compare_digest(request.form.get('csrf_token', ''), session.get('csrf_token', 'missing')):
        abort(403)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = next((u for u in repo().all('users') if u['username'] == username and u['status'] == 'ACTIVE'), None)
        if user and request.form.get('password') == 'autovault-demo':
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('web.dashboard'))
        error = 'The username or password is incorrect, or this account is inactive.'
    return render_template('auth/login.html', error=error)


@bp.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('web.login'))


def enriched(resource):
    rows = []
    for item in repo().all(resource):
        row = dict(item)
        if resource in ('sales', 'inventory'):
            row['vehicle'] = repo().get('vehicles', row['vehicle_id'])
        if resource == 'sales':
            row['customer'] = repo().get('customers', row['customer_id'])
        if resource == 'invoices':
            sale = repo().get('sales', row['sale_id'])
            row.update(customer=repo().get('customers', sale['customer_id']), vehicle=repo().get('vehicles', sale['vehicle_id']), total=sale['total'])
        if resource == 'customers':
            row['purchases'] = sum(s['customer_id'] == row['id'] and s['status'] == 'COMPLETED' for s in repo().all('sales'))
        rows.append(row)
    return rows


def analytics(start=None, end=None):
    vehicles = repo().all('vehicles')
    sales = [s for s in enriched('sales') if s['status'] == 'COMPLETED' and (not start or s['date'] >= start) and (not end or s['date'] <= end)]
    counts = {status: sum(v['status'] == status for v in vehicles) for status in ['AVAILABLE', 'RESERVED', 'SOLD', 'INACTIVE']}
    months = []
    today = date.today()
    for offset in range(5, -1, -1):
        month_index = today.year * 12 + today.month - 1 - offset
        month = date(month_index // 12, month_index % 12 + 1, 1)
        months.append(dict(label=month.strftime('%b'), value=sum(s['total'] for s in sales if s['date'].startswith(month.strftime('%Y-%m')))))
    return dict(counts=counts, total_vehicles=len(vehicles), revenue=sum(s['total'] for s in sales), recent_sales=sorted(sales, key=lambda s: s['date'], reverse=True)[:5], chart=months, sales_count=len(sales), movements=[m for m in enriched('inventory') if (not start or m['date'] >= start) and (not end or m['date'] <= end)])


@bp.get('/')
@require()
def dashboard():
    return render_template('dashboard/index.html', title='Dashboard', active='dashboard', featured=next((v for v in repo().all('vehicles') if v['status'] == 'AVAILABLE'), None), today=date.today(), **analytics())


RESOURCES = {
    'vehicles': dict(title='Vehicles', description='Manage and monitor your vehicle inventory.', singular='Vehicle', permission='vehicles.view', create='vehicles.create', columns=['Vehicle', 'VIN', 'Year', 'Price', 'Status', 'Actions']),
    'customers': dict(title='Customers', description='Build relationships that go beyond the sale.', singular='Customer', permission='customers.view', create='customers.create', columns=['Customer', 'Phone', 'Email', 'Purchases', 'Status', 'Actions']),
    'sales': dict(title='Sales', description='Every deal, from first conversation to handover.', singular='Sale', permission='sales.view', create='sales.create', columns=['Sale ID', 'Customer', 'Vehicle', 'Staff', 'Date', 'Total', 'Status', 'Actions']),
    'invoices': dict(title='Invoices', description='A clear record of every completed transaction.', singular='Invoice', permission='invoices.view', create=None, columns=['Invoice number', 'Customer', 'Vehicle', 'Date', 'Total', 'Actions']),
    'inventory': dict(title='Inventory', description='Track the movement of every physical vehicle.', singular='Stock Movement', permission='inventory.view', create='inventory.create', columns=['Date', 'Vehicle', 'Movement', 'Recorded by', 'Reason', 'Quantity']),
    'users': dict(title='Users', description='Manage your team and their access to AutoVault.', singular='User', permission='users.manage', create='users.manage', columns=['Name', 'Username', 'Role', 'Status', 'Actions']),
}


@bp.get('/<resource>')
@require()
def listing(resource):
    config = RESOURCES.get(resource)
    if not config:
        abort(404)
    if not can(config['permission']):
        abort(403)
    rows = enriched(resource)
    query = request.args.get('q', '').strip().lower()
    rows = [r for r in rows if query in ' '.join(str(value) for value in r.values()).lower()]
    for key in ('status', 'brand', 'year', 'movement'):
        if request.args.get(key):
            rows = [r for r in rows if str(r.get(key, '')) == request.args[key]]
    for key, op in [('from', lambda a, b: a >= b), ('to', lambda a, b: a <= b)]:
        if request.args.get(key):
            rows = [r for r in rows if op(r.get('date', r.get('created', '')), request.args[key])]
    rows.sort(key=lambda r: r.get('date', r.get('created', '')), reverse=True)
    total = len(rows)
    pages = max(1, math.ceil(total / 8))
    page = min(max(request.args.get('page', 1, type=int), 1), pages)
    statuses = {'vehicles': ['AVAILABLE', 'RESERVED', 'SOLD', 'INACTIVE'], 'sales': ['PENDING', 'COMPLETED', 'CANCELLED'], 'customers': ['ACTIVE', 'INACTIVE'], 'users': ['ACTIVE', 'INACTIVE']}.get(resource, [])
    def page_url(n):
        args = request.args.to_dict()
        args['page'] = n
        return url_for('web.listing', resource=resource, **args)
    return render_template('shared/list.html', **config, active=resource, resource=resource, rows=rows[(page-1)*8:page*8], total=total, page=page, pages=pages, page_url=page_url, statuses=statuses, brands=sorted({v['brand'] for v in repo().all('vehicles')}), years=sorted({v['year'] for v in repo().all('vehicles')}, reverse=True))


FIELDS = {
    'vehicles': [('Basic information', [('code', 'Vehicle code', 'text', True), ('brand', 'Brand', 'text', True), ('model', 'Model', 'text', True), ('year', 'Year', 'number', True), ('color', 'Color', 'text', True)]), ('Identification', [('vin', 'VIN', 'text', True), ('plate', 'Plate number', 'text', False)]), ('Pricing', [('purchase_price', 'Purchase price (USD)', 'number', True), ('price', 'Selling price (USD)', 'number', True)]), ('Inventory', [('status', 'Status', 'select', True)])],
    'customers': [('Contact information', [('code', 'Customer code', 'text', True), ('name', 'Full name', 'text', True), ('phone', 'Phone', 'tel', True), ('email', 'Email', 'email', True)]), ('Additional details', [('address', 'Address', 'textarea', False), ('status', 'Status', 'select', True)])],
    'users': [('Team member', [('name', 'Full name', 'text', True), ('username', 'Username', 'text', True), ('role', 'Role', 'select', True), ('status', 'Status', 'select', True)])],
    'inventory': [('Movement details', [('vehicle_id', 'Vehicle', 'select', True), ('movement', 'Movement', 'select', True), ('reason', 'Reason', 'textarea', True)])],
}


@bp.route('/<resource>/new', methods=['GET', 'POST'])
@bp.route('/<resource>/<int:item_id>/edit', methods=['GET', 'POST'])
@require()
def form(resource, item_id=None):
    if resource == 'sales' and item_id is None:
        return new_sale()
    if resource not in FIELDS or (resource == 'inventory' and item_id):
        abort(404)
    permission = {'users': 'users.manage', 'inventory': 'inventory.create'}.get(resource, f"{resource}.{'update' if item_id else 'create'}")
    if not can(permission):
        abort(403)
    original = repo().get(resource, item_id) if item_id else {}
    if item_id and not original:
        abort(404)
    values = dict(original or {})
    errors = {}
    options = {'status': [('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')], 'role': [(r, r) for r in repo().roles], 'movement': [('STOCK_IN', 'Stock in — activate vehicle'), ('STOCK_OUT', 'Stock out — remove from stock'), ('ADJUSTMENT', 'Adjustment — record an inventory note')], 'vehicle_id': [(v['id'], f"{v['code']} · {v['brand']} {v['model']}") for v in repo().all('vehicles') if v['status'] != 'SOLD']}
    if resource == 'vehicles':
        options['status'] = [(s, s.title()) for s in ['AVAILABLE', 'RESERVED', 'INACTIVE']]
        if original and original['status'] == 'SOLD':
            options['status'] = [('SOLD', 'Sold — historical record')]
    if request.method == 'POST':
        values = {key: request.form.get(key, '').strip() for _, fields in FIELDS[resource] for key, _, _, _ in fields}
        for _, fields in FIELDS[resource]:
            for key, label, kind, required in fields:
                if required and not values[key]:
                    errors[key] = f'{label} is required.'
                elif len(values[key]) > 250:
                    errors[key] = 'Use 250 characters or fewer.'
                elif kind == 'select' and values[key] not in [str(k) for k, _ in options[key]]:
                    errors[key] = 'Choose a valid option.'
                elif kind == 'number':
                    try:
                        number = float(values[key])
                        if not math.isfinite(number) or number < 0 or number > 100000000:
                            raise ValueError()
                        if key == 'year' and (not number.is_integer() or not 1900 <= number <= date.today().year+2):
                            raise ValueError()
                        values[key] = int(number) if key == 'year' else round(number, 2)
                    except ValueError:
                        errors[key] = 'Enter a valid positive number within range.'
        for key in ('code', 'vin', 'username'):
            if key in values and any(str(r.get(key, '')).lower() == str(values[key]).lower() and r['id'] != item_id for r in repo().all(resource)):
                errors[key] = f'This {key} is already in use.'
        if resource == 'vehicles' and len(values['vin']) != 17:
            errors['vin'] = 'Enter a 17-character VIN.'
        if resource == 'customers' and ('@' not in values['email'] or '.' not in values['email'].split('@')[-1]):
            errors['email'] = 'Enter a valid email address.'
        if resource == 'users' and item_id == session['user_id'] and (values['status'] != 'ACTIVE' or values['role'] != original['role']):
            errors['role'] = 'Use another administrator account to change your own access.'
        if not errors:
            with repo().lock:
                if resource == 'vehicles' and original and original['status'] == 'SOLD' and any(values[k] != original[k] for k in ('vin', 'brand', 'model', 'year', 'price')):
                    errors['vin'] = 'Sold vehicle identity and price are preserved for invoice history.'
                elif resource == 'inventory':
                    vehicle = repo().get('vehicles', int(values['vehicle_id']))
                    if not vehicle or vehicle['status'] == 'SOLD':
                        errors['vehicle_id'] = 'Sold vehicles cannot be changed through stock adjustments.'
                    elif values['movement'] == 'STOCK_IN' and vehicle['status'] != 'INACTIVE':
                        errors['movement'] = 'Stock in requires an inactive vehicle; it is already in stock.'
                    elif values['movement'] == 'STOCK_OUT' and vehicle['status'] == 'INACTIVE':
                        errors['movement'] = 'This vehicle is already out of stock.'
                    else:
                        movement = values['movement']
                        values.update(vehicle_id=vehicle['id'], date=str(date.today()), staff=current_user()['name'], quantity={'STOCK_IN': 1, 'STOCK_OUT': -1, 'ADJUSTMENT': 0}[movement])
                        if movement != 'ADJUSTMENT':
                            vehicle['status'] = 'AVAILABLE' if movement == 'STOCK_IN' else 'INACTIVE'
                if not errors:
                    if not item_id:
                        values['created'] = str(date.today())
                        if resource == 'vehicles':
                            values.update(image='sedan.svg', mileage=0, fuel='Not specified')
                    values['updated'] = str(date.today())
                    row = repo().save(resource, values, item_id)
                    flash(f"{RESOURCES[resource]['singular']} {'updated' if item_id else 'added'} successfully.", 'success')
                    return redirect(url_for('web.listing', resource=resource) if resource in ('inventory', 'users') else url_for('web.details', resource=resource, item_id=row['id']))
    if resource == 'inventory' and request.args.get('vehicle_id') and not request.method == 'POST':
        values['vehicle_id'] = request.args['vehicle_id']
    return render_template('shared/form.html', title=f"{'Edit' if item_id else 'Add'} {RESOURCES[resource]['singular']}", active=resource, resource=resource, fields=FIELDS[resource], values=values, errors=errors, options=options)


@bp.get('/<resource>/<int:item_id>')
@require()
def details(resource, item_id):
    if resource not in ('vehicles', 'customers', 'sales', 'invoices'):
        abort(404)
    if not can(RESOURCES[resource]['permission']):
        abort(403)
    row = next((r for r in enriched(resource) if r['id'] == item_id), None)
    if not row:
        abort(404)
    context = {}
    if resource == 'vehicles':
        context['history'] = [m for m in enriched('inventory') if m['vehicle_id'] == item_id]
    if resource == 'customers':
        context['history'] = [s for s in enriched('sales') if s['customer_id'] == item_id]
    if resource == 'sales':
        context['invoice'] = next((i for i in repo().all('invoices') if i['sale_id'] == item_id), None)
    if resource == 'invoices':
        context['sale'] = repo().get('sales', row['sale_id'])
    return render_template(f'{resource}/details.html', title=row.get('code', 'Details'), active=resource, row=row, **context)


@require('sales.create')
def new_sale():
    error = None
    if request.method == 'POST':
        if not can('sales.complete'):
            abort(403)
        try:
            sale, invoice = SalesService(repo()).complete(int(request.form.get('customer_id', 0)), int(request.form.get('vehicle_id', 0)), request.form.get('discount', '0'), current_user()['name'])
            return redirect(url_for('web.sale_success', item_id=sale['id']))
        except (ValueError, TypeError) as exc:
            error = str(exc)
    return render_template('sales/create.html', title='New Sale', active='sales', customers=[c for c in repo().all('customers') if c['status'] == 'ACTIVE'], vehicles=[v for v in repo().all('vehicles') if v['status'] == 'AVAILABLE'], error=error)


@bp.get('/sales/<int:item_id>/success')
@require('sales.view')
def sale_success(item_id):
    sale = repo().get('sales', item_id)
    if not sale:
        abort(404)
    invoice = next((i for i in repo().all('invoices') if i['sale_id'] == item_id), None)
    return render_template('sales/success.html', title='Sale Completed', active='sales', sale=sale, invoice=invoice)


@bp.get('/reports')
@require('reports.view')
def reports():
    period = request.args.get('period', '30')
    start = request.args.get('from') if period == 'custom' else str(date.today()-timedelta(days={'today': 0, '7': 6, '30': 29}.get(period, 29)))
    end = request.args.get('to') if period == 'custom' else str(date.today())
    error = None
    try:
        if period == 'custom' and (not start or not end or date.fromisoformat(start) > date.fromisoformat(end)):
            raise ValueError()
    except ValueError:
        error = 'Choose a valid start and end date. The start must come first.'
        start = end = str(date.today())
    return render_template('reports/index.html', title='Reports', active='reports', period=period, start=start, end=end, error=error, **analytics(start, end))


@bp.route('/roles', methods=['GET', 'POST'])
@require('roles.manage')
def roles():
    selected = request.args.get('role', 'Admin')
    if selected not in repo().roles:
        abort(404)
    groups = {'Vehicle management': ['vehicles.view', 'vehicles.create', 'vehicles.update', 'vehicles.delete'], 'Customer management': ['customers.view', 'customers.create', 'customers.update'], 'Inventory': ['inventory.view', 'inventory.create'], 'Sales & invoices': ['sales.view', 'sales.create', 'sales.complete', 'invoices.view'], 'Analytics': ['reports.view'], 'Administration': ['users.manage', 'roles.manage']}
    if request.method == 'POST':
        if selected == 'Admin':
            flash('Administrator permissions are protected in the demo.', 'warning')
        else:
            allowed = {p for group in groups.values() for p in group}
            repo().roles[selected] = [p for p in request.form.getlist('permissions') if p in allowed]
            flash('Role permissions updated.', 'success')
        return redirect(url_for('web.roles', role=selected))
    return render_template('roles/index.html', title='Roles & Permissions', active='roles', roles=repo().roles, selected=selected, groups=groups)

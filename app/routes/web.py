from datetime import date, timedelta
from functools import wraps
from decimal import Decimal, InvalidOperation
from app.models.entities import money
from app.services.auth import AuthService, UserService
from app.services.inventory import InventoryService
import secrets
from flask import Blueprint, current_app, render_template, request, redirect, url_for, session, flash, abort, g
from app.services.sales import SalesService
from app.services.vehicle_photos import PhotoError, VehiclePhotoService

bp = Blueprint('web', __name__)
navigation = [('Main', [('dashboard', 'Dashboard', 'grid', None)]), ('Management', [('vehicles', 'Vehicles', 'car', 'vehicles.view'), ('inventory', 'Inventory', 'box', 'inventory.view'), ('customers', 'Customers', 'people', 'customers.view'), ('sales', 'Sales', 'chart', 'sales.view'), ('invoices', 'Invoices', 'file', 'invoices.view')]), ('Analytics', [('reports', 'Reports', 'chart', 'reports.view')]), ('Administration', [('users', 'Users', 'people', 'users.manage'), ('roles', 'Roles & Permissions', 'shield', 'roles.manage')])]


def repo():
    return current_app.extensions['repository']


def photo_service():
    return VehiclePhotoService(repo(), current_app.static_folder, current_app.config['MAX_PHOTO_BYTES'])


def vehicle_image_url(vehicle):
    return url_for('static', filename=photo_service().image_path(vehicle))


def current_user():
    if not hasattr(g, 'current_user'):
        g.current_user = repo().get('users', session.get('user_id', 0))
    return g.current_user


def can(permission):
    user = current_user()
    if not user or user['status'] != 'ACTIVE':
        return False
    if not hasattr(g, 'permissions'):
        g.permissions = repo().users.permissions(user['id'])
    return permission is None or permission in g.permissions


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
        user = AuthService(repo()).authenticate(username, request.form.get('password', ''))
        if user:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('web.dashboard'))
        error = 'The username or password is incorrect, or this account is inactive.'
    return render_template('auth/login.html', error=error)


@bp.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('web.login'))


def analytics(start=None, end=None):
    return repo().analytics(start, end)


@bp.get('/')
@require()
def dashboard():
    return render_template('dashboard/index.html', title='Dashboard', active='dashboard', featured=next(iter(repo().entities['vehicles'].select("t.status='AVAILABLE'", suffix='ORDER BY t.vehicle_id DESC LIMIT 1')), None), today=date.today(), **analytics())


RESOURCES = {
    'vehicles': dict(title='Vehicles', description='Manage and monitor your vehicle inventory.', singular='Vehicle', permission='vehicles.view', create='vehicles.create', columns=['Vehicle', 'VIN', 'Year', 'Price', 'Status', 'Actions']),
    'customers': dict(title='Customers', description='Build relationships that go beyond the sale.', singular='Customer', permission='customers.view', create='customers.create', columns=['Customer', 'Phone', 'Email', 'Purchases', 'Status', 'Actions']),
    'sales': dict(title='Sales', description='Every deal, from first conversation to handover.', singular='Sale', permission='sales.view', create='sales.create', columns=['Sale ID', 'Customer', 'Vehicle', 'Staff', 'Date', 'Total', 'Status', 'Actions']),
    'invoices': dict(title='Invoices', description='A clear record of every completed transaction.', singular='Invoice', permission='invoices.view', create=None, columns=['Invoice number', 'Customer', 'Vehicle', 'Date', 'Total', 'Actions']),
    'inventory': dict(title='Inventory', description='Track the movement of every physical vehicle.', singular='Stock Movement', permission='inventory.view', create='inventory.create', columns=['Date', 'Vehicle', 'Movement', 'Recorded by', 'Reason', 'Quantity']),
    'users': dict(title='Users', description='Manage your team and their access to IGNITE.', singular='User', permission='users.manage', create='users.manage', columns=['Name', 'Username', 'Role', 'Status', 'Actions']),
}


@bp.get('/<resource>')
@require()
def listing(resource):
    config = RESOURCES.get(resource)
    if not config:
        abort(404)
    if not can(config['permission']):
        abort(403)
    rows, total, page, pages = repo().page(resource, request.args)
    statuses = {'vehicles': ['AVAILABLE', 'RESERVED', 'SOLD', 'INACTIVE'], 'sales': ['PENDING', 'COMPLETED', 'CANCELLED'], 'customers': ['ACTIVE', 'INACTIVE'], 'users': ['ACTIVE', 'INACTIVE']}.get(resource, [])
    def page_url(n):
        args = request.args.to_dict()
        args['page'] = n
        return url_for('web.listing', resource=resource, **args)
    return render_template('shared/list.html', **config, active=resource, resource=resource, rows=rows, total=total, page=page, pages=pages, page_url=page_url, statuses=statuses, brands=sorted({v['brand'] for v in repo().vehicles.filter_options()}), years=sorted({v['vehicle_year'] for v in repo().vehicles.filter_options()}, reverse=True))


TEXT_LIMITS = {'code': 80, 'username': 80, 'phone': 80, 'plate': 80,
               'brand': 100, 'color': 100, 'model': 150, 'vin': 17}


FIELDS = {
    'vehicles': [('Basic information', [('code', 'Vehicle code', 'text', True), ('brand', 'Brand', 'text', True), ('model', 'Model', 'text', True), ('year', 'Year', 'number', True), ('color', 'Color', 'text', True)]), ('Identification', [('vin', 'VIN', 'text', True), ('plate', 'Plate number', 'text', False)]), ('Pricing', [('purchase_price', 'Purchase price (USD)', 'number', True), ('price', 'Selling price (USD)', 'number', True)]), ('Inventory', [('status', 'Status', 'select', True)])],
    'customers': [('Contact information', [('code', 'Customer code', 'text', True), ('name', 'Full name', 'text', True), ('phone', 'Phone', 'tel', True), ('email', 'Email', 'email', True)]), ('Additional details', [('address', 'Address', 'textarea', False), ('status', 'Status', 'select', True)])],
    'users': [('Team member', [('name', 'Full name', 'text', True), ('username', 'Username', 'text', True), ('email', 'Email', 'email', True), ('password', 'Password (required for new users)', 'password', False), ('role', 'Role', 'select', True), ('status', 'Status', 'select', True)])],
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
                elif len(values[key]) > TEXT_LIMITS.get(key, 250):
                    errors[key] = f'Use {TEXT_LIMITS.get(key, 250)} characters or fewer.'
                elif kind == 'select' and values[key] not in [str(k) for k, _ in options[key]]:
                    errors[key] = 'Choose a valid option.'
                elif kind == 'number':
                    try:
                        number = Decimal(values[key])
                        if not number.is_finite() or number < 0 or number > 100000000:
                            raise ValueError()
                        if key == 'year' and (number != number.to_integral_value() or not 1900 <= number <= date.today().year+2):
                            raise ValueError()
                        values[key] = int(number) if key == 'year' else money(number)
                    except (ValueError, InvalidOperation):
                        errors[key] = 'Enter a valid positive number within range.'
        for key in ('code', 'vin', 'plate', 'username', 'email'):
            if values.get(key) and (key != 'email' or resource == 'users') and repo().exists(resource, key, values[key], item_id):
                errors[key] = f'This {key} is already in use.'
        if resource == 'vehicles' and len(values['vin']) != 17:
            errors['vin'] = 'Enter a 17-character VIN.'
        if resource == 'customers' and ('@' not in values['email'] or '.' not in values['email'].split('@')[-1]):
            errors['email'] = 'Enter a valid email address.'
        if resource == 'users' and item_id == session['user_id'] and (values['status'] != 'ACTIVE' or values['role'] != original['role']):
            errors['role'] = 'Use another administrator account to change your own access.'
        if resource == 'users' and not item_id and not values.get('password'):
            errors['password'] = 'A password is required for a new user.'
        if not errors:
            try:
                if resource == 'vehicles':
                    if not item_id:
                        values.update(mileage=0, fuel='Not specified')
                    row = photo_service().save_vehicle(values, item_id, request.files.get('photo'))
                elif resource == 'inventory':
                    row = InventoryService(repo()).record(int(values['vehicle_id']), values['movement'], values['reason'], current_user()['id'])
                elif resource == 'users':
                    row = UserService(repo()).save(values, item_id, current_user()['id'])
                else:
                    with repo().transaction():
                        row = repo().save(resource, values, item_id)
            except ValueError as exc:
                errors['photo' if resource == 'vehicles' else 'reason' if resource == 'inventory' else 'password' if resource == 'users' else 'code'] = str(exc)
            else:
                flash(f"{RESOURCES[resource]['singular']} {'updated' if item_id else 'added'} successfully.", 'success')
                return redirect(url_for('web.listing', resource=resource) if resource in ('inventory', 'users') else url_for('web.details', resource=resource, item_id=row['id']))
        values.pop('password', None)
    if resource == 'inventory' and request.args.get('vehicle_id') and not request.method == 'POST':
        values['vehicle_id'] = request.args['vehicle_id']
    return render_template('shared/form.html', title=f"{'Edit' if item_id else 'Add'} {RESOURCES[resource]['singular']}", active=resource, resource=resource, fields=FIELDS[resource], values=values, errors=errors, options=options, photo_vehicle=original or {}, item_id=item_id)


@bp.post('/vehicles/<int:item_id>/photo/remove')
@require('vehicles.update')
def remove_vehicle_photo(item_id):
    if not repo().get('vehicles', item_id):
        abort(404)
    if request.form.get('confirm_remove') != 'yes':
        return render_template('errors/photo_confirmation.html', title='Confirm photo removal', active='vehicles', item_id=item_id), 400
    try:
        photo_service().save_vehicle({'updated': str(date.today())}, item_id, remove=True)
    except PhotoError as exc:
        flash(str(exc), 'error')
    else:
        flash('Photo removed. The vehicle is unchanged and now uses the default image.', 'success')
    return redirect(url_for('web.form', resource='vehicles', item_id=item_id))


@bp.get('/<resource>/<int:item_id>')
@require()
def details(resource, item_id):
    if resource not in ('vehicles', 'customers', 'sales', 'invoices'):
        abort(404)
    if not can(RESOURCES[resource]['permission']):
        abort(403)
    row = repo().detail(resource, item_id)
    if not row:
        abort(404)
    context = {}
    if resource == 'vehicles':
        context['history'] = repo().history('inventory', 'vehicle_id', item_id)
    if resource == 'customers':
        context['history'] = repo().history('sales', 'customer_id', item_id)
    if resource == 'sales':
        context['invoice'] = repo().entities['invoices'].for_sale(item_id)
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
            sale, invoice = SalesService(repo()).complete(int(request.form.get('customer_id', 0)), int(request.form.get('vehicle_id', 0)), request.form.get('discount', '0'), current_user()['id'])
            return redirect(url_for('web.sale_success', item_id=sale['id']))
        except (ValueError, TypeError) as exc:
            error = str(exc)
    return render_template('sales/create.html', title='New Sale', active='sales', customers=repo().eligible('customers'), vehicles=repo().eligible('vehicles'), error=error)


@bp.get('/sales/<int:item_id>/success')
@require('sales.view')
def sale_success(item_id):
    sale = repo().get('sales', item_id)
    if not sale:
        abort(404)
    invoice = repo().entities['invoices'].for_sale(item_id)
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
    groups = repo().permission_repository.groups()
    if request.method == 'POST':
        try:
            UserService(repo()).permissions(selected, request.form.getlist('permissions'))
        except ValueError as exc:
            flash(str(exc), 'warning')
        else:
            flash('Role permissions updated.', 'success')
        return redirect(url_for('web.roles', role=selected))
    return render_template('roles/index.html', title='Roles & Permissions', active='roles', roles=repo().roles, selected=selected, groups=groups)

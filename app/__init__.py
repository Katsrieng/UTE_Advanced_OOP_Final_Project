import secrets
from flask import Flask, session, render_template, request, url_for, g
from config import Config
from decimal import Decimal
from database.common import settings
from app.repositories.mysql import MySQLRepository
from app.database import DatabaseUnavailable


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'].startswith('replace-with'):
        raise RuntimeError('Set a random SECRET_KEY in the local .env file.')
    app.extensions['repository'] = MySQLRepository(app.config.get('DATABASE') or settings())

    @app.teardown_appcontext
    def close_database(error):
        connection = g.pop('database_connection', None)
        if connection is not None:
            connection.close()

    @app.errorhandler(DatabaseUnavailable)
    def database_unavailable(error):
        g.database_failed = True
        # Standalone page avoids querying current_user again during an outage.
        return render_template('errors/database_unavailable.html', brand=app.config['BRAND']), 503
    from app.routes.web import bp, can, current_user, navigation, vehicle_image_url, photo_service
    app.register_blueprint(bp)

    @app.context_processor
    def shared():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(24)
        unavailable = getattr(g, 'database_failed', False)
        return dict(brand=app.config['BRAND'], user=None if unavailable else current_user(), can=(lambda permission: False) if unavailable else can,
                    navigation=navigation, csrf_token=session['csrf_token'],
                    vehicle_image_url=vehicle_image_url,
                    vehicle_has_photo=lambda vehicle: photo_service().has_photo(vehicle))

    @app.errorhandler(413)
    def upload_too_large(error):
        args = request.view_args or {}
        if request.endpoint == 'web.form' and args.get('resource') == 'vehicles':
            back_url = url_for('web.form', resource='vehicles', item_id=args.get('item_id'))
        else:
            back_url = url_for('web.listing', resource='vehicles')
        return render_template('errors/upload_too_large.html', title='Photo too large', active='vehicles', back_url=back_url), 413

    app.jinja_env.filters['money'] = lambda value: '${:,.2f}'.format(Decimal(str(value or 0)))
    for code in (403, 404, 500):
        def handle(error, code=code):
            return render_template('errors/error.html', code=code, title=str(code), active=''), code
        app.register_error_handler(code, handle)
    return app

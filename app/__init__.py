import secrets
from flask import Flask, session, render_template, request, url_for
from config import Config
from app.repositories.demo import DemoRepository


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.extensions['repository'] = DemoRepository()
    from app.routes.web import bp, can, current_user, navigation, vehicle_image_url, photo_service
    app.register_blueprint(bp)

    @app.context_processor
    def shared():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(24)
        return dict(brand=app.config['BRAND'], user=current_user(), can=can,
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

    app.jinja_env.filters['money'] = lambda value: '${:,.2f}'.format(float(value or 0))
    for code in (403, 404, 500):
        def handle(error, code=code):
            return render_template('errors/error.html', code=code, title=str(code), active=''), code
        app.register_error_handler(code, handle)
    return app

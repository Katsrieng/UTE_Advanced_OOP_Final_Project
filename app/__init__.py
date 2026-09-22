import secrets
from flask import Flask, session, render_template
from config import Config
from app.repositories.demo import DemoRepository


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    app.extensions['repository'] = DemoRepository()
    from app.routes.web import bp, can, current_user, navigation
    app.register_blueprint(bp)

    @app.context_processor
    def shared():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(24)
        return dict(brand=app.config['BRAND'], user=current_user(), can=can,
                    navigation=navigation, csrf_token=session['csrf_token'])

    app.jinja_env.filters['money'] = lambda value: '${:,.2f}'.format(float(value or 0))
    for code in (403, 404, 500):
        def handle(error, code=code):
            return render_template('errors/error.html', code=code, title=str(code), active=''), code
        app.register_error_handler(code, handle)
    return app

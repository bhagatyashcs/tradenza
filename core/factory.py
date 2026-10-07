from pathlib import Path
from flask import Flask

from config import Config
from extensions import db, login_manager, migrate, csrf

# Models
from models import User
from models.trade import Trade
from models.portfolio import Portfolio
from models.equity_history import EquityHistory

# Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.trades import trade_bp
from routes.coach import coach_bp
from routes.digital_twin import digital_twin_bp
from routes.market import market_bp
from routes.settings import settings_bp
from routes.learn import learn_bp
from routes.analytics_routes import analytics_bp
from routes.portfolio import portfolio_bp

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None


def create_app(config_class=Config, test_config=None):

    BASE_DIR = Path(__file__).resolve().parent.parent
    instance_dir = BASE_DIR / "instance"
    instance_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
        instance_path=str(instance_dir),
    )

    if config_class:
        app.config.from_object(config_class)

    if test_config:
        app.config.update(test_config)

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Global Jinja Context Processor & Filters
    @app.context_processor
    def inject_user_currency():
        from flask_login import current_user
        curr = "$"
        try:
            if current_user and current_user.is_authenticated:
                curr = getattr(current_user, "currency", "$") or "$"
        except Exception:
            pass
        return dict(user_curr=curr)

    @app.template_filter("money")
    def money_filter(amount):
        from flask_login import current_user
        curr = "$"
        try:
            if current_user and current_user.is_authenticated:
                curr = getattr(current_user, "currency", "$") or "$"
        except Exception:
            pass
        if amount is None:
            return f"{curr}0.00"
        return f"{curr}{float(amount):.2f}"

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(trade_bp)
    app.register_blueprint(coach_bp)
    app.register_blueprint(digital_twin_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(learn_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(portfolio_bp)

    with app.app_context():
        db.create_all()

    return app
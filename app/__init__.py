from flask import Flask, request, current_app
from docker.errors import DockerException
from app.extensions import logger, client, csrf, security, db, migrate, mail, rq, babel
from config import Config
from redis import Redis
from app.models import User, Role, WebAuthn
from flask_security import (
    SQLAlchemyUserDatastore,
)
from rq import Queue


def get_locale():
    return request.accept_languages.best_match(current_app.config["LANGUAGES"])


def create_app(config_class=Config) -> Flask:
    app: Flask = Flask(__name__)
    app.config.from_object(config_class)
    app.logger = logger
    app.config["REMEMBER_COOKIE_SAMESITE"] = "strict"
    app.config["SESSION_COOKIE_SAMESITE"] = "strict"

    # As of Flask-SQLAlchemy 2.4.0 it is easy to pass in options directly to the
    # underlying engine. This option makes sure that DB connections from the
    # pool are still valid. Important for entire application since
    # many DBaaS options automatically close idle connections.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)

    user_datastore = SQLAlchemyUserDatastore(db, User, Role, WebAuthn)
    csrf.init_app(app)
    security.init_app(app, user_datastore)
    mail.init_app(app)
    rq.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
    app.redis = Redis.from_url(app.config["RQ_REDIS_URL"])
    app.task_queue = Queue("microblog-tasks", connection=app.redis)
    with app.app_context():
        db.create_all()
        # Pull Ubuntu image at startup with better error handling
        try:
            client.images.pull(app.config["DEFAULT_IMAGE"])
            logger.info(
                f"Successfully pulled the default image: {app.config['DEFAULT_IMAGE']}"
            )
        except DockerException as e:
            logger.error(
                f"Failed to pull default image {app.config['DEFAULT_IMAGE']}: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while pulling default image: {e}")

    # Register blueprints after all initializations
    from app.cloudshell import bp as cloudshell_bp

    app.register_blueprint(cloudshell_bp, url_prefix="/cloudshell")

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)

    from app.quickcode import bp as quickcode_bp

    app.register_blueprint(quickcode_bp, url_prefix="/")

    from app.errors import bp as errors_bp

    app.register_blueprint(errors_bp)

    return app

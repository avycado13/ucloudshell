from flask import Flask
from docker.errors import DockerException
from app.extensions import logger, client, csrf, security, db, migrate
from config import Config
from app.models import User, Role, WebAuthn
from flask_security import (
    SQLAlchemyUserDatastore,
)


def create_app(config_class=Config) -> Flask:
    app: Flask = Flask(__name__)
    app.config.from_object(config_class)

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

    with app.app_context():
        db.create_all()
        # Pull Ubuntu image at startup
        try:
            client.images.pull(app.config["DEFAULT_IMAGE"])
        except DockerException as e:
            logger.error(f"Failed to pull default image: {e}")

    from app.cloudshell import bp as cloudshell_bp

    app.register_blueprint(cloudshell_bp)
    return app

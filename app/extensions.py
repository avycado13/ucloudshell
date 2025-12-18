import logging
import docker
from docker.errors import DockerException
from flask_wtf.csrf import CSRFProtect
from flask_security import Security
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_restx import Api
from flask_rq2 import RQ
from flask_babel import Babel, lazy_gettext as _l

# CSRF protection for wtforms
csrf = CSRFProtect()
# Security for user authentication
security = Security()
# db
db: SQLAlchemy = SQLAlchemy()
migrate = Migrate()
# Mail
mail = Mail()
# API w/ Flask-RESTful
api = Api()
# Task queue
rq = RQ()

# Babel for transalation
babel: Babel = Babel()
# Configure logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

# Create Docker client
try:
    client: docker.DockerClient = docker.from_env()
except DockerException as e:
    logger.error(f"Failed to connect to Docker: {e}")
    raise

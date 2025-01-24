import logging
import docker
from docker.errors import DockerException
from flask_wtf.csrf import CSRFProtect
from flask_security import Security
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# CSRF protection for wtforms
csrf = CSRFProtect()
# Security for user authentication
security = Security()
# db
db: SQLAlchemy = SQLAlchemy()
migrate = Migrate()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Docker client
try:
    client = docker.from_env()
except DockerException as e:
    logger.error(f"Failed to connect to Docker: {e}")
    raise

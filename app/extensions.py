import logging
import docker
from docker.errors import DockerException
from flask_wtf.csrf import CSRFProtect

# CSRF protection for wtforms
csrf = CSRFProtect()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Docker client
try:
    client = docker.from_env()
except DockerException as e:
    logger.error(f"Failed to connect to Docker: {e}")
    raise
from flask import Flask
from docker.errors import DockerException
from app.extensions import logger, client, csrf
from config import Config



def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    csrf.init_app(app)
    with app.app_context():
        # Pull Ubuntu image at startup
        try:
            client.images.pull(app.config["DEFAULT_IMAGE"])
        except DockerException as e:
            logger.error(f"Failed to pull default image: {e}")
    
    from app.cloudshell import bp as cloudshell_bp
    app.register_blueprint(cloudshell_bp,prefix=(app.config['CLOUDSHELL_PREFIX'] if app.config['CLOUDSHELL_PREFIX'] else "/cloudshell"))
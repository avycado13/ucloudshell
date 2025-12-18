import secrets
import passlib


class Config:
    """
    Set Flask configuration variables.
    """

    LANGUAGES: list[str] = ["en"]
    RQ_REDIS_URL = "redis://localhost:6379/0"
    DOCKER_HOST: str = "localhost:2376"
    CLOUDSHELL_PREFIX: str = "/cloudshell"
    SECRET_KEY = secrets.token_urlsafe()
    SECURITY_PASSWORD_SALT = str(secrets.SystemRandom().getrandbits(128))
    DEFAULT_IMAGE = "ghcr.io/aoudiamoncef/ubuntu-sshd/ubuntu-sshd:latest"
    # Change for production env
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    DEBUG = True
    # Flask Security
    # WebAuthn
    SECURITY_WEBAUTHN = True
    SECURITY_WAN_ALLOW_AS_FIRST_FACTOR = True
    SECURITY_WAN_ALLOW_AS_MULTI_FACTOR = True
    SECURITY_WAN_ALLOW_AS_VERIFY = True
    # Two Factor
    SECURITY_TWO_FACTOR_ENABLED_METHODS = ["authenticator"]
    SECURITY_TWO_FACTOR = True
    SECURITY_TOTP_SECRETS = {"1": "JBSWY3DPEHPK3PXP"}
    SECURITY_TOTP_ISSUER = "UcloudShell"
    SECURITY_REGISTERABLE = True
    SECURITY_POST_LOGIN_VIEW = "/"
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_USERNAME_ENABLE: bool = True
    # SECURITY_TWO_FACTOR_REQUIRED=True
    SECURITY_CSRF_IGNORE_UNAUTH_ENDPOINTS: bool = False
    TEMPLATES_AUTO_RELOAD = True

    # QuickCode
    QUICKCODE_IMAGE_WHITELIST_ENABLE: bool = False
    QUICKCODE_IMAGE_WHITELIST: list[str] = [""]


class TestingConfig(Config):
    RQ_CONNECTION_CLASS = "fakeredis.FakeStrictRedis"

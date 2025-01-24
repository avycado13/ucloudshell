from app.extensions import db
from flask_security.models import fsqla_v3 as fsqla
from flask_security import UserMixin, RoleMixin, WebAuthnMixin, AsaList
from datetime import datetime

fsqla.FsModels.set_db_info(db)

roles_users = db.Table(
    "roles_users",
    db.Model.metadata,
    db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
    extend_existing=True,
)


class WebAuthn(db.Model, fsqla.FsWebAuthnMixin):
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="webauthn")


class User(db.Model, UserMixin):
    @db.declared_attr
    def webauthn(cls):
        return db.relationship("WebAuthn", back_populates="user", cascade="all, delete")

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean(), nullable=False)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    fs_webauthn_user_handle = db.Column(db.String(64), unique=True, nullable=True)
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    login_count = db.Column(db.Integer)
    tf_totp_secret = db.Column(db.String(255), nullable=True)
    tf_primary_method = db.Column(db.String(255))
    username = db.Column(db.String(255), unique=True)
    balance = db.Column(db.Float, default=0.0)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    # permissions = db.Column(AsaList(db.UnicodeText), nullable=True)


class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    container_id = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", back_populates="containers")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(255), default="running")
    port = db.Column(db.Integer, nullable=False)
    user = db.relationship("User", back_populates="containers")

from typing import Optional
import redis
import rq
from datetime import datetime, timezone
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_security.models import fsqla_v3 as fsqla
from flask_security import UserMixin, RoleMixin
from app.extensions import db

fsqla.FsModels.set_db_info(db)

roles_users = db.Table(
    "roles_users",
    db.Model.metadata,
    db.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
    db.Column("role_id", sa.Integer(), sa.ForeignKey("role.id")),
    extend_existing=True,
)


class WebAuthn(db.Model, fsqla.FsWebAuthnMixin):
    user_id = db.Column(sa.Integer, sa.ForeignKey("user.id", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="webauthn")


class User(db.Model, UserMixin):
    @db.declared_attr
    def webauthn(cls):
        return db.relationship("WebAuthn", back_populates="user", cascade="all, delete")

    id = db.Column(sa.Integer, primary_key=True)
    email = db.Column(sa.String(255), unique=True, nullable=False)
    password = db.Column(sa.String(255))
    active = db.Column(sa.Boolean(), nullable=False)
    fs_uniquifier = db.Column(sa.String(64), unique=True, nullable=False)
    fs_webauthn_user_handle = db.Column(sa.String(64), unique=True, nullable=True)
    last_login_at = db.Column(sa.DateTime())
    current_login_at = db.Column(sa.DateTime())
    last_login_ip = db.Column(sa.String(100))
    current_login_ip = db.Column(sa.String(100))
    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    login_count = db.Column(sa.Integer)
    tf_totp_secret = db.Column(sa.String(255), nullable=True)
    tf_primary_method = db.Column(sa.String(255))
    username = db.Column(sa.String(255), unique=True)
    balance = db.Column(sa.Float, default=0.0)

    # Relationships
    containers = db.relationship("Container", back_populates="user")
    tasks = db.relationship("Task", back_populates="user")

    #  Task Functions
    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue(f"app.{name}", self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name, description=description, user=self)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        query = self.tasks.select().where(Task.complete is False)
        return db.session.scalars(query)

    def get_task_in_progress(self, name):
        query = self.tasks.select().where(Task.name == name, Task.complete is False)
        return db.session.scalar(query)


class Role(db.Model, RoleMixin):
    id = db.Column(sa.Integer, primary_key=True)
    name = db.Column(sa.String(80), unique=True, nullable=False)
    description = db.Column(sa.String(255))


class Container(db.Model):
    id = db.Column(sa.Integer, primary_key=True)
    container_id = db.Column(sa.String(255), unique=True, nullable=False)
    user_id = db.Column(sa.Integer, sa.ForeignKey("user.id"))
    created_at = db.Column(sa.DateTime, default=sa.func.now())
    updated_at = db.Column(sa.DateTime, default=sa.func.now(), onupdate=sa.func.now())
    status = db.Column(sa.String(255), default="running")
    port = db.Column(sa.Integer, nullable=False)

    user = db.relationship("User", back_populates="containers")


class Task(db.Model):
    id: so.Mapped[str] = so.mapped_column(sa.String(36), primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(128), index=True)
    description: so.Mapped[Optional[str]] = so.mapped_column(
        sa.String(128), nullable=True
    )
    user_id: so.Mapped[int] = so.mapped_column(sa.Integer, sa.ForeignKey("user.id"))
    complete: so.Mapped[bool] = so.mapped_column(
        sa.Boolean, default=False, nullable=False
    )

    user: so.Mapped["User"] = so.relationship("User", back_populates="tasks")

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100

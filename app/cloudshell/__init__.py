from flask import Blueprint

bp = Blueprint("cloudshell", __name__)

from app.cloudshell import routes

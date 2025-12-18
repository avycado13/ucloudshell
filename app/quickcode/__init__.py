from flask import Blueprint

bp = Blueprint("quickcode", __name__)

from app.quickcode import routes

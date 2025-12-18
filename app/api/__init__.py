from flask import Blueprint
from flask_restx import Api
from app.cloudshell.api import api as cloudshell_api
from app.quickcode.api import api as quickcode_api

bp = Blueprint("api", __name__)
api = Api(
    bp,
    title="UCloudshell API",
    version="1.0",
    description="The api for the UCloudshell application",
    doc="/docs",
)


api.add_namespace(cloudshell_api, path="/cloudshell")
api.add_namespace(quickcode_api, path="/quickcode")

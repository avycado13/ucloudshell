from flask_security.decorators import auth_token_required, current_user
from flask import jsonify, request
from app.extensions import csrf
from flask_restx import Resource as DefaultResource, Namespace


api = Namespace("quickcode")


class Resource(DefaultResource):
    method_decorators = [auth_token_required, csrf.exempt]


@api.route("/run")
@csrf.exempt
class RunCode(Resource):
    def post(self):
        # Validate required parameters
        required_fields = ["image", "run_command"]
        missing_fields = [
            field for field in required_fields if field not in request.args
        ]

        if missing_fields:
            return jsonify(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"}
            ), 400

        image = request.args.get("image")
        command = request.args.get("run_command")

        current_user.launch_task("quickcode.helpers.run_code")

from flask_security import (
    http_auth_required,
    auth_token_required,
)
from flask import jsonify, request
from app.extensions import client, logger, csrf
from flask_restx import Resource as DefaultResource
from flask_restx import Namespace, fields
from docker.errors import NotFound

api = Namespace("CloudShell", description="CloudShell related operations")


class Resource(DefaultResource):
    method_decorators = [auth_token_required, csrf.exempt]


# @http_auth_required
def get_token():
    pass


class createShell(Resource):
    def post(self):
        body = request.get_json()
        key = body.get("ssh_key")
        try:
            # Create container with SSH server and mapped port
            container = client.containers.create(
                "ubuntu",
                ports={"22/tcp": None},
                command="/bin/bash -c 'tail -f /dev/null'",  # Keep container running
                detach=True,
            )
            container.start()

            # Give container time to initialize
            import time

            time.sleep(2)

            if container.status != "running":
                raise Exception(f"Container {container.id} failed to start.")

            # Install and configure SSH
            commands = [
                "apt-get update",
                "apt-get install -y openssh-server sudo",
                "mkdir -p /root/.ssh",  # Ensure .ssh directory exists
                "ssh-keygen -A",
                f'echo "root:{container.id}" | chpasswd',
                "service ssh start",
            ]

            if key:
                commands.extend(
                    [
                        "chmod 700 /root/.ssh",
                        f'echo "{key}" > /root/.ssh/authorized_keys',
                        "chmod 600 /root/.ssh/authorized_keys",
                    ]
                )

            for cmd in commands:
                result = container.exec_run(
                    cmd, environment={"DEBIAN_FRONTEND": "noninteractive"}
                )
                if result.exit_code != 0:
                    raise Exception(
                        f"Command failed: {cmd} with error: {result.output.decode()}"
                    )

            port = container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]

            return jsonify(
                {
                    "status": "success",
                    "port": port,
                    "container_id": container.id,
                    "user": "root",
                    "password": container.id,
                }
            )

        except Exception as e:
            logger.error(f"Error creating container: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


api.add_resource(createShell, "/create")


class deleteShell(Resource):
    @auth_token_required
    def delete(self, container_id):
        try:
            if not container_id:
                return jsonify(
                    {"status": "error", "message": "No container ID provided"}
                ), 400

            container = client.containers.get(container_id)
            container.stop()
            container.remove()
            return jsonify({"status": "success", "message": "Container deleted"})

        except NotFound:
            return jsonify({"status": "error", "message": "Container not found"}), 404
        except Exception as e:
            logger.error(f"Error deleting container: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500


api.add_resource(deleteShell, "/delete/<string:container_id>")

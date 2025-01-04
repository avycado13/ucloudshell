import docker
from flask import Flask, jsonify, request
from docker.errors import DockerException, NotFound
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Docker client
try:
    client = docker.from_env()
except DockerException as e:
    logger.error(f"Failed to connect to Docker: {e}")
    raise

app = Flask(__name__)

# Pull Ubuntu image at startup
try:
    client.images.pull("ubuntu")
except DockerException as e:
    logger.error(f"Failed to pull Ubuntu image: {e}")

@app.route("/create")
def main():
    try:
        # Create container with SSH server and mapped port
        container = client.containers.create("ubuntu", ports={"22/tcp": None})
        container.start()

        # Install and configure SSH
        commands = [
            "apt-get update",
            "apt-get install -y openssh-server sudo",
            "ssh-keygen -A",
            f'echo "root:{container.id}" | chpasswd',
            "service ssh start"
        ]

        for cmd in commands:
            result = container.exec_run(cmd)
            if result.exit_code != 0:
                raise Exception(f"Command failed: {cmd}")

        port = container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]
        
        return jsonify({
            "status": "success",
            "port": port,
            "container_id": container.id,
            "user": "root",
            "password": container.id
        })

    except Exception as e:
        logger.error(f"Error creating container: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete/<container_id>")
def delete(container_id):
    try:
        if not container_id:
            container_id = request.args.get("id")
        if not container_id:
            return jsonify({"status": "error", "message": "No container ID provided"}), 400

        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        return jsonify({"status": "success", "message": "Container deleted"})

    except NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting container: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/stop/<container_id>")
def stop(container_id):
    try:
        if not container_id:
            container_id = request.args.get("id")
        if not container_id:
            return jsonify({"status": "error", "message": "No container ID provided"}), 400

        container = client.containers.get(container_id)
        container.stop()
        return jsonify({"status": "success", "message": "Container stopped"})

    except NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error stopping container: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/start/<container_id>")
def start(container_id):
    try:
        if not container_id:
            container_id = request.args.get("id")
        if not container_id:
            return jsonify({"status": "error", "message": "No container ID provided"}), 400

        container = client.containers.get(container_id)
        container.start()
        return jsonify({"status": "success", "message": "Container started"})

    except NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error starting container: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
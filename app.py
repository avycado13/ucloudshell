import docker
from flask import Flask, jsonify, request, render_template, url_for
import subprocess
import requests
from docker.errors import DockerException, NotFound
import logging
import socket
from config import Config

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
app.config.from_object(Config)

# Pull Ubuntu image at startup
try:
    client.images.pull("ubuntu")
except DockerException as e:
    logger.error(f"Failed to pull Ubuntu image: {e}")


def ensure_wireguard_container():
    """Ensure the WireGuard container is running."""
    try:
        # Check if the container already exists
        wg_container = client.containers.list(filters={"name": "wireguard"})
        if wg_container:
            logger.info("WireGuard container is already running.")
            return wg_container[0]

        # Create and start the WireGuard container
        wg_container = client.containers.run(
            "linuxserver/wireguard",
            name="wireguard",
            detach=True,
            cap_add=["NET_ADMIN"],
            ports={"51820/udp": 51820},
            environment={
                "TZ": "UTC",
                "SERVERURL": "auto",
                "SERVERPORT": "51820",
                "PEERS": "1",
                "PEERDNS": "1.1.1.1",
            },
        )
        logger.info("WireGuard container started.")
        return wg_container

    except Exception as e:
        logger.error(f"Failed to setup WireGuard container: {e}")
        raise


@app.route("/")
def homepage():
    """Display the homepage with basic information and navigation links."""
    return render_template("index.html")


@app.route("/shell/<container_id>")
def shell(container_id):
    return render_template("shell.html",container_id=container_id,docker_host=app.config['DOCKER_HOST'])

@app.route("/create", methods=["POST"])
def create():
    key = request.form.get("ssh_key")
    try:
        # Create container with SSH server and mapped port
        container = client.containers.create("ubuntu", ports={"22/tcp": None})
        container.start()
        # Wait for the container to be fully initialized
        container.wait()  # Wait for the container to exit (if it does)

        if container.status != 'running':
            raise Exception(f"Container {container.id} failed to start.")


        # Install and configure SSH
        commands = [
            "apt-get update",
            "apt-get install -y openssh-server sudo",
            "ssh-keygen -A",
            f'echo "root:{container.id}" | chpasswd',
            "service ssh start",
        ]
        if key:
            commands.append(f'echo "{key}" >> /root/.ssh/authorized_keys')

        for cmd in commands:
            result = container.exec_run(cmd)
            if result.exit_code != 0:
                raise Exception(f"Command failed: {cmd}")

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


@app.route("/delete/<container_id>", methods=["DELETE"])
def delete(container_id):
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


@app.route("/stop/<container_id>", methods=["POST"])
def stop(container_id):
    try:
        if not container_id:
            return jsonify(
                {"status": "error", "message": "No container ID provided"}
            ), 400

        container = client.containers.get(container_id)
        container.stop()
        return jsonify({"status": "success", "message": "Container stopped"})

    except NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error stopping container: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/start/<container_id>", methods=["POST"])
def start(container_id):
    try:
        if not container_id:
            return jsonify(
                {"status": "error", "message": "No container ID provided"}
            ), 400

        container = client.containers.get(container_id)
        container.start()
        return jsonify({"status": "success", "message": "Container started"})

    except NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error starting container: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/setup_wireguard/<container_id>", methods=["POST"])
def setup_wireguard(container_id):
    try:
        # Ensure WireGuard container is running
        wg_container = ensure_wireguard_container()

        container = client.containers.get(container_id)
        container_ip = container.attrs["NetworkSettings"]["IPAddress"]

        # Get the host machine's IP address
        host_ip = socket.gethostbyname(socket.gethostname())

        # Generate client keys
        client_private_key = (
            subprocess.check_output(["wg", "genkey"]).decode("utf-8").strip()
        )
        client_public_key = (
            subprocess.check_output(
                ["wg", "pubkey"], input=client_private_key.encode("utf-8")
            )
            .decode("utf-8")
            .strip()
        )

        # Server's public key
        server_public_key = (
            subprocess.check_output("cat /etc/wireguard/server_public.key", shell=True)
            .decode("utf-8")
            .strip()
        )

        # Assign an IP to the client (e.g., 10.0.0.2)
        client_ip = f"10.0.0.{int(container_id[:4], 16) % 254 + 2}/24"

        # Update WireGuard server with the new peer dynamically
        subprocess.run(
            ["wg", "set", "wg0", "peer", client_public_key, f"allowed-ips={client_ip}"],
            check=True,
        )

        # Generate client configuration
        wg_client_config = f"""
        [Interface]
        PrivateKey = {client_private_key}
        Address = {client_ip}
        DNS = 1.1.1.1

        [Peer]
        PublicKey = {server_public_key}
        Endpoint = {host_ip}:51820
        AllowedIPs = 0.0.0.0/0
        PersistentKeepalive = 25
        """

        return jsonify({"status": "success", "config": wg_client_config})

    except NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except Exception as e:
        logger.error(f"Error setting up WireGuard: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

from app.cloudshell import bp, api
from flask import render_template, request, jsonify, url_for, redirect, current_app
from app.extensions import client, logger
from flask_security import (
    auth_required,
    http_auth_required,
    auth_token_required,
)
from docker.errors import NotFound
import socket
import subprocess
from app.cloudshell.forms import ContainerForm
from app.cloudshell.helpers import ensure_wireguard_container, create


@bp.route("/", methods=["GET", "POST"])
@auth_required
def index():
    """Display the homepage with basic information and navigation links."""
    form = ContainerForm()
    if form.validate_on_submit():
        if form.shell_submit.data:
            return redirect(
                url_for("cloudshell.shell", container_id=form.container_id.data)
            )
        elif form.delete_submit.data:
            return redirect(
                url_for("cloudshell.delete", container_id=form.container_id.data)
            )
        elif form.stop_submit.data:
            return redirect(
                url_for("cloudshell.stop", container_id=form.container_id.data)
            )
        elif form.start_submit.data:
            return redirect(
                url_for("cloudshell.start", container_id=form.container_id.data)
            )
        elif form.wireguard_submit.data:
            return redirect(
                url_for(
                    "cloudshell.setup_wireguard", container_id=form.container_id.data
                )
            )
    return render_template("cloudshell/index.html", form=form)


@bp.route("/shell/<int:container_id>")
@auth_required
def shell(container_id):
    return render_template(
        "cloudshell/shell.html",
        container_id=container_id,
        docker_host=current_app.config["DOCKER_HOST"],
    )


@auth_required
@bp.route("/create", methods=["POST"])
def create():
    job = create()
    container_info = job
    return container_info


@bp.route("/stop/<container_id>", methods=["POST"])
@auth_required
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


@bp.route("/start/<container_id>", methods=["POST"])
@auth_required
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


@auth_required
@bp.route("/setup_wireguard/<string:container_id>", methods=["POST"])
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

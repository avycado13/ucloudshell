from app.extensions import logger, client
from docker.errors import NotFound
from docker.models.containers import Container, ExecResult
from typing import Optional, Union, Dict
from rq import Retry


def ensure_wireguard_container() -> Union[Container, None]:
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


def create(
    key: Optional[str], interval: int
) -> Union[Dict[str, Union[str, int]], Retry]:
    """Create a new container with an SSH server and configure it.

    Args:
        key (Optional[str]): SSH public key for authentication.

    Returns:
        Dict[str, Union[str, int]]: Information about the created container.
    """
    try:
        # Create container with SSH server and mapped port
        container: Container = client.containers.create(
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
            result: ExecResult = container.exec_run(
                cmd, environment={"DEBIAN_FRONTEND": "noninteractive"}
            )
            if result.exit_code != 0:
                raise Exception(
                    f"Command failed: {cmd} with error: {result.output.decode()}"
                )

        # Extract the mapped SSH port
        port = container.attrs["NetworkSettings"]["Ports"]["22/tcp"][0]["HostPort"]

        return {
            "status": "success",
            "port": int(port),
            "container_id": container.id or "",
            "user": "root",
            "password": container.id or "",
        }

    except Exception as e:
        logger.error(f"Error creating container: {e}")
        return Retry(max=3, interval=interval)
        return {"status": "error", "message": str(e)}

from app.extensions import logger, client


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

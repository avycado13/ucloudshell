from flask import current_app, jsonify
from app.extensions import client, logger


def run(image, command):
    # Validate image against blacklist/whitelist
    if image in current_app.config.get("QUICKCODE_IMAGE_BLACKLIST", []):
        return jsonify({"error": "This image is not allowed"}), 403

    if current_app.config.get(
        "QUICKCODE_IMAGE_WHITELIST_ENABLE", False
    ) and image not in current_app.config.get("QUICKCODE_IMAGE_WHITELIST", []):
        return jsonify({"error": "This image is not allowed"}), 403
    try:
        client.images.pull(image)  # Pull the image
    except Exception as e:
        logger.error(f"Error pull QuickCode container: {str(e)}")
        return jsonify({"error": "Failed to run Code", "details": str(e)}), 500
    try:
        # Create and start the container safely
        container = client.containers.run(image, command.split())

        return jsonify({"message": "Code Ran", "result": container}), 200
    except Exception as e:
        logger.error(f"Error running QuickCode container: {str(e)}")
        return jsonify({"error": "Failed to run Code", "details": str(e)}), 500

#!/bin/bash
set -eo pipefail

# Environment variables
IMAGE_TAG=${IMAGE_TAG:-"latest"}
REPO_URL="https://github.com/aoudiamoncef/ubuntu-sshd"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Clone repository
if [ ! -d "ubuntu-sshd" ]; then
    echo "Cloning repository..."
    git clone "$REPO_URL" || {
        echo "Failed to clone repository"
        exit 1
    }
fi

# Build Docker image
cd ubuntu-sshd
echo "Building Docker image..."
docker build -t "my-ubuntu-sshd:${IMAGE_TAG}" . || {
    echo "Failed to build Docker image"
    exit 1
}

# Verify image was created
docker image inspect "my-ubuntu-sshd:${IMAGE_TAG}" > /dev/null 2>&1 || {
    echo "Failed to verify Docker image"
    exit 1
}

echo "Successfully built my-ubuntu-sshd:${IMAGE_TAG}"
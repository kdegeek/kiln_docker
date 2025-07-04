#!/bin/bash

# Deployment script for Kiln AI Docker container with root privileges

set -e

echo "=== Kiln AI Docker Deployment Script ==="

# Stop and remove existing container
echo "Stopping existing containers..."
sudo docker stop $(sudo docker ps -q --filter ancestor=kiln-ai-root) 2>/dev/null || true
sudo docker rm $(sudo docker ps -aq --filter ancestor=kiln-ai-root) 2>/dev/null || true

# Build the image
echo "Building Kiln AI Docker image..."
sudo docker build -t kiln-ai-root .

# Configuration
KILN_HOST=${KILN_HOST:-0.0.0.0}
KILN_PORT=${KILN_PORT:-8757}
KILN_LOG_LEVEL=${KILN_LOG_LEVEL:-info}

# Run the container with full privileges
echo "Starting Kiln AI container with root privileges..."
echo "Host: $KILN_HOST, Port: $KILN_PORT"
CONTAINER_ID=$(sudo docker run --privileged \
    --cap-add=SYS_ADMIN \
    --cap-add=NET_ADMIN \
    --cap-add=SYS_PTRACE \
    --cap-add=DAC_OVERRIDE \
    --cap-add=NET_RAW \
    --cap-add=SYS_MODULE \
    -p $KILN_PORT:$KILN_PORT \
    -e KILN_HOST=$KILN_HOST \
    -e KILN_PORT=$KILN_PORT \
    -e KILN_LOG_LEVEL=$KILN_LOG_LEVEL \
    -d kiln-ai-root)

echo "Container started with ID: $CONTAINER_ID"

# Wait for startup
echo "Waiting for server to start..."
sleep 5

# Test root access
echo "Testing root access..."
sudo docker exec -it $CONTAINER_ID /app/test_root.sh

# Test web server
echo "Testing web server..."
curl -s http://localhost:8757/cors-test | head -1

echo ""
echo "=== Deployment Complete ==="
echo "Container ID: $CONTAINER_ID"
echo "Web Interface: http://$KILN_HOST:$KILN_PORT"
echo "CORS Test: http://$KILN_HOST:$KILN_PORT/cors-test"
echo ""
echo "To access container shell:"
echo "sudo docker exec -it $CONTAINER_ID /bin/bash"
echo ""
echo "To view logs:"
echo "sudo docker logs $CONTAINER_ID"
echo ""
echo "To stop container:"
echo "sudo docker stop $CONTAINER_ID"
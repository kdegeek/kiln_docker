#!/bin/bash

# Script to rebuild the web UI after making changes

echo "=== Rebuilding Kiln Web UI ==="
cd /home/kdegeek/PycharmProjects/kiln_docker/app/web_ui

echo "Installing dependencies..."
npm ci

echo "Building web UI..."
npm run build

echo "Build complete! The updated web UI is now in build/"
ls -la build/
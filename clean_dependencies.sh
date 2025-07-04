#!/bin/bash

# Clean up web UI dependencies after removing PostHog

echo "=== Cleaning up Web UI Dependencies ==="
cd /home/kdegeek/PycharmProjects/kiln_docker/app/web_ui

echo "Removing package-lock.json and node_modules..."
rm -f package-lock.json
rm -rf node_modules

echo "Reinstalling dependencies..."
npm install

echo "Building clean web UI..."
npm run build

echo "Clean build complete!"
#!/bin/bash

# Start script for Kiln AI server with proper Python path

echo "=== Starting Kiln AI Server ==="
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Python version: $(python --version)"

# Verify root access
echo "=== Root Access Verification ==="
echo "Current user: $(whoami)"
echo "User ID: $(id)"
echo "Groups: $(groups)"
echo "Root privileges: $(sudo -n whoami 2>/dev/null || echo 'Available via sudo')"

# Show directory structure for debugging
echo "=== Directory structure ==="
ls -la /app/

echo "=== App directory ==="
ls -la /app/app/

echo "=== Desktop directory ==="
ls -la /app/app/desktop/

# Add current directory to Python path
export PYTHONPATH="/app:$PYTHONPATH"

echo "=== Updated Python path ==="
echo $PYTHONPATH

# Test Python import
echo "=== Testing Python import ==="
python -c "import sys; print('Python sys.path:'); [print(p) for p in sys.path]"

# Try to import the app module
echo "=== Testing app module import ==="
python -c "try:
    import app
    print('✓ app module imported successfully')
except ImportError as e:
    print('✗ Failed to import app module:', e)"

# Try to import the desktop server module
echo "=== Testing desktop server import ==="
python -c "try:
    from app.desktop.desktop_server import make_app
    print('✓ desktop_server module imported successfully')
except ImportError as e:
    print('✗ Failed to import desktop_server module:', e)"

# Start the server
echo "=== Starting server ==="
cd /app
exec uv run python app/desktop/server_runner.py
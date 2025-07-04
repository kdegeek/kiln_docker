#!/usr/bin/env python3
"""
Simple server runner for Docker containers.
Runs the Kiln server without GUI components.
"""

import os
import ssl

# Set SSL environment variables before any imports
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["SSL_VERIFY"] = "0"

# Disable SSL verification globally
ssl._create_default_https_context = ssl._create_unverified_context

# Monkey patch httpx to disable SSL verification
import httpx

original_init = httpx.Client.__init__


def patched_init(self, *args, **kwargs):
    kwargs["verify"] = False
    return original_init(self, *args, **kwargs)


httpx.Client.__init__ = patched_init

import uvicorn

import sys
print(f"Python path: {sys.path}")
print(f"Current working directory: {os.getcwd()}")

try:
    from app.desktop.desktop_server import make_app
    print("✓ Successfully imported from app.desktop.desktop_server")
except ImportError as e:
    print(f"✗ Failed to import from app.desktop.desktop_server: {e}")
    try:
        # Fallback for when running from different paths
        from desktop_server import make_app
        print("✓ Successfully imported from desktop_server")
    except ImportError as e2:
        print(f"✗ Failed to import from desktop_server: {e2}")
        # Try adding the current directory to sys.path
        sys.path.insert(0, '/app')
        try:
            from app.desktop.desktop_server import make_app
            print("✓ Successfully imported after adding /app to sys.path")
        except ImportError as e3:
            print(f"✗ Final import attempt failed: {e3}")
            print("Available modules in /app:")
            import os
            for root, dirs, files in os.walk('/app'):
                for file in files:
                    if file.endswith('.py'):
                        print(f"  {os.path.join(root, file)}")
            raise


def main():
    """Main entry point for the containerized server."""
    # Set default environment variables for container deployment
    os.environ.setdefault("KILN_SKIP_REMOTE_MODEL_LIST", "false")

    # Create the FastAPI app
    app = make_app()

    # Get configuration from environment
    host = os.environ.get("KILN_HOST", "0.0.0.0")
    port = int(os.environ.get("KILN_PORT", "8757"))
    log_level = os.environ.get("KILN_LOG_LEVEL", "info")

    # Run the server
    uvicorn.run(app, host=host, port=port, log_level=log_level, access_log=True)


if __name__ == "__main__":
    main()

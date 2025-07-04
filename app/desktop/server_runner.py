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
    kwargs['verify'] = False
    return original_init(self, *args, **kwargs)

httpx.Client.__init__ = patched_init

import uvicorn
from app.desktop.desktop_server import make_app

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
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()
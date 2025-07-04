import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .custom_errors import connect_custom_errors
from .project_api import connect_project_api
from .prompt_api import connect_prompt_api
from .run_api import connect_run_api
from .task_api import connect_task_api


def make_app(lifespan=None):
    app = FastAPI(
        title="Kiln AI Server",
        summary="A REST API for the Kiln AI datamodel.",
        description="Learn more about Kiln AI at https://github.com/kiln-ai/kiln",
        lifespan=lifespan,
    )

    @app.get("/ping")
    def ping():
        return "pong"

    @app.get("/cors-test")
    def cors_test():
        return {
            "message": "CORS test endpoint", 
            "status": "success",
            "allowed_origins": allowed_origins,
            "server_info": "Docker container with CORS enabled"
        }

    connect_project_api(app)
    connect_task_api(app)
    connect_prompt_api(app)
    connect_run_api(app)
    connect_custom_errors(app)

    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        # Docker container origins
        "http://localhost:8757",
        "http://127.0.0.1:8757",
        "https://localhost:8757",
        "https://127.0.0.1:8757",
        "http://0.0.0.0:8757",
        # Allow all origins in Docker environment
        "*"
    ]

    # Enhanced CORS configuration for Docker environment
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,  # 24 hours
    )

    return app


app = make_app()
if __name__ == "__main__":
    auto_reload = os.environ.get("AUTO_RELOAD", "").lower() in ("true", "1", "yes")
    uvicorn.run(
        "kiln_server.server:app",
        host="127.0.0.1",
        port=8757,
        reload=auto_reload,
    )

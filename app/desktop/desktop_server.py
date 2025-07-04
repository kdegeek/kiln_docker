import asyncio
import contextlib
import os
import threading
import time
from contextlib import asynccontextmanager

import kiln_ai.datamodel.strict_mode as datamodel_strict_mode
import kiln_server.server as kiln_server
import uvicorn
from fastapi import FastAPI
from kiln_ai.adapters.remote_config import load_remote_models
from kiln_ai.utils.logging import setup_litellm_logging

from app.desktop.log_config import log_config
from app.desktop.studio_server.data_gen_api import connect_data_gen_api
from app.desktop.studio_server.eval_api import connect_evals_api
from app.desktop.studio_server.finetune_api import connect_fine_tune_api
from app.desktop.studio_server.prompt_api import connect_prompt_api
from app.desktop.studio_server.provider_api import connect_provider_api
from app.desktop.studio_server.repair_api import connect_repair_api
from app.desktop.studio_server.settings_api import connect_settings
from app.desktop.studio_server.webhost import connect_webhost

# Loads github pages hosted JSON config.
# You can see public config build logs here: https://github.com/Kiln-AI/remote_config/actions/workflows/publish_remote_config.yml
# URL is Cloudflare proxy to Github Pages: https://kiln-ai.github.io/remote_config/kiln_config.json
REMOTE_MODEL_LIST_URL = "https://remote-config.getkiln.ai/kiln_config.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # debug event loop, warning on hangs
    should_debug = os.environ.get("DEBUG_EVENT_LOOP", "false") == "true"
    if should_debug:
        loop = asyncio.get_event_loop()
        loop.set_debug(True)

    # Set datamodel strict mode on startup
    original_strict_mode = datamodel_strict_mode.strict_mode()
    datamodel_strict_mode.set_strict_mode(True)
    yield
    # Reset datamodel strict mode on shutdown
    datamodel_strict_mode.set_strict_mode(original_strict_mode)


def make_app():
    setup_litellm_logging()

    load_remote_models(REMOTE_MODEL_LIST_URL)

    app = kiln_server.make_app(lifespan=lifespan)
    connect_provider_api(app)
    connect_prompt_api(app)
    connect_repair_api(app)
    connect_settings(app)
    connect_data_gen_api(app)
    connect_fine_tune_api(app)
    connect_evals_api(app)

    # Important: webhost must be last, it handles all other URLs
    connect_webhost(app)
    return app


def server_config(port=8757):
    # Use 0.0.0.0 for Docker containers to allow external connections
    host = os.environ.get("KILN_HOST", "0.0.0.0")
    return uvicorn.Config(
        make_app(),
        host=host,
        port=port,
        use_colors=False,
        log_config=log_config(),
    )


class ThreadedServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        self.stopped = False
        thread = threading.Thread(target=self.run_safe, daemon=True)
        thread.start()
        try:
            while not self.started and not self.stopped:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()

    def run_safe(self):
        try:
            self.run()
        finally:
            self.stopped = True

    def running(self):
        return self.started and not self.stopped


def run_studio():
    host = os.environ.get("KILN_HOST", "0.0.0.0")
    uvicorn.run(kiln_server.app, host=host, port=8757, log_level="warning")


def run_studio_thread():
    thread = threading.Thread(target=run_studio)
    thread.start()
    return thread

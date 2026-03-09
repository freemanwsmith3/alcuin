from __future__ import annotations

import json
import logging
import logging.config
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.api.routes import router
from app.middleware.auth import AuthMiddleware
from app.middleware.observability import ObservabilityMiddleware


# ---------------------------------------------------------------------------
# Structured JSON logging
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    _EXTRA_KEYS = (
        "path", "status", "provider", "model",
        "stream", "elapsed_ms", "input_tokens", "output_tokens",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in self._EXTRA_KEYS:
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": _JsonFormatter},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
})


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Gateway",
    description="Multi-provider LLM gateway",
    version="0.1.0",
)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(AuthMiddleware)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

# Serve the chat UI — API routes registered above take priority over the mount.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

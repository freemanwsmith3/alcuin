from __future__ import annotations

import json
import logging
import logging.config
import os
import time

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.keyvault import load_secrets
load_secrets()

import redis.asyncio as aioredis

from app.api.routes import router
from app.api.rag_routes import router as rag_router
from app.api.graph_routes import router as graph_router
from app.api.camera_routes import router as camera_router
from app.auth.routes import router as auth_router
from app.middleware.auth import AuthMiddleware
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.rate_limit import RateLimitMiddleware


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

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379"),
        decode_responses=False,
    )
    yield
    await app.state.redis.aclose()


app = FastAPI(
    title="Carina's Company",
    description="Multi-provider LLM gateway",
    version="0.1.0",
    lifespan=lifespan,
)

_rpm = int(os.environ.get("RATE_LIMIT_RPM", 60))

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=_rpm)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(camera_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

# Serve the chat UI — API routes registered above take priority over the mount.
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

from __future__ import annotations

import os
import secrets
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class AuthMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key header on all /api/* requests.

    Requests to the static frontend and OpenAPI docs are always allowed through.
    Returns 401 if the key is missing or wrong, 403 if GATEWAY_API_KEY is not set.
    If GATEWAY_API_KEY is not configured, all /api/* requests are blocked.
    """

    _SKIP_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/api/v1/auth", "/api/v1/camera/live")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path

        # Pass through CORS preflight, docs, and non-API paths
        if request.method == "OPTIONS" or not path.startswith("/api/") or any(
            path.startswith(p) for p in self._SKIP_PREFIXES
        ):
            return await call_next(request)

        # Allow requests carrying a JWT Bearer token — the route-level
        # get_current_user dependency handles JWT verification.
        if request.headers.get("Authorization", "").startswith("Bearer "):
            return await call_next(request)

        expected = os.environ.get("GATEWAY_API_KEY", "")
        if not expected:
            return JSONResponse(
                {"detail": "server misconfigured: GATEWAY_API_KEY not set"},
                status_code=403,
            )

        provided = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided, expected):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)

        return await call_next(request)

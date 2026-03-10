from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter keyed by client IP.

    Counts requests in a rolling 60-second window per IP. Only applies to
    /api/* paths — the frontend, health check, and docs are unrestricted.
    Returns 429 with a Retry-After header when the limit is exceeded.
    """

    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self._rpm = requests_per_minute
        self._window = 60.0
        self._clients: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        timestamps = self._clients[ip]

        # Evict timestamps outside the sliding window
        while timestamps and timestamps[0] < now - self._window:
            timestamps.popleft()

        if len(timestamps) >= self._rpm:
            retry_after = int(self._window - (now - timestamps[0])) + 1
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        timestamps.append(now)
        return await call_next(request)

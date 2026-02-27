from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("llm_gateway.observability")


def _provider_from_model(model: str) -> str:
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        return "openai"
    return "anthropic"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Log every LLM gateway request with timing, token counts, and provider info.

    For streaming responses, token counts aren't available in SSE chunks, so only
    timing and model/provider info are logged. For non-streaming responses, the
    response body is buffered to extract token counts from the JSON payload.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not request.url.path.startswith("/api/v1/chat"):
            return await call_next(request)

        # Read body early so we can extract model info before the route handles it.
        # Starlette caches request.body() so the route can still read it normally.
        body_bytes = await request.body()

        model: str | None = None
        provider: str | None = None
        try:
            body = json.loads(body_bytes)
            model = body.get("config", {}).get("model")
            if model:
                provider = _provider_from_model(model)
        except Exception:
            pass

        is_stream = request.url.path.endswith("/stream")
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        if is_stream:
            # Don't consume the streaming body — log what we know from the request.
            logger.info(
                "llm_request",
                extra={
                    "path": request.url.path,
                    "status": response.status_code,
                    "provider": provider,
                    "model": model,
                    "stream": True,
                    "elapsed_ms": elapsed_ms,
                    "input_tokens": None,
                    "output_tokens": None,
                },
            )
            return response

        # Non-streaming: buffer response body to extract token counts, then re-emit.
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
        response_body = b"".join(chunks)

        input_tokens: int | None = None
        output_tokens: int | None = None
        try:
            resp_json = json.loads(response_body)
            resp_data = resp_json.get("response", {})
            input_tokens = resp_data.get("input_tokens")
            output_tokens = resp_data.get("output_tokens")
            if not model:
                model = resp_data.get("model")
            if not provider:
                provider = resp_data.get("provider")
        except Exception:
            pass

        logger.info(
            "llm_request",
            extra={
                "path": request.url.path,
                "status": response.status_code,
                "provider": provider,
                "model": model,
                "stream": False,
                "elapsed_ms": elapsed_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )

        # Rebuild response — drop content-length so Starlette recalculates it.
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )

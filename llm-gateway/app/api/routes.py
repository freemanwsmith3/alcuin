import json
from functools import lru_cache
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, ChatResponse
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider

router = APIRouter()


@lru_cache
def get_provider() -> LLMProvider:
    """Single provider instance reused across requests."""
    return AnthropicProvider()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    provider: LLMProvider = Depends(get_provider),
) -> ChatResponse:
    """Return a complete response in one shot."""
    try:
        response = await provider.complete(request.messages, request.config)
        return ChatResponse(response=response, session_id=request.session_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    provider: LLMProvider = Depends(get_provider),
) -> StreamingResponse:
    """Stream response chunks as Server-Sent Events."""

    async def generate() -> AsyncIterator[str]:
        try:
            async for chunk in provider.stream(request.messages, request.config):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

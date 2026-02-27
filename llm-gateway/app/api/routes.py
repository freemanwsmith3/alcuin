import json
from functools import lru_cache
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.conversation.store import ConversationStore, InMemoryConversationStore, new_session_id
from app.models.schemas import ChatRequest, ChatResponse, Message
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai import OpenAIProvider

router = APIRouter()


@lru_cache
def get_anthropic() -> LLMProvider:
    return AnthropicProvider()


@lru_cache
def get_openai() -> LLMProvider:
    return OpenAIProvider()


def get_provider_for_model(model: str) -> LLMProvider:
    """Pick the right provider based on the model name."""
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        return get_openai()
    return get_anthropic()


@lru_cache
def get_store() -> ConversationStore:
    """Single store instance reused across requests."""
    return InMemoryConversationStore()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: ConversationStore = Depends(get_store),
) -> ChatResponse:
    """Return a complete response in one shot."""
    session_id = request.session_id or new_session_id()
    provider = get_provider_for_model(request.config.model)

    try:
        history = await store.get(session_id)
        messages = history + request.messages

        response = await provider.complete(messages, request.config)

        await store.append(session_id, request.messages)
        await store.append(session_id, [Message(role="assistant", content=response.content)])

        return ChatResponse(response=response, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    store: ConversationStore = Depends(get_store),
) -> StreamingResponse:
    """Stream response chunks as Server-Sent Events."""
    session_id = request.session_id or new_session_id()
    provider = get_provider_for_model(request.config.model)
    history = await store.get(session_id)
    messages = history + request.messages

    async def generate() -> AsyncIterator[str]:
        collected = []
        try:
            async for chunk in provider.stream(messages, request.config):
                collected.append(chunk)
                yield f"data: {json.dumps({'text': chunk, 'session_id': session_id})}\n\n"

            full_response = "".join(collected)
            await store.append(session_id, request.messages)
            await store.append(session_id, [Message(role="assistant", content=full_response)])
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

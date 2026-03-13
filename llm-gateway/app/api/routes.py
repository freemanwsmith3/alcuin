import json
import logging
import os
from functools import lru_cache
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.conversation.store import ConversationStore, InMemoryConversationStore, new_session_id
from app.conversation.usage_store import UsageStore
from app.models.schemas import ChatRequest, ChatResponse, Message
from app.providers.anthropic import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai import OpenAIProvider
from app.providers.resilient import ResilientProvider
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)

_RAG_SYSTEM_PREFIX = """\
You are a helpful assistant. Answer the user's question using ONLY the context \
provided below. If the answer is not in the context, say so clearly.

--- CONTEXT ---
{context}
--- END CONTEXT ---

"""

router = APIRouter()


@lru_cache
def get_anthropic() -> LLMProvider:
    return AnthropicProvider()


@lru_cache
def get_openai() -> LLMProvider:
    return OpenAIProvider()


def get_provider_for_model(model: str) -> LLMProvider:
    """Return a ResilientProvider wrapping the appropriate primary provider."""
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        return ResilientProvider(primary=get_openai(), fallback=get_anthropic(), model=model)
    return ResilientProvider(primary=get_anthropic(), fallback=get_openai(), model=model)


@lru_cache
def get_store() -> ConversationStore:
    """Return RedisConversationStore if REDIS_URL is set, else in-memory."""
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        from app.conversation.redis_store import RedisConversationStore
        ttl = int(os.environ.get("SESSION_TTL_SECONDS", 86400))
        return RedisConversationStore(redis_url, ttl=ttl)
    return InMemoryConversationStore()


@lru_cache
def get_usage_store() -> UsageStore:
    return UsageStore()


async def _inject_rag_context(messages: list[Message], document_ids: list[str]) -> list[Message]:
    """Retrieve relevant chunks and prepend them as a system message."""
    # Use the last user message as the query
    user_query = next(
        (m.content for m in reversed(messages) if m.role == "user"), ""
    )
    if not user_query:
        return messages

    chunks = await retrieve(query=user_query, top_k=5, document_ids=document_ids)
    if not chunks:
        logger.info("rag_no_results", extra={"query": user_query[:100]})
        return messages

    context = "\n\n".join(
        f"[{c.filename} chunk {c.chunk_index} | score {c.score:.2f}]\n{c.content}"
        for c in chunks
    )
    logger.info(
        "rag_context_injected",
        extra={"chunks": len(chunks), "query": user_query[:100]},
    )

    system_message = Message(
        role="system",
        content=_RAG_SYSTEM_PREFIX.format(context=context),
    )
    # Prepend system message, preserving any existing messages
    return [system_message] + messages


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    store: ConversationStore = Depends(get_store),
    usage: UsageStore = Depends(get_usage_store),
) -> ChatResponse:
    """Return a complete response in one shot."""
    session_id = request.session_id or new_session_id()
    provider = get_provider_for_model(request.config.model)

    try:
        history = await store.get(session_id)
        messages = history + request.messages

        if request.document_ids:
            messages = await _inject_rag_context(messages, request.document_ids)

        response = await provider.complete(messages, request.config)

        await store.append(session_id, request.messages)
        await store.append(session_id, [Message(role="assistant", content=response.content)])

        if response.input_tokens is not None and response.output_tokens is not None:
            usage.record(
                session_id=session_id,
                model=response.model,
                provider=response.provider,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

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

    if request.document_ids:
        messages = await _inject_rag_context(messages, request.document_ids)

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


@router.get("/usage")
async def usage_summary(usage: UsageStore = Depends(get_usage_store)) -> dict:
    """Return aggregate token usage and cost across all sessions."""
    totals = usage.get_all_sessions()
    return {
        "grand_total": usage.grand_total(),
        "sessions": [
            {
                "session_id": t.session_id,
                "requests": t.request_count,
                "input_tokens": t.input_tokens,
                "output_tokens": t.output_tokens,
                "cost_usd": round(t.cost_usd, 6),
            }
            for t in totals
        ],
    }


@router.get("/usage/{session_id}")
async def usage_by_session(
    session_id: str,
    usage: UsageStore = Depends(get_usage_store),
) -> dict:
    """Return token usage and cost for a specific session."""
    t = usage.get_session(session_id)
    if t is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "session_id": t.session_id,
        "requests": t.request_count,
        "input_tokens": t.input_tokens,
        "output_tokens": t.output_tokens,
        "cost_usd": round(t.cost_usd, 6),
    }

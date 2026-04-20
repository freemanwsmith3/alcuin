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
from app.auth.dependencies import CurrentUser, get_optional_user

logger = logging.getLogger(__name__)

_RAG_SYSTEM_PREFIX = """\
You are a helpful assistant. Answer the user's question using ONLY the context \
provided below. If the answer is not in the context, say so clearly.

--- CONTEXT ---
{context}
--- END CONTEXT ---

"""

_GRAPH_SYSTEM_PREFIX = """\
You are a helpful assistant. The following is relevant information retrieved \
from a knowledge graph. Use it to answer the user's question.

--- GRAPH CONTEXT ---
{context}
--- END GRAPH CONTEXT ---

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
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> ChatResponse:
    """Return a complete response in one shot."""
    session_id = request.session_id or new_session_id()
    provider = get_provider_for_model(request.config.model)

    try:
        history = await store.get(session_id)
        messages = history + request.messages

        if request.document_ids:
            messages = await _inject_rag_context(messages, request.document_ids)

        if request.use_graph and current_user:
            messages = _inject_graph_context(messages, current_user.id)

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


def _inject_graph_context(messages: list[Message], user_id: str) -> list[Message]:
    from app.graph import generator, querier
    schema = generator.load(user_id)
    if schema is None:
        logger.warning("graph_inject_no_schema", extra={"user_id": user_id})
        return messages

    user_query = next((m.content for m in reversed(messages) if m.role == "user"), "")
    if not user_query:
        return messages

    answer = querier.query(user_query, user_id, schema)
    logger.info("graph_inject", extra={"user_id": user_id, "has_answer": bool(answer)})

    table_names = [t["name"] for t in schema.get("tables", [])]
    schema_summary = f"Tables: {', '.join(table_names)}" if table_names else "no tables"

    if answer:
        context = answer
    else:
        context = f"Query returned no results. The graph contains: {schema_summary}."

    return [Message(role="system", content=_GRAPH_SYSTEM_PREFIX.format(context=context))] + messages


async def _agentic_stream(
    messages: list[Message],
    request: "ChatRequest",
    session_id: str,
    store: "ConversationStore",
    user_id: str,
) -> AsyncIterator[str]:
    """Agentic streaming loop: handles tool calls inline and yields SSE events."""
    from app.graph import tools as graph_tools

    provider: AnthropicProvider = get_anthropic()  # type: ignore[assignment]
    system, api_messages = provider._translate_messages(messages)

    _TOOLS_SYSTEM = (
        "\n\nYou have two tools: generate_graph_data and build_knowledge_graph."
        "\n\nRULE: When a user asks to create, build, or generate a knowledge graph or any dataset, "
        "you MUST call generate_graph_data followed immediately by build_knowledge_graph. "
        "NEVER write out the data as text, JSON, or diagrams — always use the tools instead."
        "\n\nUI CONTEXT: After build_knowledge_graph succeeds, the data automatically appears in the "
        "app's Graph tab (interactive table + visual network graph). Tell the user to check it there."
        "\n\nAfter building, answer questions about the data directly in chat."
    )
    if system:
        system = system + _TOOLS_SYSTEM
    else:
        system = _TOOLS_SYSTEM.strip()

    text_parts: list[str] = []

    while True:
        # Force tool use on the first turn if the user is asking for graph creation
        _GRAPH_KEYWORDS = ("knowledge graph", "create a graph", "build a graph",
                           "generate data", "make a graph", "graph of", "graph with")
        last_user = next((m["content"] for m in reversed(api_messages) if m["role"] == "user"), "")
        force_tools = (
            len(api_messages) <= 2  # first or second turn
            and isinstance(last_user, str)
            and any(kw in last_user.lower() for kw in _GRAPH_KEYWORDS)
        )

        kwargs: dict = {
            "model": request.config.model,
            "max_tokens": request.config.max_tokens or 2048,
            "messages": api_messages,
            "tools": graph_tools.TOOLS,
            "tool_choice": {"type": "any"} if force_tools else {"type": "auto"},
        }
        if system:
            kwargs["system"] = system
        if request.config.temperature is not None:
            kwargs["temperature"] = request.config.temperature

        async with provider._client.messages.stream(**kwargs) as stream:
            turn_text: list[str] = []
            async for chunk in stream.text_stream:
                turn_text.append(chunk)
                yield f"data: {json.dumps({'text': chunk, 'session_id': session_id})}\n\n"
            final = await stream.get_final_message()

        if turn_text:
            text_parts.append("".join(turn_text))

        if final.stop_reason != "tool_use":
            full_response = "".join(text_parts)
            await store.append(session_id, request.messages)
            await store.append(session_id, [Message(role="assistant", content=full_response)])
            break

        # Serialize assistant turn (text + tool_use blocks)
        assistant_content = []
        for block in final.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        api_messages.append({"role": "assistant", "content": assistant_content})

        # Execute each tool and collect results
        tool_results = []
        for block in final.content:
            if block.type != "tool_use":
                continue
            yield f"data: {json.dumps({'tool_use': {'name': block.name, 'input': block.input}})}\n\n"
            result = graph_tools.execute(block.name, block.input, user_id)
            logger.info("tool_executed", extra={"tool": block.name, "success": result.get("success")})
            yield f"data: {json.dumps({'tool_result': {'name': block.name, 'result': result}})}\n\n"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps({k: v for k, v in result.items() if k not in ("schema", "graph")}),
            })

        api_messages.append({"role": "user", "content": tool_results})


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    store: ConversationStore = Depends(get_store),
    current_user: CurrentUser | None = Depends(get_optional_user),
) -> StreamingResponse:
    """Stream response chunks as Server-Sent Events."""
    session_id = request.session_id or new_session_id()
    history = await store.get(session_id)
    messages = history + request.messages

    if request.document_ids:
        messages = await _inject_rag_context(messages, request.document_ids)

    if request.use_graph and current_user:
        messages = _inject_graph_context(messages, current_user.id)

    # Use agentic loop for Claude models when authenticated
    use_tools = current_user is not None and request.config.model.startswith("claude-")
    logger.info("chat_stream_path", extra={"use_tools": use_tools, "user": current_user.id if current_user else None})

    if use_tools:
        async def agentic_generate() -> AsyncIterator[str]:
            try:
                async for event in _agentic_stream(messages, request, session_id, store, current_user.id):
                    yield event
            except Exception as e:
                logger.error("agentic_stream_error", extra={"error": str(e)})
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        return StreamingResponse(agentic_generate(), media_type="text/event-stream")

    provider = get_provider_for_model(request.config.model)

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

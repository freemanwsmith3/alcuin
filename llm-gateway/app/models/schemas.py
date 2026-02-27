from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ModelConfig(BaseModel):
    model: str
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=1024, gt=0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stream: bool = False


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    config: ModelConfig
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: LLMResponse
    session_id: Optional[str] = None

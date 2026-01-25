"""
Pydantic models for API request/response validation.

Strict type safety following API specification.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ChatMode(str, Enum):
    """Chat execution mode."""

    LOCAL = "local"
    CLOUD_SECURE = "cloud_secure"


class ChatDepth(str, Enum):
    """Chat reasoning depth."""

    FAST = "fast"
    DEEP_REASONING = "deep_reasoning"


class MessageRole(str, Enum):
    """Chat message role."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


# ============================================================================
# Request Models
# ============================================================================


class ChatMessage(BaseModel):
    """A single chat message."""

    role: MessageRole
    content: str


class ChatConfig(BaseModel):
    """Configuration for chat request."""

    mode: ChatMode = ChatMode.LOCAL
    depth: ChatDepth = ChatDepth.FAST


class ChatCompletionRequest(BaseModel):
    """Request for /v1/chat/completions endpoint.
    
    Compatible with OpenAI API format for Open WebUI integration.
    """

    messages: list[ChatMessage] = Field(..., min_length=1)
    config: ChatConfig = Field(default_factory=ChatConfig)
    session_id: str | None = Field(
        default=None,
        description="Optional vault session ID for encrypted history",
    )
    stream: bool = Field(default=False, description="Enable streaming response")
    
    # OpenAI-compatible fields (for Open WebUI)
    model: str | None = Field(default=None, description="Model name (OpenAI compat)")
    temperature: float | None = Field(default=None, description="Temperature")
    max_tokens: int | None = Field(default=None, description="Max tokens")
    top_p: float | None = Field(default=None, description="Top P sampling")

    model_config = {"extra": "ignore"}  # Allow extra fields from Open WebUI


class IngestRequest(BaseModel):
    """Request for /v1/system/ingest endpoint (JSON body)."""

    content: str | None = Field(
        default=None,
        description="Direct text content to ingest",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata to attach to the document",
    )

    model_config = {"extra": "forbid"}


# ============================================================================
# Response Models
# ============================================================================


class ChatChoice(BaseModel):
    """A single completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """Response for /v1/chat/completions endpoint."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: Usage = Field(default_factory=Usage)
    session_id: str | None = None
    intent: str | None = None


class IngestResponse(BaseModel):
    """Response for /v1/system/ingest endpoint."""

    success: bool
    document_id: str
    chunk_count: int
    message: str


class CollectionStats(BaseModel):
    """RAG collection statistics."""

    collection_name: str
    document_count: int
    bm25_corpus_size: int
    reranking_enabled: bool


class SessionInfo(BaseModel):
    """Vault session information."""

    session_id: str
    message_count: int
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    """Response for listing vault sessions."""

    sessions: list[SessionInfo]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    vault_unlocked: bool
    rag_document_count: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None
    code: str | None = None

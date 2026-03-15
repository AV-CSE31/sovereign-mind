"""
Pydantic schemas for Agentic Structured Outputs.

This module defines the strict schemas that the LLM must adhere to,
ensuring reliability across the Plan-Execute-Grade loop.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    """Enumeration of possible user intents."""

    SIMPLE_CHAT = "simple_chat"
    COMPLEX_REASONING = "complex_reasoning"
    RAG_SEARCH = "rag_search"


class Intent(BaseModel):
    """Classification structure for user queries."""

    category: IntentType = Field(..., description="The specific category of the user's intent.")
    confidence: float = Field(
        ..., description="Confidence score between 0.0 and 1.0.", ge=0.0, le=1.0
    )
    reasoning: str = Field(..., description="Brief explanation of why this category was chosen.")


class Plan(BaseModel):
    """Structured plan for complex queries."""

    steps: list[str] = Field(
        ...,
        description="Sequential list of actionable steps or sub-questions to answer the query.",
        min_items=1,
        max_items=5,
    )


class Grade(BaseModel):
    """Relevance assessment for a retrieved document."""

    score: float = Field(
        ...,
        description="Relevance score between 0.0 (irrelevant) and 1.0 (perfect match).",
        ge=0.0,
        le=1.0,
    )
    is_relevant: bool = Field(
        ..., description="Binary decision if the document contributes to answering the query."
    )
    reasoning: str = Field(..., description="Explanation of the score.")


class RewriteQuery(BaseModel):
    """Optimized query structure."""

    rewritten_query: str = Field(
        ..., description="The reformulated query optimized for vector and keyword search."
    )
    keywords: list[str] = Field(
        default_factory=list, description="Specific high-value keywords extracted from the query."
    )

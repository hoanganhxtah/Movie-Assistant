"""Public request and response models for FastAPI."""

from typing import Any

from pydantic import BaseModel, Field

from .recommendation import MovieRecommendation


class ChatRequest(BaseModel):
    """Input body for one chat turn."""
    thread_id: str = Field(min_length=1, max_length=100)
    user_id: int = Field(gt=0)
    message: str = Field(min_length=1, max_length=2_000)
    include_evidence: bool = True


class ChatResponse(BaseModel):
    """Answer plus optional structured recommendation evidence."""
    answer: str
    intent: str
    recommendations: tuple[MovieRecommendation, ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()
    time_response_ms: float


class ErrorResponse(BaseModel):
    """Client-safe API error body."""
    detail: str

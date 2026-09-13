"""All application data contracts live in this package."""

from .agent import AgentContext, AgentResult, AgentState, AgentToolResult
from .api import ChatRequest, ChatResponse, ErrorResponse
from .data import Movie, Rating, Tag
from .recommendation import (
    BlindSpot,
    MovieRecommendation,
    PeerOpinion,
    RecommendationEvidence,
    ScoreBreakdown,
    SimilarMovie,
    UserProfile,
)
from .search import SearchFilter, SearchHit

__all__ = [
    "AgentState",
    "AgentResult",
    "AgentContext",
    "AgentToolResult",
    "BlindSpot",
    "ChatRequest",
    "ChatResponse",
    "ErrorResponse",
    "Movie",
    "MovieRecommendation",
    "PeerOpinion",
    "Rating",
    "RecommendationEvidence",
    "ScoreBreakdown",
    "SearchFilter",
    "SearchHit",
    "SimilarMovie",
    "Tag",
    "UserProfile",
]

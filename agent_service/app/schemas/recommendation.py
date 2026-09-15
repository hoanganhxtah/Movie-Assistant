"""Structured recommendation, profile and evidence contracts."""

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Normalized signals used to rank one movie."""

    query: float = 0.0
    profile: float = 0.0
    collaborative: float = 0.0
    quality: float = 0.0
    final: float = 0.0


class SimilarMovie(BaseModel):
    """A liked movie used to explain a recommendation."""

    movie_id: int
    title: str
    user_rating: float
    similarity: float


class RecommendationEvidence(BaseModel):
    """Grounding data attached to one recommendation."""

    matched_terms: tuple[str, ...] = ()
    matched_genres: tuple[str, ...] = ()
    similar_liked_movies: tuple[SimilarMovie, ...] = ()
    predicted_rating: float | None = None
    rating_support: int = 0
    confidence: str = "low"


class MovieRecommendation(BaseModel):
    """A ranked movie and the evidence behind it."""

    movie_id: int
    title: str
    year: int | None
    genres: tuple[str, ...]
    plot_summary: str
    scores: ScoreBreakdown
    evidence: RecommendationEvidence


class UserProfile(BaseModel):
    """Compact summary of a user's rating history."""

    user_id: int
    rating_count: int
    average_rating: float
    favorite_genres: tuple[tuple[str, float, int], ...]
    liked_movies: tuple[tuple[int, str, float], ...]


class PeerOpinion(BaseModel):
    """Ratings from users with similar taste."""

    movie_id: int
    title: str
    peer_count: int
    mean_rating: float | None
    positive_share: float | None
    confidence: str


class BlindSpot(BaseModel):
    """An underexplored genre with suggested starting points."""

    genre: str
    user_rating_count: int
    catalog_count: int
    suggested_movies: tuple[str, ...]

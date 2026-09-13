"""Normalized source-data models."""

from pydantic import BaseModel, ConfigDict


class Movie(BaseModel):
    """Catalog movie enriched with tags and rating statistics."""
    model_config = ConfigDict(frozen=True)

    movie_id: int
    title: str
    year: int | None
    genres: tuple[str, ...]
    plot: str
    tags: tuple[str, ...] = ()
    rating_mean: float | None = None
    rating_count: int = 0
    quality_score: float = 0.0


class Rating(BaseModel):
    """One MovieLens user rating."""
    model_config = ConfigDict(frozen=True)

    user_id: int
    movie_id: int
    rating: float
    timestamp: int


class Tag(BaseModel):
    """One free-text MovieLens tag."""
    model_config = ConfigDict(frozen=True)

    user_id: int
    movie_id: int
    tag: str
    timestamp: int

"""Search input and output contracts."""

from pydantic import BaseModel, ConfigDict, Field


class SearchFilter(BaseModel):
    """Hard constraints applied before returning search results."""
    model_config = ConfigDict(frozen=True)

    exclude_genres: tuple[str, ...] = ()
    min_year: int | None = None
    max_year: int | None = None


class SearchHit(BaseModel):
    """One catalog match with its relevance explanation."""
    model_config = ConfigDict(frozen=True)

    movie_id: int
    title: str
    year: int | None
    genres: tuple[str, ...]
    score: float = Field(ge=0.0)
    matched_terms: tuple[str, ...] = ()

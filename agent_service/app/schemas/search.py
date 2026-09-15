"""Search input and output contracts."""

from pydantic import BaseModel, Field


class SearchFilter(BaseModel):
    """Hard constraints applied before returning search results."""

    include_genres: tuple[str, ...] = ()
    exclude_genres: tuple[str, ...] = ()
    min_year: int | None = None
    max_year: int | None = None


class SearchHit(BaseModel):
    """One catalog match with its relevance explanation."""

    movie_id: int
    title: str
    year: int | None
    genres: tuple[str, ...]
    plot_summary: str
    score: float = Field(ge=0.0)
    matched_terms: tuple[str, ...] = ()

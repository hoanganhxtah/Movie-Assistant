"""Search index construction kept behind a small service boundary."""

from agent_service.app.repository import MovieRepository

from .hybrid_search import TfidfMovieRetriever


def build_search_index(repository: MovieRepository) -> TfidfMovieRetriever:
    return TfidfMovieRetriever(repository)


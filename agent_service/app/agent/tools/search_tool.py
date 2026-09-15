"""LangChain tool for non-personalized catalog search."""

import logging
import time

from langchain_core.tools import BaseTool, tool

from agent_service.app.schemas import AgentToolResult, SearchFilter
from agent_service.app.services.search import TfidfMovieRetriever


logger = logging.getLogger(__name__)


def build_search_tool(retriever: TfidfMovieRetriever) -> BaseTool:
    @tool("search_movies", response_format="content_and_artifact")
    def search_movies(
        query: str,
        include_genres: list[str] | None = None,
        exclude_genres: list[str] | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
        limit: int = 5,
    ):
        """Search the catalog. Pass concise English keywords and explicit genre/year filters."""
        started = time.perf_counter()
        logger.info(
            "Tool search_movies started | query=%r | include_genres=%s | "
            "exclude_genres=%s | min_year=%s | max_year=%s | limit=%s",
            query,
            include_genres,
            exclude_genres,
            min_year,
            max_year,
            limit,
        )
        filters = SearchFilter(
            include_genres=tuple(include_genres or []),
            exclude_genres=tuple(exclude_genres or []),
            min_year=min_year,
            max_year=max_year,
        )
        # Keep the tool response small so the LLM receives only the best matches.
        limit = max(1, min(limit, 10))
        hits = retriever.search(query, filters=filters, top_k=limit)
        result = AgentToolResult(
            intent="search",
            evidence=tuple(hit.model_dump(mode="json") for hit in hits),
        )
        logger.info(
            "Tool search_movies completed | results=%s | elapsed_ms=%.2f",
            len(hits),
            (time.perf_counter() - started) * 1000,
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return search_movies

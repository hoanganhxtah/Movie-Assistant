"""LangChain tool for non-personalized catalog search."""

from langchain_core.tools import BaseTool, tool

from agent_service.app.schemas import AgentToolResult, SearchFilter
from agent_service.app.services.search import MovieRetriever


def build_search_tool(retriever: MovieRetriever) -> BaseTool:
    @tool("search_movies", response_format="content_and_artifact")
    def search_movies(
        query: str,
        exclude_genres: list[str] | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
    ):
        """Search movie titles, genres, tags and plots. Use for factual movie discovery, not personalization."""
        filters = SearchFilter(
            exclude_genres=tuple(exclude_genres or []),
            min_year=min_year,
            max_year=max_year,
        )
        # Keep the tool response small so the LLM receives only the best matches.
        hits = retriever.search(query, filters=filters, top_k=5)
        result = AgentToolResult(
            intent="search",
            evidence=tuple(hit.model_dump(mode="json") for hit in hits),
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return search_movies

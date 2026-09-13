"""LangChain tool for personalized movie recommendations."""

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool

from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import AgentContext, AgentToolResult, SearchFilter
from agent_service.app.services.recommendation import RecommendationService


def build_recommendation_tool(
    repository: MovieRepository, service: RecommendationService
) -> BaseTool:
    @tool("recommend_movies", response_format="content_and_artifact")
    def recommend_movies(
        query: str,
        runtime: ToolRuntime[AgentContext],
        exclude_genres: list[str] | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
    ):
        """Recommend unseen movies for the current user. Use an empty query for a general recommendation."""
        filters = SearchFilter(
            exclude_genres=tuple(exclude_genres or []),
            min_year=min_year,
            max_year=max_year,
        )
        # A mentioned title becomes a content anchor for "similar to ..." requests.
        movie = repository.resolve_title(query)
        if movie:
            genres = [genre for genre in movie.genres if genre not in filters.exclude_genres]
            query = " ".join([movie.title, *genres])

        # user_id is injected by the agent runtime and is hidden from the LLM schema.
        recommendations = service.recommend(
            runtime.context.user_id, query, filters, top_k=5
        )
        result = AgentToolResult(
            intent="recommend",
            recommendations=tuple(recommendations),
            evidence=tuple(
                item.evidence.model_dump(mode="json") for item in recommendations
            ),
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return recommend_movies

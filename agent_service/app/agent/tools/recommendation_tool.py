"""LangChain tool for personalized movie recommendations."""

import json
import logging
import time

from langgraph.prebuilt import ToolRuntime
from langchain_core.tools import BaseTool, tool

from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import AgentContext, AgentToolResult, SearchFilter
from agent_service.app.services.recommendation import RecommendationService


logger = logging.getLogger(__name__)


def build_recommendation_tool(
    repository: MovieRepository, service: RecommendationService
) -> BaseTool:
    @tool("recommend_movies", response_format="content_and_artifact")
    def recommend_movies(
        query: str,
        runtime: ToolRuntime[AgentContext],
        reference_title: str | None = None,
        include_genres: list[str] | None = None,
        exclude_genres: list[str] | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
        limit: int = 5,
    ):
        """Recommend unseen movies using concise English keywords and explicit filters."""
        started = time.perf_counter()
        user_id = runtime.context.user_id
        logger.info(
            "Tool recommend_movies started | user_id=%s | query=%r | "
            "reference_title=%r | include_genres=%s | exclude_genres=%s | "
            "min_year=%s | max_year=%s | limit=%s",
            user_id,
            query,
            reference_title,
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
        # Only resolve a title when the LLM explicitly supplies a reference movie.
        if reference_title:
            movie = repository.resolve_title(reference_title)
            if movie is None:
                logger.warning(
                    "Reference movie could not be resolved | requested=%r",
                    reference_title,
                )
                result = AgentToolResult(
                    intent="recommend",
                    evidence=(
                        {
                            "error": "Reference movie title was not found in the catalog",
                            "reference_title": reference_title,
                        },
                    ),
                )
                return result.model_dump_json(), result.model_dump(mode="json")

            logger.info(
                "Reference movie resolved | requested=%r | movie_id=%s | title=%r",
                reference_title,
                movie.movie_id,
                movie.title,
            )
            excluded = {genre.lower() for genre in filters.exclude_genres}
            genres = [
                genre for genre in movie.genres if genre.lower() not in excluded
            ]
            query = " ".join([query, movie.title, *genres]).strip()

        # user_id is injected by the agent runtime and is hidden from the LLM schema.
        limit = max(1, min(limit, 10))
        recommendations = service.recommend(user_id, query, filters, top_k=limit)
        result = AgentToolResult(
            intent="recommend",
            recommendations=tuple(recommendations),
            evidence=tuple(
                item.evidence.model_dump(mode="json") for item in recommendations
            ),
        )
        logger.info(
            "Tool recommend_movies completed | user_id=%s | results=%s | "
            "elapsed_ms=%.2f",
            user_id,
            len(recommendations),
            (time.perf_counter() - started) * 1000,
        )
        # Send only facts needed to write the answer; the API artifact stays complete.
        movies_for_llm = []
        for item in recommendations:
            movie = repository.get_movie(item.movie_id)
            movies_for_llm.append(
                {
                    "title": item.title,
                    "year": item.year,
                    "genres": item.genres,
                    "plot_summary": item.plot_summary,
                    "community_rating": round(movie.rating_mean, 2)
                    if movie.rating_mean is not None
                    else None,
                    "vote_count": movie.rating_count,
                    "matched_terms": item.evidence.matched_terms,
                    "matched_genres": item.evidence.matched_genres,
                    "similar_liked_movies": [
                        {
                            "title": similar.title,
                            "user_rating": similar.user_rating,
                        }
                        for similar in item.evidence.similar_liked_movies
                    ],
                    "predicted_rating": item.evidence.predicted_rating,
                    "confidence": item.evidence.confidence,
                }
            )
        content = json.dumps(
            {"recommendations": movies_for_llm},
            ensure_ascii=False,
        )
        return content, result.model_dump(mode="json")

    return recommend_movies

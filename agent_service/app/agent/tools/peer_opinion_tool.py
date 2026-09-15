"""LangChain tool for ratings from users with similar taste."""

import logging
import time

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool

from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import AgentContext, AgentToolResult
from agent_service.app.services.recommendation import UserUserCollaborativeFilter


logger = logging.getLogger(__name__)


def build_peer_opinion_tool(
    repository: MovieRepository, collaborative: UserUserCollaborativeFilter
) -> BaseTool:
    @tool("get_peer_opinion", response_format="content_and_artifact")
    def get_peer_opinion(movie_title: str, runtime: ToolRuntime[AgentContext]):
        """Summarize how users with similar taste rated a movie from the local catalog."""
        started = time.perf_counter()
        user_id = runtime.context.user_id
        logger.info(
            "Tool get_peer_opinion started | user_id=%s | movie_title=%r",
            user_id,
            movie_title,
        )
        # Resolve loosely typed titles against the local catalog before rating lookup.
        movie = repository.resolve_title(movie_title)
        if movie is None:
            logger.warning(
                "Tool get_peer_opinion could not resolve title | movie_title=%r",
                movie_title,
            )
            result = AgentToolResult(
                intent="peer_opinion",
                evidence=({"error": "Movie title was not found in the catalog"},),
            )
        else:
            opinion = collaborative.peer_opinion(user_id, movie.movie_id)
            result = AgentToolResult(
                intent="peer_opinion",
                evidence=(opinion.model_dump(mode="json"),),
            )
        logger.info(
            "Tool get_peer_opinion completed | user_id=%s | found=%s | "
            "elapsed_ms=%.2f",
            user_id,
            movie is not None,
            (time.perf_counter() - started) * 1000,
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return get_peer_opinion

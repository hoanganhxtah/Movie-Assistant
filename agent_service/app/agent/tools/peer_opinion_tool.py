"""LangChain tool for ratings from users with similar taste."""

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool

from agent_service.app.repository import MovieRepository
from agent_service.app.schemas import AgentContext, AgentToolResult
from agent_service.app.services.recommendation import UserUserCollaborativeFilter


def build_peer_opinion_tool(
    repository: MovieRepository, collaborative: UserUserCollaborativeFilter
) -> BaseTool:
    @tool("get_peer_opinion", response_format="content_and_artifact")
    def get_peer_opinion(movie_title: str, runtime: ToolRuntime[AgentContext]):
        """Summarize how users with similar taste rated a movie from the local catalog."""
        # Resolve loosely typed titles against the local catalog before rating lookup.
        movie = repository.resolve_title(movie_title)
        if movie is None:
            result = AgentToolResult(
                intent="peer_opinion",
                evidence=({"error": "Movie title was not found in the catalog"},),
            )
        else:
            opinion = collaborative.peer_opinion(runtime.context.user_id, movie.movie_id)
            result = AgentToolResult(
                intent="peer_opinion",
                evidence=(opinion.model_dump(mode="json"),),
            )
        return result.model_dump_json(), result.model_dump(mode="json")

    return get_peer_opinion

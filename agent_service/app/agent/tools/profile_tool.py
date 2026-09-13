"""LangChain tools for user profile and blind-spot analysis."""

from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool

from agent_service.app.schemas import AgentContext, AgentToolResult
from agent_service.app.services.recommendation import ProfileService


def build_profile_tool(service: ProfileService) -> BaseTool:
    @tool("get_user_profile", response_format="content_and_artifact")
    def get_user_profile(runtime: ToolRuntime[AgentContext]):
        """Get the current user's rating summary, favorite genres and favorite movies."""
        # Runtime context supplies the authenticated user without exposing an argument.
        profile = service.get_profile(runtime.context.user_id)
        result = AgentToolResult(
            intent="profile", evidence=(profile.model_dump(mode="json"),)
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return get_user_profile


def build_blind_spot_tool(service: ProfileService) -> BaseTool:
    @tool("find_blind_spots", response_format="content_and_artifact")
    def find_blind_spots(runtime: ToolRuntime[AgentContext]):
        """Find movie genres that the current user has explored less than the catalog average."""
        spots = service.blind_spots(runtime.context.user_id)
        result = AgentToolResult(
            intent="blind_spot",
            evidence=tuple(spot.model_dump(mode="json") for spot in spots),
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return find_blind_spots

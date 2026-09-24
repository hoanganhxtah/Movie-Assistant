"""LangChain tools for user profile and blind-spot analysis."""

import logging
import time

from langgraph.prebuilt import ToolRuntime
from langchain_core.tools import BaseTool, tool

from agent_service.app.schemas import AgentContext, AgentToolResult
from agent_service.app.services.recommendation import ProfileService


logger = logging.getLogger(__name__)


def build_profile_tool(service: ProfileService) -> BaseTool:
    @tool("get_user_profile", response_format="content_and_artifact")
    def get_user_profile(runtime: ToolRuntime[AgentContext]):
        """Get the current user's rating summary, favorite genres and favorite movies."""
        # Runtime context supplies the authenticated user without exposing an argument.
        started = time.perf_counter()
        user_id = runtime.context.user_id
        logger.info("Tool get_user_profile started | user_id=%s", user_id)
        profile = service.get_profile(user_id)
        result = AgentToolResult(
            intent="profile", evidence=(profile.model_dump(mode="json"),)
        )
        logger.info(
            "Tool get_user_profile completed | user_id=%s | elapsed_ms=%.2f",
            user_id,
            (time.perf_counter() - started) * 1000,
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return get_user_profile


def build_blind_spot_tool(service: ProfileService) -> BaseTool:
    @tool("find_blind_spots", response_format="content_and_artifact")
    def find_blind_spots(runtime: ToolRuntime[AgentContext]):
        """Find movie genres that the current user has explored less than the catalog average."""
        started = time.perf_counter()
        user_id = runtime.context.user_id
        logger.info("Tool find_blind_spots started | user_id=%s", user_id)
        spots = service.blind_spots(user_id)
        result = AgentToolResult(
            intent="blind_spot",
            evidence=tuple(spot.model_dump(mode="json") for spot in spots),
        )
        logger.info(
            "Tool find_blind_spots completed | user_id=%s | results=%s | "
            "elapsed_ms=%.2f",
            user_id,
            len(spots),
            (time.perf_counter() - started) * 1000,
        )
        return result.model_dump_json(), result.model_dump(mode="json")

    return find_blind_spots

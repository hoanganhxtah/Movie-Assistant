"""One dependency-injected registry for all agent tools."""

from dataclasses import dataclass

from langchain_core.tools import BaseTool

from agent_service.app.repository import MovieRepository
from agent_service.app.services.recommendation import (
    ProfileService,
    RecommendationService,
    UserUserCollaborativeFilter,
)
from agent_service.app.services.search import TfidfMovieRetriever

from .peer_opinion_tool import build_peer_opinion_tool
from .profile_tool import build_blind_spot_tool, build_profile_tool
from .recommendation_tool import build_recommendation_tool
from .search_tool import build_search_tool


@dataclass(frozen=True)
class ToolRegistry:
    repository: MovieRepository
    retriever: TfidfMovieRetriever
    recommendation: RecommendationService
    collaborative: UserUserCollaborativeFilter
    profile: ProfileService

    def build_tools(self) -> list[BaseTool]:
        """Create the small tool set exposed to the LLM agent."""
        return [
            build_recommendation_tool(self.repository, self.recommendation),
            build_search_tool(self.retriever),
            build_profile_tool(self.profile),
            build_peer_opinion_tool(self.repository, self.collaborative),
            build_blind_spot_tool(self.profile),
        ]

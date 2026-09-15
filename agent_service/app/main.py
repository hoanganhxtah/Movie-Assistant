"""FastAPI composition root; all heavy objects are created once at startup."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from agent_service.app.agent import AgentEngine, MovieAgent
from agent_service.app.agent.tools import ToolRegistry
from agent_service.app.api.agent_api import router as agent_router
from agent_service.app.api.health_api import router as health_router
from agent_service.app.config import (
    app_settings,
    data_settings,
    server_settings,
)
from agent_service.app.llm import get_chat_model
from agent_service.app.repository import load_movie_repository
from agent_service.app.services.recommendation import (
    ProfileService,
    RecommendationService,
    UserUserCollaborativeFilter,
)
from agent_service.app.services.search import TfidfMovieRetriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build data indexes and services once, then reuse them for every request.
    repository = load_movie_repository(data_settings.DIR)
    retriever = TfidfMovieRetriever(repository)
    collaborative = UserUserCollaborativeFilter(repository)
    recommendation = RecommendationService(
        repository, retriever, collaborative
    )
    profile = ProfileService(repository)
    tools = ToolRegistry(
        repository=repository,
        retriever=retriever,
        recommendation=recommendation,
        collaborative=collaborative,
        profile=profile,
    )
    app.state.agent_engine = AgentEngine(MovieAgent(get_chat_model(), tools))
    app.state.repository = repository
    yield
    # Drop application references when FastAPI shuts down.
    app.state.agent_engine = None


app = FastAPI(
    title=app_settings.NAME,
    version=app_settings.VERSION,
    lifespan=lifespan,
    docs_url=f"{server_settings.CONTEXT_PATH}/docs",
    openapi_url=f"{server_settings.CONTEXT_PATH}/openapi.json",
)
app.include_router(agent_router, prefix=server_settings.CONTEXT_PATH)
app.include_router(health_router)

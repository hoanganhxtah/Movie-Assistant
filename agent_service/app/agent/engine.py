"""Small application layer between FastAPI and the LangChain agent."""

import logging
import time

from agent_service.app.schemas import AgentState, ChatRequest, ChatResponse

from .movie_agent import MovieAgent


logger = logging.getLogger(__name__)


class AgentEngine:
    def __init__(self, agent: MovieAgent):
        self.agent = agent

    def run(self, request: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        # AgentState contains request identity; message history stays in LangGraph.
        state = AgentState(user_id=request.user_id, thread_id=request.thread_id)
        logger.info(
            "Calling MovieAgent | thread_id=%s | user_id=%s",
            state.thread_id,
            state.user_id,
        )
        result = self.agent.run(
            request.message,
            state,
            include_evidence=request.include_evidence,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "MovieAgent completed | thread_id=%s | user_id=%s | intent=%s | "
            "recommendations=%s | elapsed_ms=%s",
            state.thread_id,
            state.user_id,
            result.intent,
            len(result.recommendations),
            elapsed_ms,
        )
        return ChatResponse(
            answer=result.answer,
            intent=result.intent,
            recommendations=result.recommendations,
            evidence=result.evidence,
            time_response_ms=elapsed_ms,
        )

"""Small application layer between FastAPI and the LangChain agent."""

import logging
import time

from agent_service.app.schemas import AgentState, ChatRequest, ChatResponse

from .movie_agent import MovieAgent


logger = logging.getLogger(__name__)


class AgentEngine:
    def __init__(self, agent: MovieAgent):
        self.agent = agent
        # Map thread_id -> user_id so a conversation cannot be hijacked
        # by a different user calling the API directly.
        self._thread_owner: dict[str, int] = {}

    def run(self, request: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        # AgentState contains request identity; message history stays in LangGraph.
        state = AgentState(user_id=request.user_id, thread_id=request.thread_id)

        # Enforce thread-to-user binding: once a thread_id is used by a
        # user_id, no other user_id may reuse it.
        owner = self._thread_owner.get(state.thread_id)
        if owner is None:
            self._thread_owner[state.thread_id] = state.user_id
        elif owner != state.user_id:
            raise ValueError(
                f"thread_id {state.thread_id!r} belongs to userId {owner}, "
                f"not userId {state.user_id}"
            )

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

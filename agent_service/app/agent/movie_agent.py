"""LangChain movie agent."""

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from agent_service.app.agent.prompts.movie_agent_prompt import (
    MOVIE_AGENT_SYSTEM_PROMPT,
)
from agent_service.app.agent.tools import ToolRegistry
from agent_service.app.schemas import (
    AgentContext,
    AgentResult,
    AgentState,
    AgentToolResult,
)


logger = logging.getLogger(__name__)


class MovieAgent:
    """Wrap the LangChain graph and convert its output to API schemas."""

    def __init__(self, model: BaseChatModel, tools: ToolRegistry):
        self.tools = tools
        # create_react_agent lets the LLM choose a tool or answer casual chat directly.
        self.graph = create_react_agent(
            model=model,
            tools=tools.build_tools(),
            prompt=MOVIE_AGENT_SYSTEM_PROMPT,
            context_schema=AgentContext,
            checkpointer=InMemorySaver(),
        )

    def run(self, message: str, state: AgentState, include_evidence: bool) -> AgentResult:
        if not self.tools.repository.has_user(state.user_id):
            raise ValueError(f"Unknown userId: {state.user_id}")

        # thread_id is the key used by LangGraph to restore conversation history.
        logger.info(
            "Invoking agent graph | thread_id=%s | user_id=%s",
            state.thread_id,
            state.user_id,
        )
        result = self.graph.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": state.thread_id}},
            context=AgentContext(user_id=state.user_id),
        )

        intent = "conversation"
        recommendations = ()
        evidence = ()
        selected_tool = "none"

        # Read the latest tool artifact from this turn. No artifact means normal chat.
        for item in reversed(result["messages"]):
            if isinstance(item, HumanMessage):
                break
            if isinstance(item, ToolMessage) and item.artifact:
                tool_result = AgentToolResult.model_validate(item.artifact)
                intent = tool_result.intent
                recommendations = tool_result.recommendations
                evidence = tool_result.evidence
                selected_tool = item.name or "unknown"
                break

        logger.info(
            "Agent graph completed | thread_id=%s | user_id=%s | tool=%s | "
            "intent=%s | messages=%s",
            state.thread_id,
            state.user_id,
            selected_tool,
            intent,
            len(result["messages"]),
        )

        return AgentResult(
            answer=str(result["messages"][-1].text),
            intent=intent,
            recommendations=recommendations,
            evidence=evidence if include_evidence else (),
            state=state,
        )

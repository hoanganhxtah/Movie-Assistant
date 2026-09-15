"""HTTP endpoint for agent conversations."""

import logging

from fastapi import APIRouter, HTTPException, Request

from agent_service.app.schemas import ChatRequest, ChatResponse, ErrorResponse


router = APIRouter(tags=["agent"])
logger = logging.getLogger(__name__)


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}},
)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """Validate the request and forward it to the shared agent engine."""
    # Limit message length so one request cannot flood the server log.
    message_preview = payload.message[:300]
    logger.info(
        "Chat request received | thread_id=%s | user_id=%s | "
        "include_evidence=%s | message=%r",
        payload.thread_id,
        payload.user_id,
        payload.include_evidence,
        message_preview,
    )
    try:
        response = request.app.state.agent_engine.run(payload)
        logger.info(
            "Chat response ready | thread_id=%s | user_id=%s | intent=%s | "
            "recommendations=%s | evidence=%s | elapsed_ms=%s",
            payload.thread_id,
            payload.user_id,
            response.intent,
            len(response.recommendations),
            len(response.evidence),
            response.time_response_ms,
        )
        return response
    except (LookupError, ValueError) as error:
        logger.warning(
            "Chat request rejected | thread_id=%s | user_id=%s | error=%s",
            payload.thread_id,
            payload.user_id,
            error,
        )
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception(
            "Chat request failed | thread_id=%s | user_id=%s",
            payload.thread_id,
            payload.user_id,
        )
        raise

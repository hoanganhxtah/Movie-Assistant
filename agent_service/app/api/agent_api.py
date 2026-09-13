"""HTTP endpoint for agent conversations."""

from fastapi import APIRouter, HTTPException, Request

from agent_service.app.schemas import ChatRequest, ChatResponse, ErrorResponse


router = APIRouter(tags=["agent"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={400: {"model": ErrorResponse}},
)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    """Validate the request and forward it to the shared agent engine."""
    try:
        return request.app.state.agent_engine.run(payload)
    except (LookupError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

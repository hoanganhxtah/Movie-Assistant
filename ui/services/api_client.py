"""HTTP boundary between Streamlit and the agent backend."""

from __future__ import annotations

import httpx

from config import ui_settings


class AgentAPIError(RuntimeError):
    """Readable backend error shown by the Streamlit UI."""

    pass


def check_health() -> bool:
    """Return False when the backend cannot be reached."""
    try:
        response = httpx.get(
            f"{ui_settings.api_base_url}/health",
            timeout=5.0,
        )
        return response.status_code == 200 and response.json().get("status") == "ok"
    except httpx.HTTPError:
        return False


def post_chat(
    thread_id: str,
    user_id: int,
    message: str,
    include_evidence: bool,
) -> dict:
    """Send one chat turn to agent_service and return its JSON response."""
    try:
        response = httpx.post(
            f"{ui_settings.api_base_url}/api/v1/chat",
            json={
                "thread_id": thread_id,
                "user_id": user_id,
                "message": message,
                "include_evidence": include_evidence,
            },
            timeout=ui_settings.API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        detail = error.response.json().get("detail", error.response.text)
        raise AgentAPIError(str(detail)) from error
    except httpx.HTTPError as error:
        raise AgentAPIError(f"Backend unavailable: {error}") from error

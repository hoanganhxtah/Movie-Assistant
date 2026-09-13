"""Lightweight health endpoint used by the UI and containers."""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report that the initialized API process is available."""
    return {"status": "ok"}

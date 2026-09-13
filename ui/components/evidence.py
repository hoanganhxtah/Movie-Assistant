"""Render optional structured evidence from the backend."""

import streamlit as st


def render_evidence(payload: dict) -> None:
    """Show recommendation details only when the response contains them."""
    evidence = payload.get("evidence") or []
    recommendations = payload.get("recommendations") or []
    if not evidence and not recommendations:
        return
    with st.expander("Structured evidence"):
        st.json(
            {
                "intent": payload.get("intent"),
                "recommendations": recommendations,
                "evidence": evidence,
                "time_response_ms": payload.get("time_response_ms"),
            }
        )

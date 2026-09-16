"""Session and backend controls shown in the Streamlit sidebar."""

from __future__ import annotations

import uuid

import streamlit as st

from services import check_health


def _logout() -> None:
    """Clear every session key so the login screen reappears."""
    for key in ("authenticated_user_id", "thread_id", "messages"):
        st.session_state.pop(key, None)


def render_sidebar() -> tuple[str, int, bool]:
    """Return the current thread, MovieLens user and evidence preference.

    The userId is read-only once authenticated; switching user requires logout.
    """
    user_id: int = st.session_state.authenticated_user_id
    thread_id: str = st.session_state.thread_id

    with st.sidebar:
        st.header("Session")
        st.text_input(
            "Logged in as userId",
            value=str(user_id),
            disabled=True,
        )
        include_evidence = st.toggle("Show evidence", value=True)

        status = "Connected" if check_health() else "Backend unavailable"
        st.caption(status)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("New conversation", use_container_width=True):
                st.session_state.thread_id = str(uuid.uuid4())
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("Logout", use_container_width=True, type="primary"):
                _logout()
                st.rerun()

    return thread_id, user_id, include_evidence

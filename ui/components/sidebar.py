"""Session and backend controls shown in the Streamlit sidebar."""

from __future__ import annotations

import uuid

import streamlit as st

from services import check_health


def render_sidebar() -> tuple[str, int, bool]:
    """Return the current thread, MovieLens user and evidence preference."""
    if "thread_id" not in st.session_state:
        # A new UUID starts an independent LangGraph conversation history.
        st.session_state.thread_id = str(uuid.uuid4())
    with st.sidebar:
        st.header("Session")
        user_id = int(st.number_input("MovieLens userId", min_value=1, value=1))
        include_evidence = st.toggle("Show evidence", value=True)
        status = "Connected" if check_health() else "Backend unavailable"
        st.caption(status)
        if st.button("New conversation"):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
    return st.session_state.thread_id, user_id, include_evidence

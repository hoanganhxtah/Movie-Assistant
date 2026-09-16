"""Login screen: pick a MovieLens userId to start chatting."""

from __future__ import annotations

import uuid

import streamlit as st


def render_login() -> bool:
    """Show a login form and return True once the user has authenticated.

    After a successful login the following session-state keys are set:
    * ``authenticated_user_id`` – the chosen MovieLens userId (int)
    * ``thread_id``             – a fresh UUID for the LangGraph conversation
    * ``messages``              – an empty chat history
    """
    if "authenticated_user_id" in st.session_state:
        return True

    st.title("🎬 Movie Discovery Agent")
    st.caption("Log in with your MovieLens userId to start chatting.")

    with st.form("login_form"):
        user_id = int(
            st.number_input(
                "MovieLens userId",
                min_value=1,
                value=1,
                step=1,
                help="Enter any userId that exists in the MovieLens dataset.",
            )
        )
        submitted = st.form_submit_button("Log in", use_container_width=True)

    if submitted:
        st.session_state.authenticated_user_id = user_id
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    return False

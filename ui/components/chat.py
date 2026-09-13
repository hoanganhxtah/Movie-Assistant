"""Render saved chat messages."""

import streamlit as st

from .evidence import render_evidence


def render_messages(messages: list[dict]) -> None:
    """Replay messages after each Streamlit rerun."""
    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_evidence(message)

"""Streamlit client for the movie-agent backend API."""

from __future__ import annotations

import sys
import streamlit as st

from components.chat import render_messages
from components.evidence import render_evidence
from components.login import render_login
from components.sidebar import render_sidebar
from services import AgentAPIError, post_chat


def main() -> None:
    st.set_page_config(page_title="Movie Discovery Agent", page_icon="🎬")

    # Gate: show login screen until the user picks a userId.
    if not render_login():
        return

    st.title("🎬 Movie Discovery Agent")
    st.caption("Recommendations grounded in the local MovieLens dataset.")

    thread_id, user_id, include_evidence = render_sidebar()
    render_messages(st.session_state.messages)

    if prompt := st.chat_input("What should I watch tonight?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                # The UI only renders data; all agent work stays in agent_service.
                response = post_chat(thread_id, user_id, prompt, include_evidence)
                st.markdown(response["answer"])
                render_evidence(response)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": response["answer"],
                        **response,
                    }
                )
            except AgentAPIError as error:
                message = f"Error: {error}"
                st.error(message)
                st.session_state.messages.append(
                    {"role": "assistant", "content": message}
                )


if __name__ == "__main__":
    if st.runtime.exists():
        main()
    else:
        from streamlit.web import cli as stcli

        sys.argv = ["streamlit", "run", sys.argv[0]] + sys.argv[1:]
        sys.exit(stcli.main())

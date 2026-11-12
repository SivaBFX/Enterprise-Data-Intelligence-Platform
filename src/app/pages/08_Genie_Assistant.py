"""Dedicated Databricks Genie AI Assistant workspace (Milestone 7)."""

from typing import Optional

import streamlit as st

from utils.genie import (
    SUGGESTED_QUESTION_GROUPS,
    GenieResponse,
    ask_genie,
    get_genie_space_info,
    render_genie_response,
)
from utils.ui import (
    apply_theme,
    chart_card,
    render_empty_state,
    render_header,
    render_page_header,
    render_section_header,
)

st.set_page_config(
    page_title="Genie AI Assistant · AI Studio",
    page_icon="✨",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def _load_space_metadata() -> dict:
    """Cache Genie space metadata lookups to avoid redundant API calls."""
    return get_genie_space_info()


def _submit_question(question: str) -> None:
    """Submit a question to Databricks Genie and append to workspace history."""
    with st.spinner("Consulting Databricks Genie and executing query..."):
        response = ask_genie(
            question=question,
            conversation_id=st.session_state.get("genie_ws_conversation_id"),
        )

    history = st.session_state.setdefault("genie_ws_history", [])
    history.append(response)
    if response.success and response.conversation_id:
        st.session_state["genie_ws_conversation_id"] = response.conversation_id


def main() -> None:
    """Render the conversational Genie AI Assistant workspace."""
    apply_theme()
    render_header("Portfolio")

    st.session_state.setdefault("genie_ws_conversation_id", None)
    st.session_state.setdefault("genie_ws_history", [])
    st.session_state.setdefault("genie_ws_pending", None)

    space_info = _load_space_metadata()
    active_conv = st.session_state.get("genie_ws_conversation_id")
    turn_count = len(st.session_state.get("genie_ws_history", []))

    render_page_header(
        title=space_info["title"],
        description=space_info["description"],
        domain_label="Databricks AI/BI Genie · Conversational Assistant",
        reporting_period=(
            f"Active Thread ({turn_count} turn{'s' if turn_count != 1 else ''})"
            if active_conv
            else "New Conversation"
        ),
        status_text=(
            "Genie Space Ready" if space_info["configured"] else "GENIE_SPACE_ID Missing"
        ),
        status_tone="success" if space_info["configured"] else "warning",
    )

    if not space_info["configured"]:
        render_empty_state(
            "Genie Resource Not Configured",
            "Verify GENIE_SPACE_ID is mapped in app.yaml and granted CAN RUN permission.",
            tone="warning",
        )
        st.stop()

    # Execute any queued follow-up or suggested question triggered on previous interaction.
    pending_q: Optional[str] = st.session_state.pop("genie_ws_pending", None)
    if pending_q:
        _submit_question(pending_q)

    # Question bar & conversation controls
    with chart_card(
        title="Ask a Natural-Language Business Question",
        subtitle="Genie maintains conversation context for follow-ups until you start a new thread.",
        badge="Multi-Turn Context" if active_conv else "Ready",
        badge_tone="info",
    ):
        with st.form("genie_workspace_form", clear_on_submit=True):
            q_col, submit_col = st.columns([5.2, 1.2])
            with q_col:
                user_question = st.text_input(
                    "Question",
                    placeholder="Ask about occupancy, NOI, market rankings, maintenance backlogs, or CapEx...",
                    label_visibility="collapsed",
                )
            with submit_col:
                submitted = st.form_submit_button(
                    "Ask Genie", type="primary", use_container_width=True
                )

        if submitted and user_question.strip():
            _submit_question(user_question)
            st.rerun()
        elif submitted:
            st.warning("Please enter a question before submitting.")

        ctrl_left, ctrl_right = st.columns([4.5, 1.3])
        with ctrl_left:
            if active_conv:
                st.caption(
                    f"Thread context active (`conversation_id: {active_conv[:12]}...`). "
                    "Ask a follow-up like 'Break that down by market' or 'Show top 5 properties'."
                )
            else:
                st.caption(
                    "Start by typing a question above or selecting a suggested business question below."
                )
        with ctrl_right:
            if st.button("New Conversation", use_container_width=True):
                st.session_state["genie_ws_conversation_id"] = None
                st.session_state["genie_ws_history"] = []
                st.rerun()

    # Categorized starter questions
    with st.expander("Suggested Business Questions by Domain", expanded=(turn_count == 0)):
        group_cols = st.columns(len(SUGGESTED_QUESTION_GROUPS))
        for g_idx, (col, (group_name, questions)) in enumerate(
            zip(group_cols, SUGGESTED_QUESTION_GROUPS.items())
        ):
            with col:
                st.markdown(f"**{group_name}**")
                for q_idx, q_text in enumerate(questions):
                    if st.button(
                        q_text,
                        key=f"genie_lib_{g_idx}_{q_idx}",
                        use_container_width=True,
                    ):
                        st.session_state["genie_ws_pending"] = q_text
                        st.rerun()

    # Conversation results (latest response prominently shown first)
    history: list = st.session_state.get("genie_ws_history", [])
    if not history:
        render_empty_state(
            "No Questions Asked Yet",
            "Submit a question above to inspect Genie's natural-language answer, generated SQL, and query results.",
            tone="info",
        )
        return

    render_section_header(
        title="Genie Responses",
        subtitle="AI-generated insights and traceable SQL from your Residential Property Intelligence Genie space.",
        badge=f"{len(history)} Turn{'s' if len(history) != 1 else ''}",
        badge_tone="info",
    )

    latest_idx = len(history) - 1
    latest_resp: GenieResponse = history[latest_idx]
    with chart_card(
        title=f"Turn {latest_idx + 1} · Latest Response",
        subtitle="Includes generated SQL inspection, CSV download, and follow-up suggestions when returned.",
        badge=latest_resp.status or ("Completed" if latest_resp.success else "Error"),
        badge_tone="success" if latest_resp.success else "warning",
    ):
        clicked_followup = render_genie_response(
            latest_resp,
            key_prefix=f"genie_ws_turn_{latest_idx}",
            show_followups=True,
        )
        if clicked_followup:
            st.session_state["genie_ws_pending"] = clicked_followup
            st.rerun()

    if len(history) > 1:
        with st.expander(f"Earlier Conversation Turns ({len(history) - 1})"):
            for idx in range(len(history) - 2, -1, -1):
                past_resp: GenieResponse = history[idx]
                st.markdown(f"**Turn {idx + 1}**")
                render_genie_response(
                    past_resp,
                    key_prefix=f"genie_ws_turn_{idx}",
                    show_followups=False,
                )
                if idx > 0:
                    st.divider()


if __name__ == "__main__":
    main()


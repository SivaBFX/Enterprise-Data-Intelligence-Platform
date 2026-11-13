"""AI Business Assistant enterprise conversational intelligence page.

Provides interactive natural-language question answering via Databricks AI/BI Genie
and deterministic specialist decision-support agents with traceable SQL.
"""

from typing import Optional

import streamlit as st

from utils.agents import (
    AGENT_SPEC_MAP,
    AGENT_SPECS,
    AgentResult,
    run_agent_analysis,
)
from utils.genie import (
    SUGGESTED_QUESTION_GROUPS,
    GenieResponse,
    ask_genie,
    get_genie_space_info,
    is_genie_configured,
    render_genie_response,
)
from utils.ui import (
    apply_theme,
    chart_card,
    render_empty_state,
    render_header,
    render_insight_card,
    render_page_header,
    render_section_header,
    status_badge_html,
)

st.set_page_config(
    page_title="AI Business Assistant · Enterprise SaaS",
    page_icon=":material/auto_awesome:",
    layout="wide",
)


def _render_genie_chat_tab() -> None:
    """Render Databricks AI/BI Genie interactive chat workspace."""
    space_info = get_genie_space_info()
    status_tone = "success" if space_info.get("status") == "available" else "warning"

    render_section_header(
        title="Conversational Business Intelligence",
        subtitle="Ask complex property, financial, and operational questions in plain English.",
        badge="Databricks AI/BI Genie",
        badge_tone=status_tone,
    )

    with st.container(border=True):
        st.markdown(
            '<div style="font-size:0.88rem;color:#202B38;font-weight:650;margin-bottom:6px;">'
            'Suggested Executive Questions</div>',
            unsafe_allow_html=True,
        )
        tabs = st.tabs(list(SUGGESTED_QUESTION_GROUPS.keys()))
        for tab, (group_name, questions) in zip(tabs, SUGGESTED_QUESTION_GROUPS.items()):
            with tab:
                cols = st.columns(len(questions))
                for col, q in zip(cols, questions):
                    with col:
                        if st.button(q, key=f"genie_btn_{abs(hash(q))}", use_container_width=True):
                            st.session_state["genie_ws_active_q"] = q

        active_q = st.session_state.pop("genie_ws_active_q", None)

        input_col, ask_col, clear_col = st.columns([4.8, 1.2, 1.0])
        with input_col:
            user_question = st.text_input(
                "Ask a question about your portfolio",
                value=active_q or "",
                placeholder='e.g., "Which 10 properties have the lowest NOI and highest expense ratio?"',
                label_visibility="collapsed",
            )
        with ask_col:
            ask_pressed = st.button("Ask Genie", type="primary", use_container_width=True)
        with clear_col:
            if st.button("New Topic", use_container_width=True):
                st.session_state["genie_ws_conversation_id"] = None
                st.session_state["genie_ws_history"] = []
                st.rerun()

    query_to_run = user_question if ask_pressed and user_question.strip() else active_q

    if query_to_run:
        with st.spinner("Consulting Databricks Genie and generating verifiable SQL..."):
            response = ask_genie(
                question=query_to_run,
                conversation_id=st.session_state.get("genie_ws_conversation_id"),
            )
        history = st.session_state.setdefault("genie_ws_history", [])
        history.append(response)
        if response.success and response.conversation_id:
            st.session_state["genie_ws_conversation_id"] = response.conversation_id

    history = st.session_state.get("genie_ws_history", [])
    if history:
        for idx, resp in enumerate(reversed(history)):
            st.markdown(f"### Q: {resp.question}")
            render_genie_response(resp)
            st.divider()


def _render_specialist_agents_tab() -> None:
    """Render deterministic Gold-data decision support specialist agents."""
    render_section_header(
        title="Deterministic Decision-Support Specialists",
        subtitle="Auditable Gold-table analysis with traceable SQL statements.",
        badge="4 Approved Analysts",
        badge_tone="info",
    )

    agent_cols = st.columns(4)
    for col, spec in zip(agent_cols, AGENT_SPECS):
        with col:
            with st.container(border=True):
                st.markdown(
                    f'<div style="font-weight:700;font-size:0.92rem;color:#202B38;margin-bottom:4px;">{spec.name}</div>'
                    f'<div style="margin-bottom:6px;">{status_badge_html("Approved Specialist", tone="info")}</div>'
                    f'<div style="font-size:0.77rem;color:#758294;min-height:48px;line-height:1.35;">{spec.role}</div>',
                    unsafe_allow_html=True,
                )
                if st.button(f"Consult {spec.name.split()[0]}", key=f"agent_sel_{spec.key}", icon=":material/arrow_forward:", use_container_width=True):
                    st.session_state["selected_agent_key"] = spec.key

    selected_key = st.session_state.get("selected_agent_key", "portfolio")
    spec = AGENT_SPEC_MAP.get(selected_key, AGENT_SPECS[0])

    with st.container(border=True):
        st.markdown(f"#### Running Diagnostic: {spec.name}")
        sample_q = st.selectbox("Select Diagnostic Question", spec.sample_questions)
        if st.button(f"Execute Analysis via {spec.name}", icon=":material/query_stats:", type="primary"):
            with st.spinner("Executing deterministic SQL against Unity Catalog Gold views..."):
                res = run_agent_analysis(spec.key, sample_q)
            st.success(res.summary)
            if res.findings:
                for f in res.findings:
                    st.markdown(f"- {f}")
            if res.trace_sql:
                st.code(res.trace_sql, language="sql")


def main() -> None:
    """Render the AI Business Assistant enterprise page."""
    apply_theme()
    render_header("AI Business Assistant")

    render_page_header(
        title="AI Business Assistant",
        description="Conversational analytics and specialized decision support powered by Databricks Genie and Unity Catalog.",
        domain_label="Analytics & AI",
        reporting_period="Enterprise Assistant",
        status_text="Genie Configured" if is_genie_configured() else "Check Configuration",
        status_tone="success" if is_genie_configured() else "warning",
    )

    t1, t2 = st.tabs(["Databricks Genie Assistant", "Specialist Decision Agents"])
    with t1:
        _render_genie_chat_tab()
    with t2:
        _render_specialist_agents_tab()


if __name__ == "__main__":
    main()


"""AI Studio Specialist Agents & Decision Support page (Milestone 8)."""

from typing import Optional

import streamlit as st

from utils.agents import (
    AGENT_SPEC_MAP,
    AGENT_SPECS,
    AgentResult,
    run_agent_analysis,
)
from utils.genie import (
    GenieResponse,
    ask_genie,
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
    page_title="Agents · Property Intelligence AI Studio",
    page_icon="🤖",
    layout="wide",
)


def _render_agent_directory() -> None:
    """Render 2x2 directory cards for all four specialist Gold-data agents."""
    render_section_header(
        title="Specialist Decision-Support Agents",
        subtitle="Select a domain specialist below to run deterministic Gold-table diagnostics with traceable SQL.",
        badge="4 Approved Gold Analysts",
        badge_tone="success",
    )

    rows = [AGENT_SPECS[:2], AGENT_SPECS[2:]]
    for pair in rows:
        cols = st.columns(2)
        for col, spec in zip(cols, pair):
            with col:
                is_selected = st.session_state.get("selected_agent_key") == spec.key
                with chart_card(
                    title=f"{spec.icon} {spec.name}",
                    subtitle=spec.role,
                    badge="Active" if is_selected else "Implemented",
                    badge_tone="success" if is_selected else "info",
                ):
                    st.caption(
                        f"**Approved Gold Sources:** {', '.join(f'`{t}`' for t in spec.approved_tables)}"
                    )
                    for cap in spec.capabilities:
                        st.markdown(f"- {cap}")
                    if st.button(
                        f"Select {spec.name}",
                        key=f"select_agent_{spec.key}",
                        type="primary" if is_selected else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["selected_agent_key"] = spec.key
                        st.session_state["agent_question_input"] = spec.sample_questions[0]
                        st.rerun()


def _render_agent_result(
    result: AgentResult,
    genie_resp: Optional[GenieResponse],
) -> None:
    """Render traceable Gold evidence alongside clearly labeled simulated previews."""
    render_section_header(
        title=f"Agent Analysis · {result.agent_name}",
        subtitle=result.summary,
        badge=result.implementation_mode,
        badge_tone="success",
    )

    with chart_card(
        title="Traceable Findings & Supporting Gold Evidence",
        subtitle=f"Question: {result.question}",
        badge="Implemented · Live Gold Query",
        badge_tone="success",
    ):
        source_badges = " ".join(
            status_badge_html(tbl.split(".")[-1], tone="neutral")
            for tbl in result.source_tables
        )
        st.markdown(
            f"{status_badge_html('Deterministic Gold Data', tone='success')} {source_badges}",
            unsafe_allow_html=True,
        )

        for finding in result.findings:
            st.markdown(f"- {finding}")

        if result.recommended_action:
            render_insight_card(
                title="Rule-Based Decision Support Action",
                body=result.recommended_action,
                tone="info",
                tag="Rule-Based Action",
            )

        if result.evidence_df is not None and not result.evidence_df.empty:
            st.dataframe(result.evidence_df, use_container_width=True, hide_index=True)
            csv_bytes = result.evidence_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Supporting Evidence (CSV)",
                data=csv_bytes,
                file_name=f"{result.agent_name.lower().replace(' ', '_')}_evidence.csv",
                mime="text/csv",
                key="agent_evidence_csv",
            )

        if result.trace_sql:
            with st.expander("View Traceable Gold SQL & Governance Scope"):
                st.caption(
                    "Equivalent SQL representation of the approved Gold-table logic executed by this agent:"
                )
                st.code(result.trace_sql, language="sql")

    if result.simulated_preview:
        render_insight_card(
            title="Simulated Downstream Action Preview (Demonstration Only)",
            body=result.simulated_preview,
            tone="warning",
            tag="Simulated Demo · Not Executed",
        )

    if genie_resp is not None:
        with chart_card(
            title="Databricks Genie AI Supplement",
            subtitle="Open-ended natural-language response from Residential Property Intelligence Genie",
            badge="AI-Generated (Genie)",
            badge_tone="info",
        ):
            render_genie_response(
                genie_resp,
                key_prefix="agent_genie_supp",
                show_followups=False,
            )


def main() -> None:
    """Render the Specialist Agents & Business Decision Support workspace."""
    apply_theme()
    render_header(active_page="", active_section="Agents")

    st.session_state.setdefault("selected_agent_key", "portfolio")
    st.session_state.setdefault(
        "agent_question_input", AGENT_SPEC_MAP["portfolio"].sample_questions[0]
    )
    st.session_state.setdefault("agent_last_result", None)
    st.session_state.setdefault("agent_last_genie", None)

    render_page_header(
        title="AI Agents & Business Decision Support",
        description=(
            "Domain-scoped specialist analysts grounded in approved Unity Catalog Gold tables "
            "with traceable SQL evidence, optional Databricks Genie AI augmentation, and explicit "
            "separation between live analytics and simulated action previews."
        ),
        domain_label="Agents · AI Studio",
        reporting_period="4 Domain Specialists",
        status_text=(
            "Gold Analysts Active · Genie Ready"
            if is_genie_configured()
            else "Gold Analysts Active"
        ),
        status_tone="success",
    )

    col_impl, col_sim = st.columns(2)
    with col_impl:
        render_insight_card(
            title="Implemented Capabilities (Live Databricks)",
            body=(
                "Each specialist queries only its approved Gold tables via your SQL Warehouse, "
                "computes deterministic metrics, displays supporting rows, and provides traceable SQL. "
                "Optional Genie AI synthesis uses your live GENIE_SPACE_ID."
            ),
            tone="success",
            tag="Implemented",
        )
    with col_sim:
        render_insight_card(
            title="Simulated Demonstration Features",
            body=(
                "Downstream operational workflows (drafted executive emails, maintenance dispatch tickets, "
                "and CapEx approval memos) are simulated UI previews only—no external systems are modified."
            ),
            tone="warning",
            tag="Simulated Demo",
        )

    _render_agent_directory()

    selected_key = st.session_state.get("selected_agent_key", "portfolio")
    if selected_key not in AGENT_SPEC_MAP:
        selected_key = "portfolio"
    active_spec = AGENT_SPEC_MAP[selected_key]

    render_section_header(
        title="Agent Decision Console",
        subtitle=f"Currently active: {active_spec.icon} {active_spec.name}",
        badge="Traceable Execution",
        badge_tone="info",
    )

    with chart_card(
        title=f"Consult {active_spec.name}",
        subtitle=active_spec.role,
        badge=active_spec.implementation_label,
        badge_tone="success",
    ):
        agent_options = [spec.key for spec in AGENT_SPECS]
        chosen_key = st.selectbox(
            "Specialist Agent",
            agent_options,
            index=agent_options.index(selected_key),
            format_func=lambda k: f"{AGENT_SPEC_MAP[k].icon} {AGENT_SPEC_MAP[k].name}",
        )
        if chosen_key != selected_key:
            st.session_state["selected_agent_key"] = chosen_key
            st.session_state["agent_question_input"] = AGENT_SPEC_MAP[
                chosen_key
            ].sample_questions[0]
            st.rerun()

        st.caption("Quick prompts for this specialist:")
        p_cols = st.columns(len(active_spec.sample_questions))
        triggered_question: Optional[str] = None
        for idx, (col, prompt_text) in enumerate(
            zip(p_cols, active_spec.sample_questions)
        ):
            with col:
                if st.button(
                    prompt_text,
                    key=f"agent_prompt_{active_spec.key}_{idx}",
                    use_container_width=True,
                ):
                    st.session_state["agent_question_input"] = prompt_text
                    triggered_question = prompt_text

        q_col, btn_col = st.columns([5.0, 1.4])
        with q_col:
            question_text = st.text_input(
                "Question for specialist agent",
                key="agent_question_input",
                placeholder="Enter a domain question...",
                label_visibility="collapsed",
            )
        with btn_col:
            if st.button("Run Specialist Agent", type="primary", use_container_width=True):
                triggered_question = question_text

        also_genie = st.checkbox(
            "Also consult Databricks Genie AI for an open-ended natural-language supplement",
            value=False,
            disabled=not is_genie_configured(),
        )

        if triggered_question is not None:
            try:
                with st.spinner(f"Running {active_spec.name} against Unity Catalog Gold tables..."):
                    result = run_agent_analysis(active_spec.key, triggered_question)
                st.session_state["agent_last_result"] = result

                genie_supp: Optional[GenieResponse] = None
                if also_genie and is_genie_configured():
                    with st.spinner("Querying Databricks Genie AI supplement..."):
                        genie_supp = ask_genie(triggered_question)
                st.session_state["agent_last_genie"] = genie_supp
            except Exception as exc:
                st.error("Specialist agent failed to execute Gold query.")
                st.exception(exc)

    last_result: Optional[AgentResult] = st.session_state.get("agent_last_result")
    last_genie: Optional[GenieResponse] = st.session_state.get("agent_last_genie")

    if last_result is None:
        render_empty_state(
            "Select a Prompt or Ask a Question Above",
            "Run any specialist agent to view Gold-backed findings, evidence rows, traceable SQL, and simulated workflow previews.",
            tone="info",
        )
    else:
        _render_agent_result(last_result, last_genie)


if __name__ == "__main__":
    main()


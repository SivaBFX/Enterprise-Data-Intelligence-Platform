"""Databricks AI/BI Genie integration helper for natural-language analytics."""

from dataclasses import dataclass, field
from datetime import timedelta
import html
import os
import time
from typing import Any, Dict, List, Optional

from databricks.sdk import WorkspaceClient
import pandas as pd
import streamlit as st

from utils.monitoring import record_event
from utils.ui import status_badge_html

SUGGESTED_QUESTIONS = [
    "Top NOI & occupancy markets?",
    "Low occupancy or negative NOI?",
    "Highest maintenance & backlog?",
    "12-month revenue & NOI trend?",
]

SUGGESTED_QUESTION_GROUPS: Dict[str, List[str]] = {
    "Portfolio & Financials": [
        "How have monthly rental revenue and NOI trended across the last 12 months?",
        "What is our overall weighted occupancy and total NOI in the latest reporting month?",
    ],
    "Markets": [
        "Rank all markets by total NOI, weighted occupancy, and operating expense ratio.",
        "Which market had the highest operating expense ratio in the latest month?",
    ],
    "Properties": [
        "Which 10 properties generated the highest total NOI?",
        "Which properties have overall occupancy below 85% or negative NOI?",
    ],
    "Maintenance & CapEx": [
        "Which properties have the highest maintenance costs and open work orders?",
        "What is total CapEx investment by category and market?",
    ],
}


@dataclass
class GenieResponse:
    """Structured result returned from a Databricks Genie conversation call."""

    success: bool
    question: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    status: Optional[str] = None
    text_answers: List[str] = field(default_factory=list)
    sql_query: Optional[str] = None
    sql_description: Optional[str] = None
    dataframe: Optional[pd.DataFrame] = None
    row_count: Optional[int] = None
    is_truncated: Optional[bool] = None
    suggested_questions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


def is_genie_configured(space_id: Optional[str] = None) -> bool:
    """Return True when GENIE_SPACE_ID is available."""
    return bool((space_id or os.getenv("GENIE_SPACE_ID", "")).strip())


def get_genie_space_info(space_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve Genie space metadata when supported by the installed SDK."""
    resolved_space_id = (space_id or os.getenv("GENIE_SPACE_ID", "")).strip()
    if not resolved_space_id:
        return {
            "configured": False,
            "space_id": None,
            "title": "Residential Property Intelligence Genie",
            "description": "GENIE_SPACE_ID environment variable is not configured.",
        }

    info: Dict[str, Any] = {
        "configured": True,
        "space_id": resolved_space_id,
        "title": "Residential Property Intelligence Genie",
        "description": "Natural-language analytics over Unity Catalog residential property Gold tables.",
    }

    try:
        client = WorkspaceClient()
        genie_svc = getattr(client, "genie", None)
        if genie_svc and hasattr(genie_svc, "get_space"):
            space_obj = genie_svc.get_space(space_id=resolved_space_id)
            if getattr(space_obj, "title", None):
                info["title"] = str(space_obj.title)
            if getattr(space_obj, "description", None):
                info["description"] = str(space_obj.description)
    except Exception:
        # Gracefully retain default display metadata if get_space is unavailable or restricted.
        pass

    return info


def _extract_query_dataframe(
    client: WorkspaceClient,
    space_id: str,
    conversation_id: Optional[str],
    message_id: Optional[str],
    attachment_id: Optional[str],
) -> Optional[pd.DataFrame]:
    """Fetch tabular rows for a Genie SQL attachment when supported."""
    if not (conversation_id and message_id and attachment_id):
        return None

    try:
        query_result = client.genie.get_message_attachment_query_result(
            space_id=space_id,
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
        )
        statement = getattr(query_result, "statement_response", None)
        if not statement:
            return None

        manifest = getattr(statement, "manifest", None)
        result = getattr(statement, "result", None)
        schema = getattr(manifest, "schema", None) if manifest else None
        columns = getattr(schema, "columns", None) if schema else None
        rows = getattr(result, "data_array", None) if result else None

        if not columns or rows is None:
            return None

        col_names = [col.name for col in columns]
        return pd.DataFrame(rows, columns=col_names)
    except Exception:
        return None


def ask_genie(
    question: str,
    space_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    timeout_seconds: int = 120,
) -> GenieResponse:
    """Submit a natural-language question to Databricks Genie and parse its answer."""
    cleaned_question = (question or "").strip()
    if not cleaned_question:
        return GenieResponse(
            success=False,
            question="",
            error_message="Please enter a business question for Genie.",
        )

    resolved_space_id = (space_id or os.getenv("GENIE_SPACE_ID", "")).strip()
    if not resolved_space_id:
        return GenieResponse(
            success=False,
            question=cleaned_question,
            error_message="GENIE_SPACE_ID resource is not configured in app.yaml.",
        )

    started = time.perf_counter()
    try:
        client = WorkspaceClient()
        if not hasattr(client, "genie"):
            return GenieResponse(
                success=False,
                question=cleaned_question,
                error_message=(
                    "Installed databricks-sdk version does not expose the Genie API. "
                    "Upgrade databricks-sdk to use Genie."
                ),
            )

        wait_timeout = timedelta(seconds=timeout_seconds)
        if conversation_id:
            message = client.genie.create_message_and_wait(
                space_id=resolved_space_id,
                conversation_id=conversation_id,
                content=cleaned_question,
                timeout=wait_timeout,
            )
        else:
            message = client.genie.start_conversation_and_wait(
                space_id=resolved_space_id,
                content=cleaned_question,
                timeout=wait_timeout,
            )

        resolved_conv_id = getattr(message, "conversation_id", conversation_id)
        resolved_msg_id = getattr(message, "id", None) or getattr(
            message, "message_id", None
        )
        status_obj = getattr(message, "status", None)
        status_str = getattr(status_obj, "value", str(status_obj)) if status_obj else None

        msg_error = getattr(message, "error", None)
        if status_str in {"FAILED", "CANCELLED"} or msg_error:
            err_detail = getattr(msg_error, "error", None) or str(msg_error or status_str)
            return GenieResponse(
                success=False,
                question=cleaned_question,
                conversation_id=resolved_conv_id,
                message_id=resolved_msg_id,
                status=status_str,
                error_message=f"Genie query did not complete ({status_str}): {err_detail}",
            )

        text_answers: List[str] = []
        sql_query: Optional[str] = None
        sql_description: Optional[str] = None
        result_df: Optional[pd.DataFrame] = None
        row_count: Optional[int] = None
        is_truncated: Optional[bool] = None
        follow_ups: List[str] = []

        for attachment in getattr(message, "attachments", None) or []:
            text_att = getattr(attachment, "text", None)
            if text_att and getattr(text_att, "content", None):
                text_answers.append(str(text_att.content).strip())

            query_att = getattr(attachment, "query", None)
            if query_att:
                sql_query = getattr(query_att, "query", None) or sql_query
                sql_description = (
                    getattr(query_att, "description", None) or sql_description
                )
                metadata = getattr(query_att, "query_result_metadata", None)
                if metadata:
                    if getattr(metadata, "row_count", None) is not None:
                        row_count = int(metadata.row_count)
                    if getattr(metadata, "is_truncated", None) is not None:
                        is_truncated = bool(metadata.is_truncated)

                attachment_id = getattr(attachment, "attachment_id", None)
                if result_df is None:
                    result_df = _extract_query_dataframe(
                        client=client,
                        space_id=resolved_space_id,
                        conversation_id=resolved_conv_id,
                        message_id=resolved_msg_id,
                        attachment_id=attachment_id,
                    )
                    if result_df is not None and row_count is None:
                        row_count = len(result_df)

            sq_att = getattr(attachment, "suggested_questions", None)
            if sq_att and getattr(sq_att, "questions", None):
                follow_ups.extend([str(q) for q in sq_att.questions if q])

        fallback_content = getattr(message, "content", None)
        if not text_answers and not sql_query and fallback_content:
            text_answers.append(str(fallback_content).strip())

        record_event(
            category="genie",
            target=resolved_space_id[:12],
            status="ok",
            duration_ms=(time.perf_counter() - started) * 1000.0,
            detail=f"status={status_str} rows={row_count}",
        )
        return GenieResponse(
            success=True,
            question=cleaned_question,
            conversation_id=resolved_conv_id,
            message_id=resolved_msg_id,
            status=status_str,
            text_answers=text_answers,
            sql_query=sql_query,
            sql_description=sql_description,
            dataframe=result_df,
            row_count=row_count,
            is_truncated=is_truncated,
            suggested_questions=follow_ups,
        )

    except Exception as exc:
        record_event(
            category="genie",
            target=resolved_space_id[:12],
            status="error",
            duration_ms=(time.perf_counter() - started) * 1000.0,
            detail=type(exc).__name__,
        )
        return GenieResponse(
            success=False,
            question=cleaned_question,
            conversation_id=conversation_id,
            error_message=(
                f"Unable to reach Databricks Genie ({type(exc).__name__}: {exc}). "
                "Verify app CAN RUN permissions on Residential Property Intelligence Genie "
                "and SQL Warehouse CAN USE access."
            ),
        )


def render_genie_response(
    response: GenieResponse,
    key_prefix: str = "genie",
    show_followups: bool = True,
) -> Optional[str]:
    """Render a Genie response with SQL, tabular data, CSV export, and follow-ups."""
    if not response.success:
        st.warning(response.error_message or "Genie could not complete this request.")
        return None

    badges = [status_badge_html("AI-Generated (Genie)", tone="info")]
    if response.row_count is not None:
        row_label = f"{response.row_count:,} row{'s' if response.row_count != 1 else ''}"
        if response.is_truncated:
            row_label += " (truncated)"
        badges.append(status_badge_html(row_label, tone="neutral"))

    st.markdown(
        f"{' '.join(badges)} &nbsp; **Question:** {html.escape(response.question)}",
        unsafe_allow_html=True,
    )

    if response.text_answers:
        for answer_block in response.text_answers:
            st.markdown(answer_block)
    elif response.sql_description:
        st.markdown(response.sql_description)

    if response.dataframe is not None and not response.dataframe.empty:
        st.dataframe(response.dataframe, use_container_width=True, hide_index=True)
        csv_bytes = response.dataframe.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Results (CSV)",
            data=csv_bytes,
            file_name="genie_query_results.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv",
        )
    elif response.sql_query:
        st.caption(
            "Genie generated SQL for this question. Expand below to inspect the query."
        )

    if response.sql_query:
        with st.expander("View SQL generated by Genie"):
            if response.sql_description:
                st.caption(response.sql_description)
            st.code(response.sql_query, language="sql")

    if show_followups and response.suggested_questions:
        st.caption("Suggested follow-up questions:")
        f_cols = st.columns(min(len(response.suggested_questions), 3))
        for idx, (col, fq) in enumerate(zip(f_cols, response.suggested_questions[:3])):
            with col:
                if st.button(fq, key=f"{key_prefix}_followup_{idx}", use_container_width=True):
                    return fq

    return None

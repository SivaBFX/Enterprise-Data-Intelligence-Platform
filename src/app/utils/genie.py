"""Databricks AI/BI Genie integration helper for natural-language analytics."""

from dataclasses import dataclass, field
from datetime import timedelta
import os
from typing import List, Optional

from databricks.sdk import WorkspaceClient
import pandas as pd

SUGGESTED_QUESTIONS = [
    "Which markets delivered the highest NOI and weighted occupancy?",
    "Which properties have occupancy below 85% or negative NOI?",
    "Which properties have the highest maintenance costs and open work orders?",
    "How have portfolio rental revenue and NOI trended over the last 12 months?",
]


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
    suggested_questions: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


def is_genie_configured(space_id: Optional[str] = None) -> bool:
    """Return True when GENIE_SPACE_ID is available."""
    return bool((space_id or os.getenv("GENIE_SPACE_ID", "")).strip())


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

        text_answers: List[str] = []
        sql_query: Optional[str] = None
        sql_description: Optional[str] = None
        result_df: Optional[pd.DataFrame] = None
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
                attachment_id = getattr(attachment, "attachment_id", None)
                if result_df is None:
                    result_df = _extract_query_dataframe(
                        client=client,
                        space_id=resolved_space_id,
                        conversation_id=resolved_conv_id,
                        message_id=resolved_msg_id,
                        attachment_id=attachment_id,
                    )

            sq_att = getattr(attachment, "suggested_questions", None)
            if sq_att and getattr(sq_att, "questions", None):
                follow_ups.extend([str(q) for q in sq_att.questions if q])

        fallback_content = getattr(message, "content", None)
        if not text_answers and not sql_query and fallback_content:
            text_answers.append(str(fallback_content).strip())

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
            suggested_questions=follow_ups,
        )

    except Exception as exc:
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


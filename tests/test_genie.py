"""Databricks Genie integration and error-handling tests."""

import os
import types
import unittest
from unittest.mock import patch

from tests._test_env import install_test_stubs

st_stub = install_test_stubs()
import utils.genie as genie  # noqa: E402


class _FakeGenieService:
    def get_space(self, space_id):
        return types.SimpleNamespace(
            title="Residential Property Intelligence Genie",
            description="Gold portfolio Q&A space",
        )

    def start_conversation_and_wait(self, space_id, content, timeout=None):
        att_text = types.SimpleNamespace(
            text=types.SimpleNamespace(content="Austin leads portfolio NOI."),
            query=None,
            suggested_questions=None,
            attachment_id="att-1",
        )
        att_query = types.SimpleNamespace(
            text=None,
            query=types.SimpleNamespace(
                query="SELECT market_name, total_noi FROM workspace.gold.gold_market_monthly",
                description="Market NOI summary",
                query_result_metadata=types.SimpleNamespace(row_count=2, is_truncated=False),
            ),
            suggested_questions=types.SimpleNamespace(questions=["Show occupancy too"]),
            attachment_id="att-2",
        )
        return types.SimpleNamespace(
            id="msg-1",
            conversation_id="conv-abc",
            status=types.SimpleNamespace(value="COMPLETED"),
            error=None,
            content="",
            attachments=[att_text, att_query],
        )

    def create_message_and_wait(self, space_id, conversation_id, content, timeout=None):
        return types.SimpleNamespace(
            id="msg-2",
            conversation_id=conversation_id,
            status=types.SimpleNamespace(value="FAILED"),
            error=types.SimpleNamespace(error="Warehouse unavailable"),
            content="",
            attachments=[],
        )

    def get_message_attachment_query_result(
        self, space_id, conversation_id, message_id, attachment_id
    ):
        cols = [types.SimpleNamespace(name="market_name"), types.SimpleNamespace(name="total_noi")]
        return types.SimpleNamespace(
            statement_response=types.SimpleNamespace(
                manifest=types.SimpleNamespace(schema=types.SimpleNamespace(columns=cols)),
                result=types.SimpleNamespace(data_array=[["Austin", "75000"], ["Denver", "45000"]]),
            )
        )


class _FakeClient:
    def __init__(self):
        self.genie = _FakeGenieService()


class TestGenieIntegration(unittest.TestCase):
    """Validate Genie SDK wrappers, follow-ups, and failure states."""

    def setUp(self) -> None:
        st_stub.session_state.clear()

    def test_empty_question_and_missing_space(self) -> None:
        self.assertFalse(genie.ask_genie("   ").success)
        with patch.dict(os.environ, {}, clear=True):
            res = genie.ask_genie("What is total NOI?")
        self.assertFalse(res.success)
        self.assertIn("GENIE_SPACE_ID", res.error_message)

    def test_start_conversation_and_extract_dataframe(self) -> None:
        with patch.dict(os.environ, {"GENIE_SPACE_ID": "space-1"}, clear=True):
            with patch.object(genie, "WorkspaceClient", _FakeClient):
                info = genie.get_genie_space_info()
                res = genie.ask_genie("Which market leads NOI?")

        self.assertTrue(info["configured"])
        self.assertTrue(res.success)
        self.assertEqual(res.conversation_id, "conv-abc")
        self.assertEqual(res.row_count, 2)
        self.assertFalse(res.is_truncated)
        self.assertEqual(len(res.dataframe), 2)
        self.assertEqual(res.suggested_questions, ["Show occupancy too"])

    def test_failed_status_surfaces_error(self) -> None:
        with patch.dict(os.environ, {"GENIE_SPACE_ID": "space-1"}, clear=True):
            with patch.object(genie, "WorkspaceClient", _FakeClient):
                res = genie.ask_genie("Follow-up", conversation_id="conv-abc")

        self.assertFalse(res.success)
        self.assertIn("Warehouse unavailable", res.error_message)


if __name__ == "__main__":
    unittest.main()


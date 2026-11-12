"""Database connection, SQL validation, and telemetry tests."""

from decimal import Decimal
import os
import unittest
from unittest.mock import patch

import pandas as pd

from tests._test_env import install_test_stubs

st_stub = install_test_stubs()
import utils.database as db  # noqa: E402
import utils.monitoring as monitoring  # noqa: E402


class TestDatabaseAndSQLValidation(unittest.TestCase):
    """Validate SQL Warehouse connection handling, SQL guards, and coercion."""

    def setUp(self) -> None:
        st_stub.session_state.clear()

    def test_missing_warehouse_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                db.get_connection()

    def test_get_connection_strips_scheme(self) -> None:
        captured = {}

        def fake_connect(**kwargs):
            captured.update(kwargs)
            return "conn"

        with patch.dict(os.environ, {"DATABRICKS_WAREHOUSE_ID": "wh123"}, clear=True):
            with patch.object(db.sql, "connect", side_effect=fake_connect):
                conn = db.get_connection()

        self.assertEqual(conn, "conn")
        self.assertEqual(captured["server_hostname"], "example.cloud.databricks.com")
        self.assertEqual(captured["http_path"], "/sql/1.0/warehouses/wh123")

    def test_table_identifier_validation(self) -> None:
        self.assertEqual(
            db._validate_table_identifier("workspace.gold.gold_portfolio_kpis"),
            "workspace.gold.gold_portfolio_kpis",
        )
        for bad in ["", "x; DROP TABLE y", "table -- comment", "bad space"]:
            with self.assertRaises(ValueError):
                db._validate_table_identifier(bad)

    def test_read_only_sql_validation(self) -> None:
        self.assertEqual(
            db.validate_read_only_sql("  SELECT * FROM workspace.gold.gold_portfolio_kpis; "),
            "SELECT * FROM workspace.gold.gold_portfolio_kpis",
        )
        self.assertTrue(
            db.validate_read_only_sql("DESCRIBE TABLE workspace.gold.gold_capex_summary").startswith(
                "DESCRIBE"
            )
        )
        for unsafe in [
            "",
            "DROP TABLE workspace.gold.gold_capex_summary",
            "DELETE FROM workspace.gold.gold_capex_summary",
            "SELECT 1; DROP TABLE x",
            "SELECT * FROM x -- comment",
            "UPDATE workspace.gold.gold_capex_summary SET a = 1",
        ]:
            with self.assertRaises(ValueError):
                db.validate_read_only_sql(unsafe)

    def test_run_query_records_telemetry(self) -> None:
        class FakeCursor:
            description = [("property_id",), ("total_noi",)]

            def execute(self, query):
                self.query = query

            def fetchall(self):
                return [("P-1", Decimal("1200.50"))]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        class FakeConn:
            def cursor(self):
                return FakeCursor()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.object(db, "get_connection", return_value=FakeConn()):
            df = db.query_table("workspace.gold.gold_property_performance", limit=5)

        self.assertEqual(len(df), 1)
        events = monitoring.get_recent_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["category"], "sql")
        self.assertEqual(events[0]["status"], "ok")

    def test_coerce_numeric_handles_decimals_and_invalid(self) -> None:
        df = pd.DataFrame([{"a": Decimal("10.5"), "b": "bad", "c": None}])
        coerced = db.coerce_numeric(df, ["a", "b", "c"])
        self.assertEqual(float(coerced.iloc[0]["a"]), 10.5)
        self.assertEqual(float(coerced.iloc[0]["b"]), 0.0)
        self.assertEqual(float(coerced.iloc[0]["c"]), 0.0)

    def test_freshness_handles_error_gracefully(self) -> None:
        with patch.object(db, "run_query", side_effect=RuntimeError("permission denied")):
            res = db.get_table_freshness("workspace.gold.gold_portfolio_kpis")
        self.assertEqual(res["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()


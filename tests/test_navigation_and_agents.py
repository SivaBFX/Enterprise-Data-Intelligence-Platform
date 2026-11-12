"""Navigation route integrity, UI contrast helper, and agent safety tests."""

import unittest

import pandas as pd

from tests._test_env import APP_DIR, install_test_stubs, load_app_module

st_stub = install_test_stubs()
import utils.agents as agents  # noqa: E402
import utils.ui as ui  # noqa: E402

dp_mod = load_app_module("pages/06_Data_Products.py", "test_dp_mod")


class TestNavigationAndAgents(unittest.TestCase):
    """Verify all navigation page targets exist and specialist agents degrade safely."""

    def setUp(self) -> None:
        st_stub.captured_links.clear()
        st_stub.captured_markdown.clear()

    def test_all_configured_page_files_exist(self) -> None:
        expected_paths = (
            [path for _, path, _ in ui.TOP_NAV_ITEMS]
            + [path for _, path, _ in ui.DOMAIN_NAV_ITEMS]
            + ["pages/08_Genie_Assistant.py"]
            + [item["page_path"] for item in dp_mod.DATA_PRODUCTS]
        )
        for rel_path in expected_paths:
            self.assertTrue(
                (APP_DIR / rel_path).is_file(),
                f"Missing Streamlit page target: {rel_path}",
            )

    def test_render_header_links_all_top_and_domain_pages(self) -> None:
        ui.apply_theme()
        ui.render_header("Portfolio")

        expected = {path for _, path, _ in ui.TOP_NAV_ITEMS + ui.DOMAIN_NAV_ITEMS}
        self.assertTrue(expected.issubset(set(st_stub.captured_links)))

        for html_block in st_stub.captured_markdown:
            for line in html_block.splitlines():
                self.assertFalse(
                    line.startswith("    "),
                    f"Unexpected 4-space indented HTML line: {line!r}",
                )

    def test_agents_handle_empty_tables_gracefully(self) -> None:
        original_query = agents.query_table
        try:
            agents.query_table = lambda table_name, limit=10: pd.DataFrame()
            for key in ["portfolio", "market", "maintenance", "capex"]:
                res = agents.run_agent_analysis(key, "Test empty table")
                self.assertIn("Implemented", res.implementation_mode)
                self.assertTrue(res.source_tables)
        finally:
            agents.query_table = original_query


if __name__ == "__main__":
    unittest.main()


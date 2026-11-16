"""Navigation route integrity, UI contrast helper, and agent safety tests."""

import unittest

import pandas as pd

from tests._test_env import APP_DIR, install_test_stubs, load_app_module

st_stub = install_test_stubs()
import utils.agents as agents  # noqa: E402
import utils.ui as ui  # noqa: E402

dp_mod = load_app_module("pages/08_Data_Platform_Health.py", "test_dp_mod")


class TestNavigationAndAgents(unittest.TestCase):
    """Verify all navigation page targets exist and specialist agents degrade safely."""

    def setUp(self) -> None:
        st_stub.captured_links.clear()
        st_stub.captured_markdown.clear()

    def test_all_configured_page_files_exist(self) -> None:
        expected_paths = (
            [path for _, path, _ in ui.ALL_SAAS_PAGES]
            + [item["page_path"] for item in dp_mod.DATA_PRODUCTS]
        )
        for rel_path in expected_paths:
            self.assertTrue(
                (APP_DIR / rel_path).is_file(),
                f"Missing Streamlit page target: {rel_path}",
            )

    def test_render_header_links_all_top_and_domain_pages(self) -> None:
        ui.apply_theme()
        ui.render_header("Executive Overview")

        expected = {path for _, path, _ in ui.ALL_SAAS_PAGES}
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


    def test_button_backward_compatibility_with_older_streamlit(self) -> None:
        """Simulate older Streamlit runtime rejecting 'icon' and ensure safe wrapper degrades gracefully."""
        called_without_icon = []
        original_btn = ui._orig_st_button

        def legacy_button(label, *args, **kwargs):
            if "icon" in kwargs:
                raise TypeError("ButtonMixin.button() got an unexpected keyword argument 'icon'")
            called_without_icon.append(label)
            return True

        try:
            ui._orig_st_button = legacy_button
            res = ui._safe_st_button("Test Button", icon=":material/refresh:")
            self.assertTrue(res)
            self.assertEqual(called_without_icon, ["Test Button"])
        finally:
            ui._orig_st_button = original_btn

    def test_metric_css_and_kpi_visibility_rules(self) -> None:
        """Verify CSS contains anti-truncation and equal-height flex rules."""
        st_stub.captured_markdown.clear()
        ui.apply_theme()
        full_css = "\n".join(st_stub.captured_markdown)
        self.assertIn("div[data-testid=\"stMetricValue\"]", full_css)
        self.assertIn("overflow: visible !important", full_css)
        self.assertIn("padding-top: 4.5rem !important", full_css)
        self.assertIn("div[data-testid=\"stHorizontalBlock\"]", full_css)
        self.assertIn("align-items: stretch !important", full_css)

    def test_design_tokens_and_sidebar_spec(self) -> None:
        """Verify global enterprise design tokens and sidebar dimensions."""
        st_stub.captured_markdown.clear()
        ui.apply_theme()
        full_css = "\n".join(st_stub.captured_markdown)
        self.assertIn("--saas-bg: #F7F9FC", full_css)
        self.assertIn("--saas-sidebar: #172536", full_css)
        self.assertIn("--saas-green: #0F9D83", full_css)
        self.assertIn("--saas-text-primary: #172B4D", full_css)
        self.assertIn("--saas-text-secondary: #64748B", full_css)
        self.assertIn("--saas-text-muted: #94A3B8", full_css)
        self.assertIn("--saas-border: #E2E8F0", full_css)
        self.assertIn("min-width: 250px !important", full_css)
        self.assertIn("key*=\"genie_suggest\"", full_css)


if __name__ == "__main__":
    unittest.main()


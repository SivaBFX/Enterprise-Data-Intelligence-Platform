"""KPI reconciliation, filter behavior, and empty-data handling tests."""

from decimal import Decimal
import unittest

import pandas as pd

from tests._test_env import install_test_stubs, load_app_module

install_test_stubs()
import utils.database as db  # noqa: E402

app_mod = load_app_module("app.py", "test_app_mod")
market_mod = load_app_module("pages/03_Market_Intelligence.py", "test_market_mod")
prop_mod = load_app_module("pages/02_Property_Intelligence.py", "test_prop_mod")
maint_mod = load_app_module("pages/04_Maintenance_Intelligence.py", "test_maint_mod")
capex_mod = load_app_module("pages/05_Investment_CapEx.py", "test_capex_mod")


class TestKPIReconciliationAndFilters(unittest.TestCase):
    """Verify cross-page KPI reconciliation, filters, and zero/empty safety."""

    def test_portfolio_and_market_kpi_reconciliation(self) -> None:
        # Two markets summing exactly to portfolio totals for 2026-09
        market_df = pd.DataFrame(
            [
                {
                    "month": "2026-09-01",
                    "market_name": "Austin",
                    "region": "South",
                    "property_count": 150,
                    "total_occupied_days": 4200,
                    "total_service_days": 4500,
                    "total_rental_revenue": Decimal("260000"),
                    "total_opex": Decimal("90000"),
                    "total_noi": Decimal("170000"),
                    "net_operating_revenue": Decimal("260000"),
                },
                {
                    "month": "2026-09-01",
                    "market_name": "Denver",
                    "region": "West",
                    "property_count": 150,
                    "total_occupied_days": 3900,
                    "total_service_days": 4500,
                    "total_rental_revenue": Decimal("200000"),
                    "total_opex": Decimal("90000"),
                    "total_noi": Decimal("110000"),
                    "net_operating_revenue": Decimal("200000"),
                },
            ]
        )
        market_df = db.coerce_numeric(market_df, market_mod.NUMERIC_COLS)
        mkt_kpis = market_mod._aggregate_market_slice(market_df)

        portfolio_df = pd.DataFrame(
            [
                {
                    "month_year": "2026-09",
                    "total_properties": 300,
                    "total_occupied_days": 8100,
                    "total_service_days": 9000,
                    "total_rental_revenue": 460000.0,
                    "total_noi": 280000.0,
                    "occupancy_pct": 90.0,
                }
            ]
        )
        port_summary = app_mod.compute_portfolio_summary(
            portfolio_df=portfolio_df,
            maintenance_df=pd.DataFrame(),
            capex_totals={"total_capex_amount": 50000.0, "investment_count": 5},
        )

        self.assertAlmostEqual(mkt_kpis["occupancy"], port_summary["occupancy"], places=4)
        self.assertAlmostEqual(mkt_kpis["revenue"], port_summary["latest_revenue"], places=2)
        self.assertAlmostEqual(mkt_kpis["noi"], port_summary["latest_noi"], places=2)
        self.assertEqual(int(mkt_kpis["properties"]), 300)

    def test_property_filters_and_empty_match(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "property_id": "PROP-001",
                    "market_name": "Austin",
                    "property_type": "Single Family",
                    "bedrooms": 3.0,
                    "total_occupied_days": 340.0,
                    "total_service_days": 365.0,
                    "overall_occupancy_pct": 93.15,
                    "total_rental_revenue": 36000.0,
                    "total_noi": 22000.0,
                    "avg_monthly_noi": 1833.33,
                    "operating_expense_ratio_pct": 38.9,
                },
                {
                    "property_id": "PROP-002",
                    "market_name": "Denver",
                    "property_type": "Townhome",
                    "bedrooms": 2.0,
                    "total_occupied_days": 0.0,
                    "total_service_days": 0.0,
                    "overall_occupancy_pct": 0.0,
                    "total_rental_revenue": 0.0,
                    "total_noi": -500.0,
                    "avg_monthly_noi": -41.67,
                    "operating_expense_ratio_pct": 0.0,
                },
            ]
        )
        matched = prop_mod._apply_property_filters(df, "austin", "Austin", "Single Family", 3.0)
        self.assertEqual(len(matched), 1)
        empty = prop_mod._apply_property_filters(df, "nonexistent", "All Markets", "All Types", "All")
        self.assertTrue(empty.empty)
        # Zero-denominator KPI calculation must not raise
        cards = prop_mod._compute_property_kpis(df.iloc[[1]], total_portfolio_count=2)
        self.assertEqual(cards[1]["value"], "0.00%")

    def test_maintenance_weighted_completion_zero_safe(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "property_id": "P-1",
                    "market_name": "Austin",
                    "region": "South",
                    "total_work_orders": 0.0,
                    "total_maintenance_cost": 0.0,
                    "avg_work_order_cost": 0.0,
                    "avg_completion_days": 0.0,
                    "open_work_orders": 0.0,
                    "in_progress_work_orders": 0.0,
                    "completed_work_orders": 0.0,
                    "cancelled_work_orders": 0.0,
                    "active_backlog": 0.0,
                }
            ]
        )
        summary = maint_mod._compute_maintenance_summary(df)
        self.assertEqual(summary["weighted_completion"], 0.0)
        self.assertEqual(summary["completion_rate"], 0.0)

    def test_capex_filters_and_summary(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "market_id": 1,
                    "market_name": "Austin",
                    "region": "South",
                    "property_id": "PROP-001",
                    "capex_month": "2026-09",
                    "category": "Roofing",
                    "investment_count": 2,
                    "total_capex_amount": 20000.0,
                    "avg_capex_amount": 10000.0,
                },
                {
                    "market_id": 2,
                    "market_name": "Denver",
                    "region": "West",
                    "property_id": "PROP-002",
                    "capex_month": "2026-08",
                    "category": "HVAC",
                    "investment_count": 1,
                    "total_capex_amount": 5000.0,
                    "avg_capex_amount": 5000.0,
                },
            ]
        )
        filtered = capex_mod._apply_capex_filters(df, "roof", "Austin", "Roofing", "2026-09")
        self.assertEqual(len(filtered), 1)
        summary = capex_mod._compute_capex_summary(filtered)
        self.assertEqual(summary["total_investment"], 20000.0)
        self.assertEqual(summary["weighted_avg"], 10000.0)


if __name__ == "__main__":
    unittest.main()


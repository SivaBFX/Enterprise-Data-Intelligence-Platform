"""Performance Analytics enterprise multi-metric historical analysis page.

Provides longitudinal performance trends, cross-metric comparisons (Revenue vs. NOI vs. OpEx),
weighted occupancy trajectories, and regional market performance dispersion.
"""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from utils.database import (
    coerce_numeric,
    get_table_freshness,
    query_table,
    resolve_table_name,
)
from utils.ui import (
    apply_theme,
    chart_card,
    render_empty_state,
    render_formatted_table,
    render_header,
    render_insight_card,
    render_kpi_row,
    render_page_header,
    render_section_header,
    status_badge_html,
)

st.set_page_config(
    page_title="Performance Analytics · Enterprise SaaS",
    page_icon=":material/insights:",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_performance_datasets() -> Dict[str, Any]:
    """Load monthly portfolio and market Gold records for multi-period trend analytics."""
    port_tbl = resolve_table_name("PORTFOLIO_KPIS_TABLE", "workspace.gold.gold_portfolio_kpis")
    mkt_tbl = resolve_table_name("MARKET_MONTHLY_TABLE", "workspace.gold.gold_market_monthly")

    port_df = query_table(port_tbl, limit=1000)
    mkt_df = query_table(mkt_tbl, limit=2000)

    if not port_df.empty:
        port_df = coerce_numeric(
            port_df,
            [
                "total_properties",
                "total_occupied_days",
                "total_service_days",
                "total_rental_revenue",
                "total_noi",
            ],
        )
        port_df["occupancy_pct"] = (
            port_df["total_occupied_days"]
            / port_df["total_service_days"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)
        port_df["noi_margin_pct"] = (
            port_df["total_noi"]
            / port_df["total_rental_revenue"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)
        port_df["calculated_opex"] = (
            port_df["total_rental_revenue"] - port_df["total_noi"]
        ).clip(lower=0.0)

    if not mkt_df.empty:
        mkt_df = coerce_numeric(
            mkt_df,
            [
                "property_count",
                "total_occupied_days",
                "total_service_days",
                "total_rental_revenue",
                "total_noi",
                "total_opex",
            ],
        )
        mkt_df["occupancy_pct"] = (
            mkt_df["total_occupied_days"]
            / mkt_df["total_service_days"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)
        mkt_df["noi_margin_pct"] = (
            mkt_df["total_noi"]
            / mkt_df["total_rental_revenue"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)

    return {
        "portfolio_df": port_df,
        "market_df": mkt_df,
        "freshness": get_table_freshness(port_tbl),
        "table_name": port_tbl,
    }


def _build_performance_kpi_cards(port_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Compute executive performance KPI cards across the historical cohort."""
    total_rev = float(port_df["total_rental_revenue"].sum())
    total_noi = float(port_df["total_noi"].sum())
    total_occ_days = float(port_df["total_occupied_days"].sum())
    total_svc_days = float(port_df["total_service_days"].sum())
    weighted_occ = (total_occ_days / total_svc_days * 100.0) if total_svc_days else 0.0
    overall_margin = (total_noi / total_rev * 100.0) if total_rev else 0.0
    latest_props = int(port_df.iloc[-1]["total_properties"]) if not port_df.empty else 0

    return [
        {
            "label": "Cumulative Rental Revenue",
            "value": f"${total_rev:,.2f}",
            "delta": f"{len(port_df):,} Reporting Months",
            "delta_tone": "info",
            "caption": "Aggregate rental income across cohort",
        },
        {
            "label": "Cumulative Net Operating Income",
            "value": f"${total_noi:,.2f}",
            "delta": f"{overall_margin:.1f}% Margin",
            "delta_tone": "success" if overall_margin >= 60 else "neutral",
            "caption": "Gross revenue minus operating expenses",
        },
        {
            "label": "Cohort Weighted Occupancy",
            "value": f"{weighted_occ:.2f}%",
            "delta": "Above Target" if weighted_occ >= 90 else "Monitor",
            "delta_tone": "success" if weighted_occ >= 90 else "warning",
            "caption": f"{int(total_occ_days):,} occupied / {int(total_svc_days):,} service days",
        },
        {
            "label": "Active Portfolio Assets",
            "value": f"{latest_props:,}",
            "delta": "Stabilized Base",
            "delta_tone": "neutral",
            "caption": "Residential units under active management",
        },
    ]


def main() -> None:
    """Render the Performance Analytics enterprise page."""
    apply_theme()
    render_header("Performance Analytics")

    try:
        with st.spinner("Aggregating historical performance analytics from Databricks Gold tables..."):
            data = load_performance_datasets()

        port_df = data["portfolio_df"]
        mkt_df = data["market_df"]
        freshness = data["freshness"]
        table_name = data.get("table_name", "workspace.gold.gold_portfolio_kpis")

        if port_df.empty:
            render_page_header(
                title="Performance Analytics",
                description="Longitudinal multi-metric performance trends across revenue, NOI, and occupancy.",
                domain_label="Analytics & AI",
                status_text="Awaiting Synchronization",
                status_tone="warning",
            )
            with st.container(border=True):
                st.markdown(
                    f'<div style="padding:1rem 0.5rem;">'
                    f'<strong style="font-size:1.05rem;color:#202B38;">Gold Performance Data Pipeline Awaiting Execution</strong>'
                    f'<p style="color:#758294;margin:6px 0 14px 0;font-size:0.88rem;">'
                    f'The target table <code>{table_name}</code> does not currently contain completed monthly rollups. '
                    f'Once the Lakeflow / Delta pipeline completes its monthly aggregation run, multi-year performance trends, '
                    f'revenue vs. OpEx comparisons, and regional variance trajectories will populate automatically here.'
                    f'</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                c1, c2 = st.columns(2)
                with c1:
                    st.page_link("app.py", label="Return to Executive Overview", icon=":material/dashboard:")
                with c2:
                    st.page_link("pages/08_Data_Platform_Health.py", label="Inspect Unity Catalog Health", icon=":material/health_and_safety:")
            return

        freshness_badge = (
            f"Gold Synced · {freshness['timestamp']}"
            if freshness.get("status") == "available"
            else "Gold Layer Connected"
        )

        render_page_header(
            title="Performance Analytics",
            description="Longitudinal trend analysis: monthly revenue trajectory, NOI margins, and regional performance dispersion.",
            domain_label="Analytics & AI",
            reporting_period=f"{len(port_df):,} Reporting Months",
            status_text=freshness_badge,
            status_tone="success",
        )

        render_section_header(
            title="Executive Performance Summary",
            subtitle=f"Aggregated financial and operational trajectory across {len(port_df):,} monthly reporting periods.",
        )
        render_kpi_row(_build_performance_kpi_cards(port_df))

        sorted_port = port_df.sort_values("month_year").set_index("month_year")

        c_left, c_right = st.columns(2)
        with c_left:
            with chart_card(
                title="Revenue, NOI & OpEx Trajectory",
                subtitle="Historical progression of gross rental revenue, NOI, and operating expenses",
            ):
                chart_cols = [c for c in ["total_rental_revenue", "total_noi", "calculated_opex"] if c in sorted_port.columns]
                st.line_chart(sorted_port[chart_cols])

        with c_right:
            with chart_card(
                title="Weighted Occupancy Rate Trend (%)",
                subtitle="Monthly occupancy percentage benchmarked against portfolio target (90%)",
            ):
                st.line_chart(sorted_port["occupancy_pct"], color="#119B78")

        if not mkt_df.empty:
            render_section_header(
                title="Regional Market Performance Benchmark",
                subtitle="Comparing cumulative revenue and operating margins across geographic markets.",
            )
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                with chart_card(
                    title="Rental Revenue by Market ($)",
                    subtitle="Aggregate market revenue contribution across all active periods",
                ):
                    mkt_rev = mkt_df.groupby("market_name")["total_rental_revenue"].sum().sort_values(ascending=False)
                    st.bar_chart(mkt_rev, color="#3478D4")

            with col_m2:
                with chart_card(
                    title="Average NOI Margin by Market (%)",
                    subtitle="Mean operating efficiency across residential market clusters",
                ):
                    mkt_noi = mkt_df.groupby("market_name")["noi_margin_pct"].mean().sort_values(ascending=False)
                    st.bar_chart(mkt_noi, color="#119B78")

        render_section_header(
            title="Portfolio Performance Insights",
            subtitle="Deterministic observations derived from historical Gold analytics.",
        )
        i1, i2 = st.columns(2)
        with i1:
            best_month = sorted_port["total_rental_revenue"].idxmax()
            best_rev = float(sorted_port["total_rental_revenue"].max())
            render_insight_card(
                title=f"Peak Revenue Period: {best_month}",
                body=f"Portfolio achieved peak gross rental revenue of ${best_rev:,.2f} with strong collection efficiency across residential assets.",
                tone="success",
                tag="Growth Milestone",
            )
        with i2:
            avg_margin = float(sorted_port["noi_margin_pct"].mean())
            render_insight_card(
                title=f"Portfolio NOI Margin: {avg_margin:.1f}% Avg",
                body=f"Net operating income margin averaged {avg_margin:.1f}% across all evaluated periods, reflecting stable cost controls.",
                tone="info",
                tag="Margin Stability",
            )

        with st.expander("View Monthly Performance Summary Records"):
            render_formatted_table(
                port_df.sort_values("month_year", ascending=False),
                column_labels={
                    "month_year": "Reporting Month",
                    "total_properties": "Total Properties",
                    "occupancy_pct": "Occupancy (%)",
                    "total_rental_revenue": "Rental Revenue ($)",
                    "total_noi": "Total NOI ($)",
                    "noi_margin_pct": "NOI Margin (%)",
                },
                formats={
                    "occupancy_pct": "{:.2f}%",
                    "total_rental_revenue": "${:,.2f}",
                    "total_noi": "${:,.2f}",
                    "noi_margin_pct": "{:.2f}%",
                },
            )

    except Exception as exc:
        render_page_header(
            title="Performance Analytics",
            description="Historical performance trends.",
            domain_label="Analytics & AI",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load performance analytics.")
        st.exception(exc)


if __name__ == "__main__":
    main()

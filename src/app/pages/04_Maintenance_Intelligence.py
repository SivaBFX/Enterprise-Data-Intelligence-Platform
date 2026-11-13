"""Maintenance Intelligence enterprise operations dashboard.

Provides operations-focused KPI cards, work-order status breakdown,
maintenance expenditure by market, and detailed work order records.
"""

from typing import Any, Dict, List

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
)

NUMERIC_COLS = [
    "total_work_orders",
    "total_maintenance_cost",
    "avg_work_order_cost",
    "avg_completion_days",
    "open_work_orders",
    "in_progress_work_orders",
    "completed_work_orders",
    "cancelled_work_orders",
]

st.set_page_config(
    page_title="Maintenance Intelligence · Enterprise SaaS",
    page_icon=":material/build:",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_maintenance_data() -> Dict[str, Any]:
    """Load Gold maintenance summary data and Delta freshness metadata."""
    table_name = resolve_table_name(
        "MAINTENANCE_TABLE", "workspace.gold.gold_maintenance_summary"
    )
    df = query_table(table_name, limit=2000)
    if not df.empty:
        df = coerce_numeric(df, NUMERIC_COLS)
        df["active_backlog"] = df["open_work_orders"] + df["in_progress_work_orders"]
    freshness = get_table_freshness(table_name)
    return {"table_name": table_name, "df": df, "freshness": freshness}


def _compute_maintenance_summary(filtered: pd.DataFrame) -> Dict[str, Any]:
    """Compute portfolio/filtered work-order KPIs preserving weighted completion logic."""
    total_orders = int(filtered["total_work_orders"].sum())
    total_cost = float(filtered["total_maintenance_cost"].sum())
    open_orders = int(filtered["open_work_orders"].sum())
    in_progress_orders = int(filtered["in_progress_work_orders"].sum())
    completed_orders = int(filtered["completed_work_orders"].sum())
    cancelled_orders = int(filtered["cancelled_work_orders"].sum())
    active_backlog = open_orders + in_progress_orders

    avg_cost = (total_cost / total_orders) if total_orders else 0.0

    completed_weight = float((filtered["avg_completion_days"] * filtered["completed_work_orders"]).sum())
    weighted_completion_days = (completed_weight / completed_orders) if completed_orders else 0.0
    completion_rate_pct = (completed_orders / total_orders * 100.0) if total_orders else 0.0

    return {
        "total_properties": int(filtered["property_id"].nunique()),
        "total_work_orders": total_orders,
        "total_cost": total_cost,
        "open_orders": open_orders,
        "in_progress_orders": in_progress_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "active_backlog": active_backlog,
        "avg_cost": avg_cost,
        "weighted_completion": weighted_completion_days,
        "weighted_completion_days": weighted_completion_days,
        "completion_rate": completion_rate_pct,
        "completion_rate_pct": completion_rate_pct,
    }


def _build_maintenance_kpi_cards(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Construct 8 operations KPI cards matching Master Prompt requirements."""
    return [
        {
            "label": "Total Work Orders",
            "value": f"{summary['total_work_orders']:,}",
            "delta": f"{summary['total_properties']:,} properties",
            "delta_tone": "neutral",
            "caption": "All recorded work orders",
        },
        {
            "label": "Open Work Orders",
            "value": f"{summary['open_orders']:,}",
            "delta": "Awaiting Triage" if summary['open_orders'] > 0 else "Clear",
            "delta_tone": "warning" if summary['open_orders'] > 0 else "success",
            "caption": "Unassigned or pending review",
        },
        {
            "label": "In-Progress Orders",
            "value": f"{summary['in_progress_orders']:,}",
            "delta": f"{summary['active_backlog']:,} active backlog",
            "delta_tone": "info",
            "caption": "Currently under repair",
        },
        {
            "label": "Completed Orders",
            "value": f"{summary['completed_orders']:,}",
            "delta": f"{summary['completion_rate_pct']:.1f}% resolution",
            "delta_tone": "success",
            "caption": "Successfully resolved",
        },
        {
            "label": "Cancelled Orders",
            "value": f"{summary['cancelled_orders']:,}",
            "delta": "Voided / Duplicate",
            "delta_tone": "neutral",
            "caption": "Withdrawn work orders",
        },
        {
            "label": "Total Maintenance Cost",
            "value": f"${summary['total_cost']:,.2f}",
            "delta": f"${(summary['total_cost'] / summary['total_properties'] if summary['total_properties'] else 0):,.0f} / asset",
            "delta_tone": "neutral",
            "caption": "Cumulative repair spend",
        },
        {
            "label": "Avg Work Order Cost",
            "value": f"${summary['avg_cost']:,.2f}",
            "delta": "Per work order",
            "delta_tone": "neutral",
            "caption": "Mean expenditure per ticket",
        },
        {
            "label": "Avg Completion Days",
            "value": f"{summary['weighted_completion_days']:.1f}d",
            "delta": "SLA Benchmark",
            "delta_tone": "success" if summary['weighted_completion_days'] <= 7 else "warning",
            "caption": "Weighted resolution time",
        },
    ]


def main() -> None:
    """Render the Maintenance Intelligence enterprise page."""
    apply_theme()
    render_header("Maintenance Intelligence")

    try:
        with st.spinner("Loading maintenance operations data from Databricks Gold layer..."):
            payload = load_maintenance_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Maintenance Intelligence",
                description="Monitor work-order volume, resolution cycle times, and maintenance costs.",
                domain_label="Maintenance Intelligence",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No Maintenance Data Available",
                f"Table {payload['table_name']} returned zero rows.",
                tone="warning",
            )
            st.stop()

        freshness = payload["freshness"]
        freshness_badge = (
            f"Gold Synced · {freshness['timestamp']}"
            if freshness.get("status") == "available"
            else "Gold Layer Connected"
        )

        with st.container(border=True):
            f1, f2, f3 = st.columns([2.0, 1.6, 0.9])
            with f1:
                search_prop = st.text_input("Search Property ID", placeholder="e.g. PROP-010...")
            with f2:
                mkts = ["All Markets"] + sorted(df["market_name"].dropna().unique().tolist())
                selected_market = st.selectbox("Market Filter", mkts)
            with f3:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", key="maint_refresh_btn", use_container_width=True):
                    load_maintenance_data.clear()
                    st.rerun()

        filtered = df.copy()
        if selected_market != "All Markets":
            filtered = filtered[filtered["market_name"] == selected_market]
        if search_prop.strip():
            filtered = filtered[filtered["property_id"].astype(str).str.contains(search_prop.strip(), case=False, regex=False)]

        render_page_header(
            title="Maintenance Intelligence",
            description="Operational maintenance command center: work-order backlogs, completion SLAs, and cost drivers.",
            domain_label="Portfolio Intelligence",
            reporting_period=f"{len(filtered):,} of {len(df):,} Properties",
            status_text=freshness_badge,
            status_tone="success",
        )

        summary = _compute_maintenance_summary(filtered)
        render_section_header(
            title="Operational Maintenance KPIs",
            subtitle=f"Aggregated metrics for {selected_market}.",
            badge=f"{summary['active_backlog']:,} Active Tickets",
            badge_tone="warning" if summary['active_backlog'] > 0 else "success",
        )
        render_kpi_row(_build_maintenance_kpi_cards(summary))

        with chart_card(
            title="Maintenance Expenditure by Market",
            subtitle="Comparing total repair expenditure across markets",
        ):
            mkt_spend = filtered.groupby("market_name")["total_maintenance_cost"].sum().sort_values(ascending=False)
            st.bar_chart(mkt_spend, color="#3478D4")

        with st.expander(f"View Detailed Property Maintenance Records ({len(filtered):,} records)"):
            render_formatted_table(
                filtered.sort_values("total_maintenance_cost", ascending=False),
                column_labels={
                    "property_id": "Property ID",
                    "market_name": "Market",
                    "total_work_orders": "Total Orders",
                    "open_work_orders": "Open",
                    "in_progress_work_orders": "In Progress",
                    "completed_work_orders": "Completed",
                    "total_maintenance_cost": "Total Spend ($)",
                    "avg_work_order_cost": "Avg Cost ($)",
                    "avg_completion_days": "Avg Days",
                },
                formats={
                    "total_maintenance_cost": "${:,.2f}",
                    "avg_work_order_cost": "${:,.2f}",
                    "avg_completion_days": "{:.1f}",
                },
            )

    except Exception as exc:
        render_page_header(
            title="Maintenance Intelligence",
            description="Operations maintenance intelligence.",
            domain_label="Maintenance Intelligence",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load maintenance intelligence.")
        st.exception(exc)


if __name__ == "__main__":
    main()

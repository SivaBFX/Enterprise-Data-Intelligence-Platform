"""Maintenance Analytics AI Studio page (Milestone 5)."""

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
    page_title="Maintenance Analytics · AI Studio",
    page_icon="🔧",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_maintenance_data() -> Dict[str, Any]:
    """Load Gold maintenance summary data and Delta freshness metadata."""
    table_name = resolve_table_name(
        "MAINTENANCE_TABLE", "workspace.gold.gold_maintenance_summary"
    )
    df = query_table(table_name, limit=1000)
    if not df.empty:
        df = coerce_numeric(df, NUMERIC_COLS)
        df["active_backlog"] = df["open_work_orders"] + df["in_progress_work_orders"]
    freshness = get_table_freshness(table_name)
    return {"table_name": table_name, "df": df, "freshness": freshness}


def _compute_maintenance_summary(filtered: pd.DataFrame) -> Dict[str, Any]:
    """Compute portfolio/filtered work-order KPIs preserving weighted completion logic."""
    total_orders = int(filtered["total_work_orders"].sum())
    completed = int(filtered["completed_work_orders"].sum())
    open_orders = int(filtered["open_work_orders"].sum())
    in_progress = int(filtered["in_progress_work_orders"].sum())
    cancelled = int(filtered["cancelled_work_orders"].sum())
    active_backlog = open_orders + in_progress

    total_cost = float(filtered["total_maintenance_cost"].sum())
    avg_wo_cost = (total_cost / total_orders) if total_orders > 0 else 0.0
    completion_rate = (completed / total_orders * 100.0) if total_orders > 0 else 0.0
    open_share = (open_orders / total_orders * 100.0) if total_orders > 0 else 0.0

    completed_count = float(filtered["completed_work_orders"].sum())
    if completed_count > 0:
        weighted_completion = (
            float((filtered["avg_completion_days"] * filtered["completed_work_orders"]).sum())
            / completed_count
        )
    else:
        weighted_completion = 0.0

    cards: List[Dict[str, Any]] = [
        {
            "label": "Total Work Orders",
            "value": f"{total_orders:,}",
            "delta": f"{int(filtered['property_id'].nunique()):,} properties",
            "delta_tone": "neutral",
            "caption": "All work-order statuses",
            "icon": "📋",
        },
        {
            "label": "Completed Work Orders",
            "value": f"{completed:,}",
            "delta": f"{completion_rate:.1f}% completion",
            "delta_tone": "success" if completion_rate >= 75 else "warning",
            "caption": f"{cancelled:,} cancelled",
            "icon": "✅",
        },
        {
            "label": "Total Maintenance Cost",
            "value": f"${total_cost:,.0f}",
            "delta": f"${avg_wo_cost:,.2f} / WO",
            "delta_tone": "info",
            "caption": "Cumulative property maintenance spend",
            "icon": "💵",
        },
        {
            "label": "Open Work Orders",
            "value": f"{open_orders:,}",
            "delta": f"{open_share:.1f}% of total",
            "delta_tone": "warning" if open_orders > 0 else "success",
            "caption": "Awaiting assignment or start",
            "icon": "⏳",
        },
        {
            "label": "In Progress",
            "value": f"{in_progress:,}",
            "delta": f"{active_backlog:,} total active",
            "delta_tone": "warning" if active_backlog > 0 else "success",
            "caption": "Open + In Progress backlog",
            "icon": "🔧",
        },
        {
            "label": "Avg. Completion Time",
            "value": f"{weighted_completion:.1f} days",
            "delta": "Weighted SLA",
            "delta_tone": "success" if weighted_completion <= 5.0 else "warning",
            "caption": "Weighted by completed work orders",
            "icon": "⏱️",
        },
    ]

    return {
        "cards": cards,
        "total_orders": total_orders,
        "completed": completed,
        "open_orders": open_orders,
        "in_progress": in_progress,
        "cancelled": cancelled,
        "active_backlog": active_backlog,
        "total_cost": total_cost,
        "avg_wo_cost": avg_wo_cost,
        "completion_rate": completion_rate,
        "weighted_completion": weighted_completion,
    }


def _build_market_maintenance_summary(filtered: pd.DataFrame) -> pd.DataFrame:
    """Aggregate maintenance metrics by market including weighted completion time."""
    work = filtered.copy()
    work["weighted_days_num"] = work["avg_completion_days"] * work["completed_work_orders"]

    market_summary = (
        work.groupby("market_name", as_index=False)
        .agg(
            Properties=("property_id", "nunique"),
            Total_Work_Orders=("total_work_orders", "sum"),
            Completed=("completed_work_orders", "sum"),
            Open=("open_work_orders", "sum"),
            In_Progress=("in_progress_work_orders", "sum"),
            Cancelled=("cancelled_work_orders", "sum"),
            Maintenance_Cost=("total_maintenance_cost", "sum"),
            _weighted_num=("weighted_days_num", "sum"),
        )
    )

    market_summary["Completion_Rate_%"] = (
        market_summary["Completed"]
        / market_summary["Total_Work_Orders"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    market_summary["Weighted_Avg_Days"] = (
        market_summary["_weighted_num"]
        / market_summary["Completed"].replace(0, pd.NA)
    ).fillna(0.0)
    market_summary["Avg_Cost_Per_WO"] = (
        market_summary["Maintenance_Cost"]
        / market_summary["Total_Work_Orders"].replace(0, pd.NA)
    ).fillna(0.0)

    return market_summary.drop(columns=["_weighted_num"]).sort_values(
        "Maintenance_Cost", ascending=False
    )


def _render_status_and_completion(
    summary: Dict[str, Any],
    market_summary: pd.DataFrame,
) -> None:
    """Render work-order status analysis and completion performance by market."""
    render_section_header(
        title="Work-Order Status & Completion Performance",
        subtitle="Volume distribution across lifecycle states and completion efficiency by market.",
        badge=f"{summary['completion_rate']:.1f}% Completion Rate",
        badge_tone="success" if summary["completion_rate"] >= 75 else "warning",
    )

    left, right = st.columns(2)
    with left:
        with chart_card(
            title="Work-Order Status Breakdown",
            subtitle="Distribution across Completed, Open, In Progress, and Cancelled states",
            badge=f"{summary['total_orders']:,} Total",
            badge_tone="info",
        ):
            status_df = pd.DataFrame(
                {
                    "Status": ["Completed", "Open", "In Progress", "Cancelled"],
                    "Work Orders": [
                        summary["completed"],
                        summary["open_orders"],
                        summary["in_progress"],
                        summary["cancelled"],
                    ],
                }
            )
            st.bar_chart(status_df.set_index("Status")[["Work Orders"]])
            total = summary["total_orders"] or 1
            st.caption(
                f"Completed: {summary['completed'] / total * 100:.1f}% · "
                f"Open: {summary['open_orders'] / total * 100:.1f}% · "
                f"In Progress: {summary['in_progress'] / total * 100:.1f}% · "
                f"Cancelled: {summary['cancelled'] / total * 100:.1f}%"
            )

    with right:
        with chart_card(
            title="Completion Performance by Market",
            subtitle="Weighted average days to complete work orders across markets",
            badge=f"Overall {summary['weighted_completion']:.1f}d",
            badge_tone="neutral",
        ):
            comp_bar = (
                market_summary.sort_values("Weighted_Avg_Days", ascending=False)
                .set_index("market_name")[["Weighted_Avg_Days"]]
                .rename(columns={"Weighted_Avg_Days": "Weighted Avg Completion (Days)"})
            )
            st.bar_chart(comp_bar)


def _render_cost_and_market_comparison(
    filtered: pd.DataFrame,
    market_summary: pd.DataFrame,
    summary: Dict[str, Any],
) -> None:
    """Render maintenance cost concentration, market comparison, and summary table."""
    render_section_header(
        title="Maintenance Cost Analysis & Market Comparison",
        subtitle="Spend concentration across markets and highest-cost properties (property-level Gold summary).",
        badge=f"${summary['total_cost']:,.0f} Total Spend",
        badge_tone="neutral",
    )

    c_left, c_right = st.columns(2)
    with c_left:
        with chart_card(
            title="Maintenance Cost by Market",
            subtitle="Cumulative maintenance expenditure ranked by market ($)",
            badge=f"{len(market_summary)} Markets",
            badge_tone="info",
        ):
            market_cost_bar = (
                market_summary.set_index("market_name")[["Maintenance_Cost"]]
                .rename(columns={"Maintenance_Cost": "Maintenance Cost ($)"})
            )
            st.bar_chart(market_cost_bar)

    with c_right:
        top_20 = filtered.nlargest(20, "total_maintenance_cost")
        top_20_share = (
            float(top_20["total_maintenance_cost"].sum()) / summary["total_cost"] * 100.0
            if summary["total_cost"] > 0
            else 0.0
        )
        with chart_card(
            title="Top 20 High-Cost Properties Spend Profile",
            subtitle="Cost concentration across the highest-expenditure properties ($)",
            badge=f"Top 20 = {top_20_share:.1f}%",
            badge_tone="warning" if top_20_share >= 35 else "neutral",
        ):
            prop_bar = (
                top_20.set_index("property_id")[["total_maintenance_cost"]]
                .rename(columns={"total_maintenance_cost": "Maintenance Cost ($)"})
            )
            st.bar_chart(prop_bar)

    with chart_card(
        title="Market Maintenance Summary",
        subtitle="Cross-market operational efficiency, completion rate, and unit work-order cost",
        badge="Benchmark",
        badge_tone="success",
    ):
        render_formatted_table(
            market_summary,
            column_labels={
                "market_name": "Market",
                "Properties": "Properties",
                "Total_Work_Orders": "Total WOs",
                "Completed": "Completed",
                "Open": "Open",
                "In_Progress": "In Progress",
                "Cancelled": "Cancelled",
                "Completion_Rate_%": "Completion %",
                "Weighted_Avg_Days": "Avg Days",
                "Avg_Cost_Per_WO": "Avg Cost / WO",
                "Maintenance_Cost": "Total Cost",
            },
            formats={
                "Properties": "{:,.0f}",
                "Total WOs": "{:,.0f}",
                "Completed": "{:,.0f}",
                "Open": "{:,.0f}",
                "In Progress": "{:,.0f}",
                "Cancelled": "{:,.0f}",
                "Completion %": "{:.1f}%",
                "Avg Days": "{:.1f}",
                "Avg Cost / WO": "${:,.2f}",
                "Total Cost": "${:,.2f}",
            },
        )


def _render_decision_queue_and_insights(
    filtered: pd.DataFrame,
    market_summary: pd.DataFrame,
    summary: Dict[str, Any],
) -> None:
    """Render maintenance decision queue tabs and calculated operational insights."""
    p90_cost = float(filtered["total_maintenance_cost"].quantile(0.9))
    high_cost_df = filtered[filtered["total_maintenance_cost"] >= p90_cost].sort_values(
        "total_maintenance_cost", ascending=False
    )
    backlog_df = filtered[filtered["active_backlog"] > 0].sort_values(
        ["active_backlog", "total_maintenance_cost"], ascending=[False, False]
    )
    slow_df = filtered[
        (filtered["completed_work_orders"] > 0)
        & (filtered["avg_completion_days"] > summary["weighted_completion"])
    ].sort_values("avg_completion_days", ascending=False)

    render_section_header(
        title="Maintenance Decision Queue & Insights",
        subtitle="High-cost assets, active work-order backlogs, and completion SLA exceptions.",
        badge=f"{len(high_cost_df)} Top-Decile Cost · {len(backlog_df)} Active Backlog",
        badge_tone="warning" if (len(high_cost_df) + len(backlog_df)) > 0 else "success",
    )

    with st.container(border=True):
        tab_cost, tab_backlog, tab_slow = st.tabs(
            [
                f"High-Cost Properties ({len(high_cost_df)})",
                f"Active Work-Order Backlog ({len(backlog_df)})",
                f"Above-Avg Completion Time ({len(slow_df)})",
            ]
        )

        common_cols = {
            "property_id": "Property ID",
            "market_name": "Market",
            "region": "Region",
            "total_work_orders": "Total WOs",
            "open_work_orders": "Open",
            "in_progress_work_orders": "In Progress",
            "completed_work_orders": "Completed",
            "total_maintenance_cost": "Total Cost",
            "avg_work_order_cost": "Avg Cost / WO",
            "avg_completion_days": "Avg Days",
        }
        common_formats = {
            "Total WOs": "{:,.0f}",
            "Open": "{:,.0f}",
            "In Progress": "{:,.0f}",
            "Completed": "{:,.0f}",
            "Total Cost": "${:,.2f}",
            "Avg Cost / WO": "${:,.2f}",
            "Avg Days": "{:.1f}",
        }

        with tab_cost:
            st.caption(
                f"Showing properties at or above the 90th percentile of maintenance spend (>= ${p90_cost:,.2f})."
            )
            render_formatted_table(high_cost_df, common_cols, common_formats)

        with tab_backlog:
            if backlog_df.empty:
                render_empty_state(
                    "No Open or In-Progress Backlog",
                    "All filtered properties currently have zero open or in-progress work orders.",
                    tone="success",
                )
            else:
                st.caption("Properties with open or in-progress work orders prioritized by backlog volume.")
                render_formatted_table(backlog_df, common_cols, common_formats)

        with tab_slow:
            if slow_df.empty:
                render_empty_state(
                    "All Properties Within Avg Completion Time",
                    f"No completed-order properties exceed the {summary['weighted_completion']:.1f}-day average.",
                    tone="success",
                )
            else:
                st.caption(
                    f"Properties exceeding the filtered weighted average completion time ({summary['weighted_completion']:.1f} days)."
                )
                render_formatted_table(slow_df, common_cols, common_formats)

    # Calculated insight cards
    top_mkt = market_summary.iloc[0]
    top_mkt_share = (
        float(top_mkt["Maintenance_Cost"]) / summary["total_cost"] * 100.0
        if summary["total_cost"] > 0
        else 0.0
    )
    fastest_mkt = market_summary.loc[market_summary["Weighted_Avg_Days"].idxmin()]
    slowest_mkt = market_summary.loc[market_summary["Weighted_Avg_Days"].idxmax()]
    p90_share = (
        float(high_cost_df["total_maintenance_cost"].sum()) / summary["total_cost"] * 100.0
        if summary["total_cost"] > 0
        else 0.0
    )

    i_col1, i_col2 = st.columns(2)
    with i_col1:
        render_insight_card(
            title="Market Spend & SLA Dispersion",
            body=(
                f"{top_mkt['market_name']} accounts for the largest share of maintenance spend at "
                f"${top_mkt['Maintenance_Cost']:,.0f} ({top_mkt_share:.1f}%). "
                f"Completion speed spans from {fastest_mkt['Weighted_Avg_Days']:.1f} days "
                f"({fastest_mkt['market_name']}) to {slowest_mkt['Weighted_Avg_Days']:.1f} days "
                f"({slowest_mkt['market_name']})."
            ),
            tone="info",
            tag="Calculated",
        )
    with i_col2:
        render_insight_card(
            title="Cost Concentration & Dispatch Action",
            body=(
                f"The {len(high_cost_df)} top-decile properties represent {p90_share:.1f}% of "
                f"filtered maintenance cost, and {summary['active_backlog']:,} work orders remain active "
                f"across {len(backlog_df)} properties. Prioritize vendor triage on high-backlog units "
                f"and evaluate preventive CapEx upgrades on repeat high-cost assets."
            ),
            tone="warning" if summary["active_backlog"] > 0 else "success",
            tag="Calculated + Action",
        )


def main() -> None:
    """Render the Maintenance Analytics AI Studio page."""
    apply_theme()
    render_header("Maintenance")

    try:
        with st.spinner("Loading maintenance analytics from Databricks Gold layer..."):
            payload = load_maintenance_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Maintenance Analytics",
                description="Work-order status, maintenance costs, and completion performance.",
                domain_label="Maintenance",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No Maintenance Data Found",
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

        # Filters card
        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([1.8, 1.4, 1.4, 0.9])
            with f1:
                search_prop = st.text_input(
                    "Search Property ID",
                    placeholder="e.g., PROP-001...",
                )
            with f2:
                markets = ["All"] + sorted(df["market_name"].dropna().unique().tolist())
                selected_market = st.selectbox("Market", markets)
            with f3:
                regions = ["All"] + sorted(df["region"].dropna().unique().tolist())
                selected_region = st.selectbox("Region", regions)
            with f4:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", use_container_width=True):
                    load_maintenance_data.clear()
                    st.rerun()

        filtered = df.copy()
        if selected_market != "All":
            filtered = filtered[filtered["market_name"] == selected_market]
        if selected_region != "All":
            filtered = filtered[filtered["region"] == selected_region]
        cleaned_search = (search_prop or "").strip().lower()
        if cleaned_search:
            filtered = filtered[
                filtered["property_id"].astype(str).str.lower().str.contains(cleaned_search, regex=False)
            ]

        render_page_header(
            title="Maintenance Analytics",
            description=(
                "Work-order lifecycle status, maintenance cost concentration, completion SLAs, "
                "and operational dispatch queues."
            ),
            domain_label="Maintenance · AI Studio",
            reporting_period=f"{filtered['property_id'].nunique():,} Properties · {selected_market} / {selected_region}",
            status_text=freshness_badge,
            status_tone="success",
        )

        if filtered.empty:
            render_empty_state(
                "No Records Match Selected Filters",
                "Adjust the property search, market, or region filters to view maintenance metrics.",
                tone="warning",
            )
            st.stop()

        summary = _compute_maintenance_summary(filtered)
        market_summary = _build_market_maintenance_summary(filtered)

        render_section_header(
            title="Work-Order & Cost Overview",
            subtitle="Aggregated work-order volumes, completion rates, and weighted SLA timing.",
            badge=f"{summary['total_orders']:,} Work Orders",
            badge_tone="neutral",
        )
        render_kpi_row(summary["cards"])

        _render_status_and_completion(summary=summary, market_summary=market_summary)
        _render_cost_and_market_comparison(
            filtered=filtered,
            market_summary=market_summary,
            summary=summary,
        )
        _render_decision_queue_and_insights(
            filtered=filtered,
            market_summary=market_summary,
            summary=summary,
        )

        with st.expander("View Property-Level Maintenance Details"):
            property_details = filtered[
                [
                    "property_id",
                    "market_name",
                    "region",
                    "total_work_orders",
                    "completed_work_orders",
                    "open_work_orders",
                    "in_progress_work_orders",
                    "cancelled_work_orders",
                    "total_maintenance_cost",
                    "avg_work_order_cost",
                    "avg_completion_days",
                ]
            ].sort_values("total_maintenance_cost", ascending=False)

            st.dataframe(
                property_details,
                use_container_width=True,
                hide_index=True,
            )

    except Exception as exc:
        render_page_header(
            title="Maintenance Analytics",
            description="Work-order status, maintenance costs, and completion performance.",
            domain_label="Maintenance",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load maintenance analytics.")
        st.exception(exc)


if __name__ == "__main__":
    main()

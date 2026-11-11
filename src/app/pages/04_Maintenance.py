
import streamlit as st
import pandas as pd

from utils.database import query_table
from utils.ui import apply_theme, render_header

st.set_page_config(
    page_title="Maintenance Analytics",
    page_icon="🔧",
    layout="wide"
)

apply_theme()
render_header("Maintenance")

#st.title("🔧 Maintenance Analytics")
#st.caption("Work-order status, maintenance costs and completion performance")

TABLE = "workspace.gold.gold_maintenance_summary"

try:
    df = query_table(TABLE, limit=1000)

    if df.empty:
        st.warning("No maintenance data found.")
        st.stop()

    # Normalize numeric columns
    numeric_columns = [
        "total_work_orders",
        "total_maintenance_cost",
        "avg_work_order_cost",
        "avg_completion_days",
        "open_work_orders",
        "in_progress_work_orders",
        "completed_work_orders",
        "cancelled_work_orders",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Filters
    st.subheader("Filters")

    col1, col2 = st.columns(2)

    markets = ["All"] + sorted(df["market_name"].dropna().unique().tolist())
    regions = ["All"] + sorted(df["region"].dropna().unique().tolist())

    with col1:
        selected_market = st.selectbox("Market", markets)

    with col2:
        selected_region = st.selectbox("Region", regions)

    filtered = df.copy()

    if selected_market != "All":
        filtered = filtered[filtered["market_name"] == selected_market]

    if selected_region != "All":
        filtered = filtered[filtered["region"] == selected_region]

    if filtered.empty:
        st.info("No records match the selected filters.")
        st.stop()

    # Portfolio-level metrics
    total_orders = int(filtered["total_work_orders"].sum())
    completed = int(filtered["completed_work_orders"].sum())
    open_orders = int(filtered["open_work_orders"].sum())
    in_progress = int(filtered["in_progress_work_orders"].sum())
    cancelled = int(filtered["cancelled_work_orders"].sum())

    total_cost = filtered["total_maintenance_cost"].sum()

    # Weighted average: completed work orders only
    completed_count = filtered["completed_work_orders"].sum()

    if completed_count > 0:
        weighted_completion = (
            filtered["avg_completion_days"]
            * filtered["completed_work_orders"]
        ).sum() / completed_count
    else:
        weighted_completion = 0

    st.divider()
    st.subheader("Maintenance Overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Work Orders", f"{total_orders:,}")
    c2.metric("Completed Work Orders", f"{completed:,}")
    c3.metric("Total Maintenance Cost", f"${total_cost:,.0f}")

    c4, c5, c6 = st.columns(3)
    c4.metric("Open Work Orders", f"{open_orders:,}")
    c5.metric("In Progress", f"{in_progress:,}")
    c6.metric("Avg. Completion Time", f"{weighted_completion:.1f} days")

    st.divider()

    # Status and market analysis
    left, right = st.columns(2)

    with left:
        st.subheader("Work Order Status")

        status_df = pd.DataFrame({
            "Status": ["Completed", "Open", "In Progress", "Cancelled"],
            "Work Orders": [
                completed,
                open_orders,
                in_progress,
                cancelled
            ]
        })

        st.bar_chart(
            status_df.set_index("Status"),
            y="Work Orders"
        )

    with right:
        st.subheader("Maintenance Cost by Market")

        market_cost = (
            filtered.groupby("market_name", as_index=False)
            ["total_maintenance_cost"].sum()
            .sort_values("total_maintenance_cost", ascending=False)
        )

        st.bar_chart(
            market_cost.set_index("market_name"),
            y="total_maintenance_cost"
        )

    st.divider()

    # Market-level summary
    st.subheader("Market Maintenance Summary")

    market_summary = (
        filtered.groupby("market_name", as_index=False)
        .agg(
            Properties=("property_id", "nunique"),
            Total_Work_Orders=("total_work_orders", "sum"),
            Completed=("completed_work_orders", "sum"),
            Open=("open_work_orders", "sum"),
            In_Progress=("in_progress_work_orders", "sum"),
            Cancelled=("cancelled_work_orders", "sum"),
            Maintenance_Cost=("total_maintenance_cost", "sum"),
        )
    )

    market_summary["Completion_Rate_%"] = (
        market_summary["Completed"]
        / market_summary["Total_Work_Orders"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(1)

    market_summary["Maintenance_Cost"] = (
        market_summary["Maintenance_Cost"].round(2)
    )

    st.dataframe(
        market_summary,
        use_container_width=True,
        hide_index=True
    )

    # Property-level details
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
            hide_index=True
        )

except Exception as e:
    st.error("Unable to load maintenance analytics.")
    st.exception(e)


import os
import streamlit as st
import pandas as pd

from utils.database import query_table

st.set_page_config(
    page_title="Market Analytics",
    page_icon="🌎",
    layout="wide"
)

st.title("Market Analytics")
st.caption("Compare residential property performance across markets")

table_name = os.getenv("MARKET_MONTHLY_TABLE")

try:
    with st.spinner("Loading market performance data..."):
        df = query_table(table_name, limit=1000)

    if df.empty:
        st.warning("No market data available.")
        st.stop()

    df["month"] = pd.to_datetime(df["month"])

    # Filters
    months = sorted(df["month"].dropna().unique(), reverse=True)
    market_names = ["All Markets"] + sorted(df["market_name"].unique())

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        selected_month = st.selectbox(
            "Reporting Month",
            months,
            format_func=lambda x: x.strftime("%B %Y")
        )

    with filter_col2:
        selected_market = st.selectbox(
            "Market",
            market_names
        )

    monthly = df[df["month"] == selected_month].copy()

    if selected_market != "All Markets":
        filtered = monthly[
            monthly["market_name"] == selected_market
        ].copy()

        trend_data = df[
            df["market_name"] == selected_market
        ].copy()
    else:
        filtered = monthly.copy()
        trend_data = df.copy()

    if filtered.empty:
        st.warning("No records found for the selected filters.")
        st.stop()

    # Aggregate KPI values
    properties = filtered["property_count"].sum()
    occupied_days = filtered["total_occupied_days"].sum()
    service_days = filtered["total_service_days"].sum()

    occupancy = (
        occupied_days / service_days * 100
        if service_days else 0
    )

    revenue = filtered["total_rental_revenue"].sum()
    noi = filtered["total_noi"].sum()
    opex = filtered["total_opex"].sum()
    net_operating_revenue = filtered["net_operating_revenue"].sum()

    expense_ratio = (
        opex / net_operating_revenue * 100
        if net_operating_revenue else 0
    )

    st.success("Market data loaded from Databricks Gold layer")

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Properties", f"{int(properties):,}")
    c2.metric("Weighted Occupancy", f"{occupancy:.2f}%")
    c3.metric("Rental Revenue", f"${revenue:,.2f}")
    c4.metric("Net Operating Income", f"${noi:,.2f}")

    c5, c6 = st.columns(2)

    c5.metric("Operating Expenses", f"${opex:,.2f}")
    c6.metric("Operating Expense Ratio", f"{expense_ratio:.2f}%")

    st.divider()

    # Market comparison
    st.subheader("Market Performance Comparison")

    comparison = monthly.copy()

    comparison["occupancy_pct"] = (
        comparison["total_occupied_days"]
        / comparison["total_service_days"] * 100
    )

    comparison = comparison[
        [
            "market_name",
            "region",
            "property_count",
            "occupancy_pct",
            "total_rental_revenue",
            "total_opex",
            "total_noi"
        ]
    ].rename(columns={
        "market_name": "Market",
        "region": "Region",
        "property_count": "Properties",
        "occupancy_pct": "Occupancy %",
        "total_rental_revenue": "Rental Revenue",
        "total_opex": "Operating Expenses",
        "total_noi": "NOI"
    })

    st.dataframe(
        comparison.style.format({
            "Occupancy %": "{:.2f}%",
            "Rental Revenue": "${:,.2f}",
            "Operating Expenses": "${:,.2f}",
            "NOI": "${:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Monthly trends
    st.subheader("Monthly Market Trends")

    trend = (
        trend_data.groupby("month", as_index=False)
        .agg({
            "total_rental_revenue": "sum",
            "total_noi": "sum",
            "total_occupied_days": "sum",
            "total_service_days": "sum"
        })
        .sort_values("month")
    )

    trend["occupancy_pct"] = (
        trend["total_occupied_days"]
        / trend["total_service_days"] * 100
    )

    trend["month"] = trend["month"].dt.strftime("%Y-%m")
    trend = trend.set_index("month")

    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("**Rental Revenue vs NOI**")
        st.line_chart(
            trend[["total_rental_revenue", "total_noi"]]
        )

    with chart2:
        st.markdown("**Weighted Occupancy Trend**")
        st.line_chart(trend[["occupancy_pct"]])

    with st.expander("View detailed market records"):
        st.dataframe(
            df.sort_values(
                ["month", "market_name"],
                ascending=[False, True]
            ),
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error("Unable to load market analytics.")
    st.exception(e)

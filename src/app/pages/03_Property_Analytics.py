
import os
import streamlit as st
import pandas as pd

from utils.database import query_table

st.set_page_config(
    page_title="Property Analytics",
    page_icon="🏠",
    layout="wide"
)

st.title("Property Analytics")
st.caption("Property-level performance and investment insights")

table_name = os.getenv("PROPERTY_PERFORMANCE_TABLE")

try:
    with st.spinner("Loading property performance data..."):
        df = query_table(table_name, limit=1000)

    if df.empty:
        st.warning("No property records found.")
        st.stop()

    st.success("Property data loaded from Databricks Gold layer")

    # Filters
    st.subheader("Property Filters")

    c1, c2, c3 = st.columns(3)

    with c1:
        markets = ["All Markets"] + sorted(
            df["market_name"].dropna().unique().tolist()
        )
        selected_market = st.selectbox("Market", markets)

    with c2:
        types = ["All Types"] + sorted(
            df["property_type"].dropna().unique().tolist()
        )
        selected_type = st.selectbox("Property Type", types)

    with c3:
        bedrooms = ["All"] + sorted(
            df["bedrooms"].dropna().unique().tolist()
        )
        selected_bedrooms = st.selectbox("Bedrooms", bedrooms)

    filtered = df.copy()

    if selected_market != "All Markets":
        filtered = filtered[
            filtered["market_name"] == selected_market
        ]

    if selected_type != "All Types":
        filtered = filtered[
            filtered["property_type"] == selected_type
        ]

    if selected_bedrooms != "All":
        filtered = filtered[
            filtered["bedrooms"] == selected_bedrooms
        ]

    if filtered.empty:
        st.warning("No properties match the selected filters.")
        st.stop()

    # Portfolio KPIs for selected properties
    total_properties = filtered["property_id"].nunique()

    occupied_days = filtered["total_occupied_days"].sum()
    service_days = filtered["total_service_days"].sum()

    occupancy = (
        occupied_days / service_days * 100
        if service_days else 0
    )

    total_revenue = filtered["total_rental_revenue"].sum()
    total_noi = filtered["total_noi"].sum()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Properties", f"{total_properties:,}")
    c2.metric("Weighted Occupancy", f"{occupancy:.2f}%")
    c3.metric("Total Rental Revenue", f"${total_revenue:,.2f}")
    c4.metric("Total NOI", f"${total_noi:,.2f}")

    st.divider()

    # Top performing properties
    st.subheader("Top 10 Properties by NOI")

    top_properties = filtered.nlargest(10, "total_noi")

    st.dataframe(
        top_properties[
            [
                "property_id",
                "market_name",
                "property_type",
                "bedrooms",
                "overall_occupancy_pct",
                "total_rental_revenue",
                "total_noi",
                "avg_monthly_noi"
            ]
        ].style.format({
            "overall_occupancy_pct": "{:.2f}%",
            "total_rental_revenue": "${:,.2f}",
            "total_noi": "${:,.2f}",
            "avg_monthly_noi": "${:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Lowest occupancy properties
    st.subheader("10 Lowest Occupancy Properties")

    lowest_occupancy = filtered.nsmallest(
        10, "overall_occupancy_pct"
    )

    st.dataframe(
        lowest_occupancy[
            [
                "property_id",
                "market_name",
                "property_type",
                "overall_occupancy_pct",
                "total_noi",
                "operating_expense_ratio_pct"
            ]
        ].style.format({
            "overall_occupancy_pct": "{:.2f}%",
            "total_noi": "${:,.2f}",
            "operating_expense_ratio_pct": "{:.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # Property performance comparison
    st.subheader("Property Performance Distribution")

    chart1, chart2 = st.columns(2)

    with chart1:
        st.markdown("**Occupancy by Property Type**")
        occupancy_data = (
            filtered.groupby("property_type")[
                ["total_occupied_days", "total_service_days"]
            ].sum()
        )
        occupancy_data["occupancy_pct"] = (
            occupancy_data["total_occupied_days"]
            / occupancy_data["total_service_days"] * 100
        )

        st.bar_chart(occupancy_data["occupancy_pct"])

    with chart2:
        st.markdown("**Total NOI by Property Type**")
        noi_data = (
            filtered.groupby("property_type")["total_noi"]
            .sum()
            .sort_values(ascending=False)
        )
        st.bar_chart(noi_data)

    with st.expander("View all filtered properties"):
        st.dataframe(
            filtered.sort_values("total_noi", ascending=False),
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error("Unable to load property analytics.")
    st.exception(e)

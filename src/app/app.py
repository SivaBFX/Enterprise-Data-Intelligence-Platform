import os
import streamlit as st
import pandas as pd

from utils.database import query_table
from utils.ui import apply_theme, render_header

st.set_page_config(
    page_title="Property Intelligence Platform",
    page_icon="🏢",
    layout="wide"
)

apply_theme()
render_header("Portfolio")

#st.title("Residential Property Intelligence Platform")
#st.caption("Enterprise Data Intelligence Platform")

st.header("Portfolio Overview")

table_name = os.getenv("PORTFOLIO_KPIS_TABLE")

try:
    with st.spinner("Loading portfolio data..."):
        df = query_table(table_name, limit=12)

    if df.empty:
        st.warning("No portfolio KPI records found.")
        st.stop()

    # Sort latest month first
    df = df.sort_values("month_year", ascending=False).reset_index(drop=True)

    latest = df.iloc[0]

    # Calculate weighted occupancy
    occupancy = (
        latest["total_occupied_days"]
        / latest["total_service_days"] * 100
        if latest["total_service_days"] else 0
    )

    st.success("Connected to Databricks Gold layer")

    st.caption(f"Reporting month: {latest['month_year']}")

    # KPI cards
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Properties",
        f"{int(latest['total_properties']):,}"
    )

    c2.metric(
        "Occupancy",
        f"{occupancy:.2f}%"
    )

    c3.metric(
        "Rental Revenue",
        f"${latest['total_rental_revenue']:,.2f}"
    )

    c4.metric(
        "Net Operating Income",
        f"${latest['total_noi']:,.2f}"
    )

    st.divider()

    # Monthly financial trends
    st.subheader("Monthly Financial Performance")

    trend = df.sort_values("month_year").set_index("month_year")

    st.line_chart(
        trend[["total_rental_revenue", "total_noi"]]
    )

    # Detailed monthly records
    with st.expander("View monthly portfolio data"):
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("Unable to load portfolio data.")
    st.exception(e)

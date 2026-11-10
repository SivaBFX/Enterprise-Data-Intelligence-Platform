
import os
import streamlit as st

from utils.database import query_table

st.set_page_config(
    page_title="Property Intelligence Platform",
    page_icon="🏢",
    layout="wide"
)

st.title("Residential Property Intelligence Platform")
st.caption("Enterprise Data Intelligence Platform")

st.subheader("Portfolio Overview")

table_name = os.getenv("PORTFOLIO_KPIS_TABLE")

if not table_name:
    st.error("Portfolio KPI table resource is not configured.")
else:
    try:
        with st.spinner("Loading portfolio data..."):
            df = query_table(table_name, limit=12)

        st.success("Connected to Databricks SQL Warehouse!")

        st.write("Source:", table_name)
        st.write(f"Records retrieved: {len(df)}")

        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error("Unable to retrieve portfolio data.")
        st.exception(e)

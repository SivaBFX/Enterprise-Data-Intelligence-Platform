import streamlit as st

st.set_page_config(
    page_title="Property Intelligence Platform",
    page_icon="🏢",
    layout="wide"
)

st.title("Residential Property Intelligence Platform")
st.caption("Enterprise Data Intelligence Platform")

st.success("Streamlit application deployed successfully!")

st.subheader("Platform Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Properties", "300")
col2.metric("Markets", "5")
col3.metric("Historical Data", "12 Months")

st.info("Next: Connect Gold-layer tables and build analytics pages.")


import streamlit as st


def apply_theme():
    st.markdown("""
    <style>
    /* Main application */
    .stApp {
        background: #f7f8fa;
        color: #20242c;
        font-family: Inter, Arial, sans-serif;
    }

    .main .block-container {
        max-width: 1440px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Hide default sidebar */
    section[data-testid="stSidebar"] {
        display: none;
    }

    /* Top navigation */
    .brand-title {
        font-size: 23px;
        font-weight: 750;
        color: #172b4d;
        letter-spacing: -0.7px;
    }

    .brand-subtitle {
        font-size: 12px;
        color: #788397;
        margin-top: -5px;
    }

    .section-label {
        color: #52756d;
        font-size: 11px;
        font-weight: 750;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-top: 20px;
        margin-bottom: 8px;
    }

    .page-heading {
        font-size: 30px;
        font-weight: 750;
        color: #172b4d;
        letter-spacing: -1px;
        margin-top: 12px;
        margin-bottom: 3px;
    }

    .page-description {
        color: #697586;
        font-size: 14px;
        margin-bottom: 20px;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e7eaf0;
        border-radius: 13px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(25, 40, 65, 0.035);
    }

    div[data-testid="stMetricLabel"] {
        color: #68758a;
        font-size: 13px;
    }

    div[data-testid="stMetricValue"] {
        color: #172b4d;
        font-weight: 750;
    }

    /* Containers and cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff;
        border-color: #e7eaf0;
        border-radius: 13px;
    }

    /* Buttons */
    .stButton > button,
    div[data-testid="stPageLink"] a {
        border-radius: 9px;
        font-weight: 600;
        border: 1px solid #e1e6ed;
    }

    .stButton > button[kind="primary"] {
        background: #087f67;
        border-color: #087f67;
        color: white;
    }

    /* Inputs */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        border-radius: 8px;
        border-color: #dce2ea;
        background: white;
    }

    /* Dataframes */
    div[data-testid="stDataFrame"] {
        border: 1px solid #e7eaf0;
        border-radius: 10px;
        overflow: hidden;
    }

    /* Charts */
    div[data-testid="stVegaLiteChart"],
    div[data-testid="stArrowVegaLiteChart"] {
        background: white;
        border: 1px solid #e7eaf0;
        border-radius: 12px;
        padding: 12px;
    }

    hr {
        border-color: #e8ebf0;
    }

    /* Remove excessive top padding */
    header[data-testid="stHeader"] {
        background: transparent;
    }
    </style>
    """, unsafe_allow_html=True)


def render_header(active_page="Portfolio"):

    # Brand and primary navigation
    left, right = st.columns([2.2, 3])

    with left:
        st.markdown(
            """
            <div class="brand-title">◈ Property Intelligence</div>
            <div class="brand-subtitle">
                AI Studio · Enterprise Data Intelligence Platform
            </div>
            """,
            unsafe_allow_html=True
        )

    with right:
        nav1, nav2, nav3 = st.columns(3)

        with nav1:
            st.page_link(
                "app.py",
                label="Today",
                icon="🏠"
            )

        with nav2:
            st.markdown(
                "<div style='padding:8px;color:#64748b;"
                "font-size:14px;text-align:center'>Data products</div>",
                unsafe_allow_html=True
            )

        with nav3:
            st.markdown(
                "<div style='padding:8px;color:#64748b;"
                "font-size:14px;text-align:center'>Agents</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # Domain navigation
    st.markdown(
        '<div class="section-label">DATA DOMAIN</div>',
        unsafe_allow_html=True
    )

    pages = [
        ("Portfolio", "app.py", "🏠"),
        ("Markets", "pages/02_Market_Analytics.py", "🌎"),
        ("Properties", "pages/03_Property_Analytics.py", "🏢"),
        ("Maintenance", "pages/04_Maintenance.py", "🔧"),
    ]

    columns = st.columns(len(pages))

    for column, (label, path, icon) in zip(columns, pages):
        with column:
            st.page_link(
                path,
                label=label,
                icon=icon
            )

    st.divider()

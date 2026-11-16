"""Investment & CapEx enterprise capital allocation dashboard.

Provides capital investment totals, project counts, category distributions,
market allocations, and detailed project inspection.
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
    "market_id",
    "investment_count",
    "total_capex_amount",
    "avg_capex_amount",
]

st.set_page_config(
    page_title="Investment & CapEx · Enterprise SaaS",
    page_icon=":material/account_balance:",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_capex_data() -> Dict[str, Any]:
    """Load Gold CapEx summary records and Delta freshness metadata."""
    table_name = resolve_table_name(
        "CAPEX_TABLE", "workspace.gold.gold_capex_summary"
    )
    df = query_table(table_name, limit=50000)

    if not df.empty:
        df = coerce_numeric(df, NUMERIC_COLS)
        df["capex_month"] = df["capex_month"].astype(str)
        df["capex_month_dt"] = pd.to_datetime(df["capex_month"], errors="coerce")

    freshness = get_table_freshness(table_name)
    return {"table_name": table_name, "df": df, "freshness": freshness}


def _apply_capex_filters(
    df: pd.DataFrame,
    search_prop: str,
    selected_market: str,
    selected_category: str,
    selected_month: str = "All Months",
) -> pd.DataFrame:
    """Apply property search, market, category, and month filters to CapEx rows."""
    filtered = df.copy()

    if selected_market != "All Markets":
        filtered = filtered[filtered["market_name"] == selected_market]
    if selected_category != "All Categories":
        filtered = filtered[filtered["category"] == selected_category]
    if selected_month != "All Months":
        filtered = filtered[filtered["capex_month"] == selected_month]

    cleaned_search = (search_prop or "").strip().lower()
    if cleaned_search:
        mask = (
            filtered["property_id"].astype(str).str.lower().str.contains(cleaned_search, regex=False)
            | filtered["category"].astype(str).str.lower().str.contains(cleaned_search, regex=False)
        )
        filtered = filtered[mask]

    return filtered


def _compute_capex_summary(filtered: pd.DataFrame) -> Dict[str, Any]:
    """Compute CapEx KPIs and grouped summaries by market, category, and property."""
    total_investment = float(filtered["total_capex_amount"].sum())
    total_count = int(filtered["investment_count"].sum())
    weighted_avg = (total_investment / total_count) if total_count > 0 else 0.0
    unique_props = int(filtered["property_id"].nunique())
    avg_per_prop = (total_investment / unique_props) if unique_props > 0 else 0.0
    unique_cats = int(filtered["category"].nunique())

    return {
        "total_investment": total_investment,
        "total_count": total_count,
        "weighted_avg": weighted_avg,
        "unique_props": unique_props,
        "avg_per_prop": avg_per_prop,
        "unique_cats": unique_cats,
    }


def _compute_capex_kpis(filtered: pd.DataFrame) -> List[Dict[str, Any]]:
    """Compute executive CapEx allocation KPI cards."""
    total_spend = float(filtered["total_capex_amount"].sum())
    total_projects = int(filtered["investment_count"].sum())
    avg_per_proj = (total_spend / total_projects) if total_projects else 0.0
    properties_invested = int(filtered["property_id"].nunique())
    markets_count = int(filtered["market_name"].nunique())

    return [
        {
            "label": "Total CapEx Invested",
            "value": f"${total_spend:,.2f}",
            "delta": f"{total_projects:,} projects",
            "delta_tone": "neutral",
            "caption": "Cumulative capital expenditure",
        },
        {
            "label": "Investment Projects",
            "value": f"{total_projects:,}",
            "delta": f"{properties_invested:,} properties",
            "delta_tone": "info",
            "caption": "Capital work authorizations",
        },
        {
            "label": "Avg Project Size",
            "value": f"${avg_per_proj:,.2f}",
            "delta": "Capitalized Spend",
            "delta_tone": "neutral",
            "caption": "Mean investment per project",
        },
        {
            "label": "Active Markets",
            "value": f"{markets_count:,}",
            "delta": "Multi-Market",
            "delta_tone": "success",
            "caption": "Markets receiving CapEx",
        },
    ]


def main() -> None:
    """Render the Investment & CapEx enterprise page."""
    apply_theme()
    render_header("Investment & CapEx")

    try:
        with st.spinner("Loading CapEx investment data from Databricks Gold layer..."):
            payload = load_capex_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Investment & CapEx",
                description="Capital expenditure and property enhancement investments.",
                domain_label="Investment & CapEx",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No CapEx Records Found",
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
            f1, f2, f3, f4 = st.columns([1.8, 1.4, 1.4, 0.9])
            with f1:
                search_prop = st.text_input("Search Property ID", placeholder="e.g. PROP-025...")
            with f2:
                mkts = ["All Markets"] + sorted(df["market_name"].dropna().unique().tolist())
                selected_market = st.selectbox("Market Filter", mkts)
            with f3:
                cats = ["All Categories"] + sorted(df["category"].dropna().unique().tolist())
                selected_category = st.selectbox("CapEx Category", cats)
            with f4:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", key="capex_refresh_btn", use_container_width=True):
                    load_capex_data.clear()
                    st.rerun()

        filtered = df.copy()
        if selected_market != "All Markets":
            filtered = filtered[filtered["market_name"] == selected_market]
        if selected_category != "All Categories":
            filtered = filtered[filtered["category"] == selected_category]
        if search_prop.strip():
            filtered = filtered[filtered["property_id"].astype(str).str.contains(search_prop.strip(), case=False, regex=False)]

        render_page_header(
            title="Investment & CapEx",
            description="Capital allocation command center: project distribution, category allocations, and asset value additions.",
            domain_label="Portfolio Intelligence",
            reporting_period=f"{len(filtered):,} Investment Line Items",
            status_text=freshness_badge,
            status_tone="success",
        )

        render_section_header(
            title="Capital Investment Summary",
            subtitle=f"Aggregated CapEx for {selected_market} · {selected_category}.",
            badge=selected_category,
            badge_tone="neutral",
        )
        render_kpi_row(_compute_capex_kpis(filtered))

        with chart_card(
            title="CapEx Investment by Category",
            subtitle="Capital allocation breakdown across major repair and upgrade categories",
        ):
            cat_spend = filtered.groupby("category")["total_capex_amount"].sum().sort_values(ascending=False)
            st.bar_chart(cat_spend, color="#119B78")

        with st.expander(f"View Detailed CapEx Records ({len(filtered):,} records)"):
            render_formatted_table(
                filtered.sort_values("total_capex_amount", ascending=False),
                column_labels={
                    "property_id": "Property ID",
                    "market_name": "Market",
                    "category": "Category",
                    "investment_count": "Projects",
                    "total_capex_amount": "Total Invested ($)",
                    "avg_capex_amount": "Avg Project ($)",
                    "capex_month": "Month",
                },
                formats={
                    "total_capex_amount": "${:,.2f}",
                    "avg_capex_amount": "${:,.2f}",
                },
            )

    except Exception as exc:
        render_page_header(
            title="Investment & CapEx",
            description="Capital expenditure analytics.",
            domain_label="Investment & CapEx",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load investment & CapEx analytics.")
        st.exception(exc)


if __name__ == "__main__":
    main()

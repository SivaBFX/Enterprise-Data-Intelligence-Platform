"""Property Intelligence enterprise portfolio management page.

Provides property directory search, multi-attribute filtering, occupancy and NOI tiers,
and dedicated individual property drill-downs.
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

LOW_OCCUPANCY_THRESHOLD_PCT = 85.0

NUMERIC_COLS = [
    "bedrooms",
    "total_occupied_days",
    "total_service_days",
    "overall_occupancy_pct",
    "total_rental_revenue",
    "total_noi",
    "avg_monthly_noi",
    "operating_expense_ratio_pct",
]

st.set_page_config(
    page_title="Property Intelligence · Enterprise SaaS",
    page_icon=":material/apartment:",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_property_data() -> Dict[str, Any]:
    """Load property performance Gold data and Delta freshness metadata."""
    table_name = resolve_table_name(
        "PROPERTY_PERFORMANCE_TABLE", "workspace.gold.gold_property_performance"
    )
    df = query_table(table_name, limit=2000)
    if not df.empty:
        df = coerce_numeric(df, NUMERIC_COLS)
    freshness = get_table_freshness(table_name)
    return {"table_name": table_name, "df": df, "freshness": freshness}


def _apply_property_filters(
    df: pd.DataFrame,
    search_query: str,
    selected_market: str,
    selected_type: str,
    selected_bedrooms: Any,
) -> pd.DataFrame:
    """Filter properties by search text, market, property type, and bedrooms."""
    filtered = df.copy()

    if selected_market != "All Markets":
        filtered = filtered[filtered["market_name"] == selected_market]

    if selected_type != "All Types":
        filtered = filtered[filtered["property_type"] == selected_type]

    if selected_bedrooms != "All":
        filtered = filtered[filtered["bedrooms"] == selected_bedrooms]

    cleaned_search = (search_query or "").strip().lower()
    if cleaned_search:
        mask = (
            filtered["property_id"].astype(str).str.lower().str.contains(cleaned_search, regex=False)
            | filtered["market_name"].astype(str).str.lower().str.contains(cleaned_search, regex=False)
            | filtered["property_type"].astype(str).str.lower().str.contains(cleaned_search, regex=False)
        )
        filtered = filtered[mask]

    return filtered


def _compute_property_kpis(filtered: pd.DataFrame, total_portfolio_count: int) -> List[Dict[str, Any]]:
    """Compute executive property-slice KPI cards."""
    total_properties = int(filtered["property_id"].nunique())
    occupied_days = float(filtered["total_occupied_days"].sum())
    service_days = float(filtered["total_service_days"].sum())
    occupancy = (occupied_days / service_days * 100.0) if service_days else 0.0

    total_revenue = float(filtered["total_rental_revenue"].sum())
    total_noi = float(filtered["total_noi"].sum())
    noi_margin = (total_noi / total_revenue * 100.0) if total_revenue else 0.0
    avg_monthly_noi = float(filtered["avg_monthly_noi"].mean()) if not filtered.empty else 0.0
    avg_exp_ratio = (
        float(filtered["operating_expense_ratio_pct"].mean()) if not filtered.empty else 0.0
    )

    low_occ_count = int((filtered["overall_occupancy_pct"] < LOW_OCCUPANCY_THRESHOLD_PCT).sum())
    neg_noi_count = int((filtered["total_noi"] <= 0).sum())
    watchlist_count = int(
        (
            (filtered["overall_occupancy_pct"] < LOW_OCCUPANCY_THRESHOLD_PCT)
            | (filtered["total_noi"] <= 0)
        ).sum()
    )
    share_pct = (
        (total_properties / total_portfolio_count * 100.0) if total_portfolio_count else 0.0
    )

    return [
        {
            "label": "Total Properties",
            "value": f"{total_properties:,}",
            "delta": f"{share_pct:.1f}% of portfolio",
            "delta_tone": "neutral",
            "caption": f"{total_portfolio_count:,} total portfolio assets",
        },
        {
            "label": "Weighted Occupancy",
            "value": f"{occupancy:.2f}%",
            "delta": "Healthy" if occupancy >= 90 else "Monitor",
            "delta_tone": "success" if occupancy >= 90 else "warning",
            "caption": f"{int(occupied_days):,} / {int(service_days):,} service days",
        },
        {
            "label": "Total Rental Revenue",
            "value": f"${total_revenue:,.2f}",
            "delta": f"${(total_revenue / total_properties if total_properties else 0):,.0f} / prop",
            "delta_tone": "info",
            "caption": "Cumulative rental revenue",
        },
        {
            "label": "Total NOI",
            "value": f"${total_noi:,.2f}",
            "delta": f"{noi_margin:.1f}% margin",
            "delta_tone": "success" if total_noi > 0 else "danger",
            "caption": "Net operating income",
        },
        {
            "label": "Avg Monthly NOI",
            "value": f"${avg_monthly_noi:,.2f}",
            "delta": f"{avg_exp_ratio:.1f}% avg OpEx ratio",
            "delta_tone": "neutral",
            "caption": "Mean monthly NOI per asset",
        },
        {
            "label": "Attention Watchlist",
            "value": f"{watchlist_count:,}",
            "delta": f"{low_occ_count} low occ · {neg_noi_count} <=$0 NOI",
            "delta_tone": "warning" if watchlist_count > 0 else "success",
            "caption": f"Occupancy < {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% or NOI <= $0",
        },
    ]


def _render_top_and_underperforming(filtered: pd.DataFrame) -> None:
    """Render top-performing and underperforming property leaderboards."""
    render_section_header(
        title="Top-Performing & Underperforming Properties",
        subtitle="Rankings by cumulative NOI and occupancy risk across the filtered selection.",
        badge=f"{len(filtered):,} Evaluated",
        badge_tone="info",
    )

    with chart_card(
        title="Top 10 Properties by NOI",
        subtitle="Highest net operating income contributors in the active filter",
    ):
        top10 = filtered.nlargest(10, "total_noi")[
            ["property_id", "market_name", "property_type", "total_noi", "overall_occupancy_pct"]
        ].set_index("property_id")
        st.bar_chart(top10["total_noi"], color="#119B78")

    watchlist = filtered[
        (filtered["overall_occupancy_pct"] < LOW_OCCUPANCY_THRESHOLD_PCT)
        | (filtered["total_noi"] <= 0)
    ].sort_values("overall_occupancy_pct")

    with chart_card(
        title="Underperforming Property Watchlist",
        subtitle=f"Properties with occupancy below {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% or cumulative NOI <= $0",
        badge=f"{len(watchlist):,} Requiring Attention",
        badge_tone="warning" if not watchlist.empty else "success",
    ):
        if watchlist.empty:
            render_empty_state(
                "Watchlist Clear",
                "All filtered properties exceed 85% occupancy with positive NOI.",
                tone="success",
            )
        else:
            render_formatted_table(
                watchlist.head(15),
                column_labels={
                    "property_id": "Property ID",
                    "market_name": "Market",
                    "property_type": "Type",
                    "bedrooms": "Beds",
                    "overall_occupancy_pct": "Occupancy (%)",
                    "total_rental_revenue": "Revenue ($)",
                    "total_noi": "Total NOI ($)",
                    "operating_expense_ratio_pct": "OpEx Ratio (%)",
                },
                formats={
                    "overall_occupancy_pct": "{:.2f}%",
                    "total_rental_revenue": "${:,.2f}",
                    "total_noi": "${:,.2f}",
                    "operating_expense_ratio_pct": "{:.2f}%",
                },
            )


def _render_property_drilldown_and_insights(filtered: pd.DataFrame) -> None:
    """Render individual property selector and detail inspection card."""
    render_section_header(
        title="Individual Property Detail & Unit Economics",
        subtitle="Select a property below for comprehensive performance breakdown and diagnostics.",
    )

    property_ids = filtered["property_id"].astype(str).tolist()
    selected_id = st.selectbox(
        "Select Property to Inspect",
        property_ids,
        key="property_detail_selector",
    )

    prop_row = filtered[filtered["property_id"].astype(str) == selected_id].iloc[0]

    with st.container(border=True):
        p_head_col, p_badge_col = st.columns([3, 1])
        with p_head_col:
            st.markdown(
                f'<h2 style="font-size:1.35rem;font-weight:750;color:#202B38;margin:0 0 4px 0;">'
                f'Property {prop_row["property_id"]} — {prop_row["market_name"]}</h2>'
                f'<div style="font-size:0.83rem;color:#758294;">'
                f'{prop_row["property_type"]} · {int(prop_row["bedrooms"])} Bedrooms · Region {prop_row.get("region", "N/A")}</div>',
                unsafe_allow_html=True,
            )
        with p_badge_col:
            occ_val = float(prop_row["overall_occupancy_pct"])
            occ_status = "Healthy Occupancy" if occ_val >= 90 else ("Attention Required" if occ_val < 85 else "Standard Tier")
            occ_tone = "success" if occ_val >= 90 else ("danger" if occ_val < 85 else "warning")
            st.markdown(
                f'<div style="text-align:right;">'
                f'<span style="background:{"#E7F5EE" if occ_tone == "success" else "#FEF0F0"};'
                f'color:{"#0B5E42" if occ_tone == "success" else "#9B1C1C"};'
                f'padding:4px 10px;border-radius:999px;font-size:0.75rem;font-weight:700;">'
                f'{occ_status}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.metric("Overall Occupancy", f"{prop_row['overall_occupancy_pct']:.2f}%")
        with k2:
            st.metric("Total Rental Revenue", f"${prop_row['total_rental_revenue']:,.2f}")
        with k3:
            st.metric("Total NOI", f"${prop_row['total_noi']:,.2f}")
        with k4:
            st.metric("Avg Monthly NOI", f"${prop_row['avg_monthly_noi']:,.2f}")
        with k5:
            st.metric("OpEx Ratio", f"{prop_row['operating_expense_ratio_pct']:.2f}%")


def main() -> None:
    """Render the Property Intelligence enterprise page."""
    apply_theme()
    render_header("Property Intelligence")

    try:
        with st.spinner("Loading property performance data from Databricks Gold layer..."):
            payload = load_property_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Property Intelligence",
                description="Property-level occupancy, rental revenue, and NOI insights.",
                domain_label="Property Intelligence",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No Property Records Found",
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
            f1, f2, f3, f4, f5 = st.columns([2.0, 1.4, 1.4, 1.2, 0.9])
            with f1:
                search_query = st.text_input(
                    "Search Property / Market / Type",
                    placeholder="e.g., PROP-001 or Austin...",
                )
            with f2:
                markets = ["All Markets"] + sorted(df["market_name"].dropna().unique().tolist())
                selected_market = st.selectbox("Market", markets)
            with f3:
                types = ["All Types"] + sorted(df["property_type"].dropna().unique().tolist())
                selected_type = st.selectbox("Property Type", types)
            with f4:
                bedrooms = ["All"] + sorted(df["bedrooms"].dropna().unique().tolist())
                selected_bedrooms = st.selectbox(
                    "Bedrooms",
                    bedrooms,
                    format_func=lambda x: (
                        "All"
                        if x == "All"
                        else f"{int(x)} BR" if float(x).is_integer() else str(x)
                    ),
                )
            with f5:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", key="prop_refresh_btn", use_container_width=True):
                    load_property_data.clear()
                    st.rerun()

        filtered = _apply_property_filters(
            df=df,
            search_query=search_query,
            selected_market=selected_market,
            selected_type=selected_type,
            selected_bedrooms=selected_bedrooms,
        )

        render_page_header(
            title="Property Intelligence",
            description="Property portfolio directory, unit economics, occupancy tiers, and asset drill-downs.",
            domain_label="Portfolio Intelligence",
            reporting_period=f"{len(filtered):,} of {len(df):,} Properties",
            status_text=freshness_badge,
            status_tone="success",
        )

        if filtered.empty:
            render_empty_state(
                "No Properties Match Selected Filters",
                "Adjust search query, market, property type, or bedroom filters to view results.",
                tone="warning",
            )
            st.stop()

        render_section_header(
            title="Property Performance Summary",
            subtitle="Aggregated metrics for the currently filtered property cohort.",
            badge=f"{selected_market} · {selected_type}",
            badge_tone="neutral",
        )
        render_kpi_row(_compute_property_kpis(filtered, total_portfolio_count=len(df)))

        _render_top_and_underperforming(filtered)
        _render_property_drilldown_and_insights(filtered)

        with st.expander(f"View Full Property Directory ({len(filtered):,} records)"):
            render_formatted_table(
                filtered.sort_values("total_noi", ascending=False),
                column_labels={
                    "property_id": "Property ID",
                    "market_name": "Market",
                    "property_type": "Type",
                    "bedrooms": "Beds",
                    "overall_occupancy_pct": "Occupancy (%)",
                    "total_rental_revenue": "Rental Revenue ($)",
                    "total_noi": "Total NOI ($)",
                    "avg_monthly_noi": "Avg Monthly NOI ($)",
                    "operating_expense_ratio_pct": "OpEx Ratio (%)",
                },
                formats={
                    "overall_occupancy_pct": "{:.2f}%",
                    "total_rental_revenue": "${:,.2f}",
                    "total_noi": "${:,.2f}",
                    "avg_monthly_noi": "${:,.2f}",
                    "operating_expense_ratio_pct": "{:.2f}%",
                },
            )

    except Exception as exc:
        render_page_header(
            title="Property Intelligence",
            description="Property portfolio management and intelligence.",
            domain_label="Property Intelligence",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load property intelligence.")
        st.exception(exc)


if __name__ == "__main__":
    main()


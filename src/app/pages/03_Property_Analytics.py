"""Property Analytics AI Studio page (Milestone 4)."""

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
    page_title="Property Analytics · AI Studio",
    page_icon="🏢",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_property_data() -> Dict[str, Any]:
    """Load property performance Gold data and Delta freshness metadata."""
    table_name = resolve_table_name(
        "PROPERTY_PERFORMANCE_TABLE", "workspace.gold.gold_property_performance"
    )
    df = query_table(table_name, limit=1000)
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
            "label": "Properties",
            "value": f"{total_properties:,}",
            "delta": f"{share_pct:.1f}% of portfolio",
            "delta_tone": "neutral",
            "caption": f"{total_portfolio_count:,} total portfolio assets",
            "icon": "🏢",
        },
        {
            "label": "Weighted Occupancy",
            "value": f"{occupancy:.2f}%",
            "delta": "Healthy" if occupancy >= 90 else "Monitor",
            "delta_tone": "success" if occupancy >= 90 else "warning",
            "caption": f"{int(occupied_days):,} / {int(service_days):,} service days",
            "icon": "🔑",
        },
        {
            "label": "Total Rental Revenue",
            "value": f"${total_revenue:,.2f}",
            "delta": f"${(total_revenue / total_properties if total_properties else 0):,.0f} / prop",
            "delta_tone": "info",
            "caption": "Cumulative for filtered properties",
            "icon": "💵",
        },
        {
            "label": "Total NOI",
            "value": f"${total_noi:,.2f}",
            "delta": f"{noi_margin:.1f}% margin",
            "delta_tone": "success" if total_noi > 0 else "danger",
            "caption": "Net operating income",
            "icon": "📈",
        },
        {
            "label": "Avg Monthly NOI",
            "value": f"${avg_monthly_noi:,.2f}",
            "delta": f"{avg_exp_ratio:.1f}% avg OpEx ratio",
            "delta_tone": "neutral",
            "caption": "Mean monthly NOI per property",
            "icon": "⚖️",
        },
        {
            "label": "Underperforming Watchlist",
            "value": f"{watchlist_count:,}",
            "delta": f"{low_occ_count} low occ · {neg_noi_count} <=$0 NOI",
            "delta_tone": "warning" if watchlist_count > 0 else "success",
            "caption": f"Occupancy < {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% or NOI <= $0",
            "icon": "🚨",
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
        badge="Top Performers",
        badge_tone="success",
    ):
        top_properties = filtered.nlargest(10, "total_noi")
        render_formatted_table(
            top_properties,
            column_labels={
                "property_id": "Property ID",
                "market_name": "Market",
                "property_type": "Property Type",
                "bedrooms": "Bedrooms",
                "overall_occupancy_pct": "Occupancy %",
                "total_rental_revenue": "Rental Revenue",
                "total_noi": "Total NOI",
                "avg_monthly_noi": "Avg Monthly NOI",
            },
            formats={
                "Bedrooms": "{:.0f}",
                "Occupancy %": "{:.2f}%",
                "Rental Revenue": "${:,.2f}",
                "Total NOI": "${:,.2f}",
                "Avg Monthly NOI": "${:,.2f}",
            },
        )

    with chart_card(
        title="Underperforming Properties Watchlist",
        subtitle="Properties requiring leasing, pricing, or expense intervention",
        badge="Action Queue",
        badge_tone="warning",
    ):
        tab_occ, tab_noi = st.tabs(
            ["10 Lowest Occupancy Properties", "10 Lowest NOI Properties"]
        )
        with tab_occ:
            lowest_occupancy = filtered.nsmallest(10, "overall_occupancy_pct")
            render_formatted_table(
                lowest_occupancy,
                column_labels={
                    "property_id": "Property ID",
                    "market_name": "Market",
                    "property_type": "Property Type",
                    "overall_occupancy_pct": "Occupancy %",
                    "total_noi": "Total NOI",
                    "operating_expense_ratio_pct": "Expense Ratio %",
                },
                formats={
                    "Occupancy %": "{:.2f}%",
                    "Total NOI": "${:,.2f}",
                    "Expense Ratio %": "{:.2f}%",
                },
            )

        with tab_noi:
            lowest_noi = filtered.nsmallest(10, "total_noi")
            render_formatted_table(
                lowest_noi,
                column_labels={
                    "property_id": "Property ID",
                    "market_name": "Market",
                    "property_type": "Property Type",
                    "bedrooms": "Bedrooms",
                    "overall_occupancy_pct": "Occupancy %",
                    "total_rental_revenue": "Rental Revenue",
                    "total_noi": "Total NOI",
                    "operating_expense_ratio_pct": "Expense Ratio %",
                },
                formats={
                    "Bedrooms": "{:.0f}",
                    "Occupancy %": "{:.2f}%",
                    "Rental Revenue": "${:,.2f}",
                    "Total NOI": "${:,.2f}",
                    "Expense Ratio %": "{:.2f}%",
                },
            )


def _render_occupancy_and_noi_analysis(filtered: pd.DataFrame) -> None:
    """Render occupancy tier distribution and NOI breakdown by type and bedrooms."""
    render_section_header(
        title="Occupancy & NOI Analysis",
        subtitle="Structural performance distribution across property types, bedroom tiers, and occupancy bands.",
        badge="Distribution",
        badge_tone="neutral",
    )

    col_occ, col_noi = st.columns(2)
    with col_occ:
        with chart_card(
            title="Weighted Occupancy by Property Type",
            subtitle="Occupied days divided by total service days (%)",
            badge="Occupancy %",
            badge_tone="success",
        ):
            occupancy_data = filtered.groupby("property_type")[
                ["total_occupied_days", "total_service_days"]
            ].sum()
            occupancy_data["Occupancy %"] = (
                occupancy_data["total_occupied_days"]
                / occupancy_data["total_service_days"].replace(0, pd.NA)
                * 100.0
            ).fillna(0.0)
            st.bar_chart(occupancy_data[["Occupancy %"]])

    with col_noi:
        with chart_card(
            title="Total NOI by Property Type",
            subtitle="Cumulative net operating income across asset classes ($)",
            badge="NOI ($)",
            badge_tone="info",
        ):
            noi_data = (
                filtered.groupby("property_type", as_index=True)[["total_noi"]]
                .sum()
                .sort_values("total_noi", ascending=False)
                .rename(columns={"total_noi": "Total NOI ($)"})
            )
            st.bar_chart(noi_data)

    tier_col, bed_col = st.columns(2)
    with tier_col:
        with chart_card(
            title="Occupancy Band Distribution",
            subtitle="Property count across operational occupancy tiers",
            badge="Occupancy Tiers",
            badge_tone="neutral",
        ):
            bands = pd.cut(
                filtered["overall_occupancy_pct"],
                bins=[-float("inf"), 85.0, 90.0, 95.0, float("inf")],
                labels=["< 85% (Risk)", "85% - 89.9%", "90% - 94.9%", ">= 95% (High)"],
                right=False,
            )
            tier_counts = (
                bands.value_counts()
                .reindex(["< 85% (Risk)", "85% - 89.9%", "90% - 94.9%", ">= 95% (High)"], fill_value=0)
                .rename_axis("Occupancy Band")
                .to_frame(name="Properties")
            )
            st.bar_chart(tier_counts)

    with bed_col:
        with chart_card(
            title="NOI & Expense Ratio by Bedroom Count",
            subtitle="Unit economics summary grouped by bedroom configuration",
            badge="Unit Mix",
            badge_tone="neutral",
        ):
            bed_summary = (
                filtered.groupby("bedrooms", as_index=False)
                .agg(
                    Properties=("property_id", "nunique"),
                    Avg_Occupancy=("overall_occupancy_pct", "mean"),
                    Avg_Monthly_NOI=("avg_monthly_noi", "mean"),
                    Total_NOI=("total_noi", "sum"),
                    Avg_Exp_Ratio=("operating_expense_ratio_pct", "mean"),
                )
                .sort_values("bedrooms")
            )
            render_formatted_table(
                bed_summary,
                column_labels={
                    "bedrooms": "Bedrooms",
                    "Properties": "Properties",
                    "Avg_Occupancy": "Avg Occupancy %",
                    "Avg_Monthly_NOI": "Avg Monthly NOI",
                    "Total_NOI": "Total NOI",
                    "Avg_Exp_Ratio": "Avg Expense Ratio %",
                },
                formats={
                    "Bedrooms": "{:.0f}",
                    "Properties": "{:,.0f}",
                    "Avg Occupancy %": "{:.2f}%",
                    "Avg Monthly NOI": "${:,.2f}",
                    "Total NOI": "${:,.2f}",
                    "Avg Expense Ratio %": "{:.2f}%",
                },
            )


def _render_property_drilldown_and_insights(filtered: pd.DataFrame) -> None:
    """Render individual property-level inspector and calculated property insights."""
    render_section_header(
        title="Property-Level Details & Business Insights",
        subtitle="Inspect an individual property against filtered portfolio averages and review calculated takeaways.",
    )

    left_col, right_col = st.columns([1.15, 1.0])

    with left_col:
        with chart_card(
            title="Property-Level Detail Inspector",
            subtitle="Select any property in the current filter to inspect its unit economics",
            badge="Asset Lookup",
            badge_tone="info",
        ):
            prop_ids = sorted(filtered["property_id"].astype(str).unique().tolist())
            selected_prop_id = st.selectbox("Select Property ID", prop_ids)
            prop_row = filtered[filtered["property_id"].astype(str) == selected_prop_id].iloc[0]

            avg_occ = float(filtered["overall_occupancy_pct"].mean())
            avg_exp = float(filtered["operating_expense_ratio_pct"].mean())
            occ_diff = float(prop_row["overall_occupancy_pct"]) - avg_occ
            exp_diff = float(prop_row["operating_expense_ratio_pct"]) - avg_exp

            render_kpi_row(
                [
                    {
                        "label": "Property Occupancy",
                        "value": f"{float(prop_row['overall_occupancy_pct']):.2f}%",
                        "delta": f"{occ_diff:+.2f} pp vs. slice avg",
                        "delta_tone": "success" if occ_diff >= 0 else "warning",
                        "caption": f"{prop_row['market_name']} · {prop_row['property_type']}",
                    },
                    {
                        "label": "Total NOI",
                        "value": f"${float(prop_row['total_noi']):,.2f}",
                        "delta": f"${float(prop_row['avg_monthly_noi']):,.2f} / mo",
                        "delta_tone": "success" if float(prop_row["total_noi"]) > 0 else "danger",
                        "caption": f"{int(prop_row['bedrooms'])} BR · Rev ${float(prop_row['total_rental_revenue']):,.0f}",
                    },
                    {
                        "label": "Expense Ratio",
                        "value": f"{float(prop_row['operating_expense_ratio_pct']):.2f}%",
                        "delta": f"{exp_diff:+.2f} pp vs. slice avg",
                        "delta_tone": "success" if exp_diff <= 0 else "warning",
                        "caption": f"{int(prop_row['total_occupied_days']):,} / {int(prop_row['total_service_days']):,} days",
                    },
                ]
            )

    with right_col:
        with chart_card(
            title="Calculated Property Insights",
            subtitle="Metrics computed strictly from the active property filter",
            badge="Calculated Metrics",
            badge_tone="success",
        ):
            top_prop = filtered.loc[filtered["total_noi"].idxmax()]
            type_noi = filtered.groupby("property_type")["total_noi"].sum()
            best_type = type_noi.idxmax()
            best_type_share = (
                float(type_noi.max()) / float(filtered["total_noi"].sum()) * 100.0
                if float(filtered["total_noi"].sum())
                else 0.0
            )
            low_occ_count = int((filtered["overall_occupancy_pct"] < LOW_OCCUPANCY_THRESHOLD_PCT).sum())
            neg_noi_count = int((filtered["total_noi"] <= 0).sum())

            render_insight_card(
                title="Top Asset & Property Class Driver",
                body=(
                    f"Property {top_prop['property_id']} ({top_prop['market_name']}, "
                    f"{top_prop['property_type']}) generated the highest NOI at "
                    f"${top_prop['total_noi']:,.2f}. {best_type} assets account for "
                    f"{best_type_share:.1f}% of filtered NOI."
                ),
                tone="success",
                tag="Calculated",
            )
            render_insight_card(
                title="Asset Watchlist Exposure",
                body=(
                    f"{low_occ_count} of {len(filtered)} filtered properties are below "
                    f"{LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% occupancy and {neg_noi_count} have "
                    f"non-positive NOI. Focus renewal incentives and expense audits on flagged units."
                ),
                tone="warning" if (low_occ_count + neg_noi_count) > 0 else "info",
                tag="Calculated + Action",
            )


def main() -> None:
    """Render the Property Analytics AI Studio page."""
    apply_theme()
    render_header("Properties")

    try:
        with st.spinner("Loading property performance data from Databricks Gold layer..."):
            payload = load_property_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Property Analytics",
                description="Property-level occupancy, rental revenue, and NOI insights.",
                domain_label="Properties",
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

        # Search and filters inside a consistent AI Studio card
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
                if st.button("Refresh Data", use_container_width=True):
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
            title="Property Analytics",
            description=(
                "Property-level search, occupancy tiers, NOI rankings, and individual unit economics."
            ),
            domain_label="Properties · AI Studio",
            reporting_period=f"{len(filtered):,} of {len(df):,} Properties",
            status_text=freshness_badge,
            status_tone="success",
        )

        if filtered.empty:
            render_empty_state(
                "No Properties Match Selected Filters",
                "Adjust the search query, market, property type, or bedroom filters to view results.",
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
        _render_occupancy_and_noi_analysis(filtered)
        _render_property_drilldown_and_insights(filtered)

        with st.expander("View all filtered properties"):
            st.dataframe(
                filtered.sort_values("total_noi", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    except Exception as exc:
        render_page_header(
            title="Property Analytics",
            description="Property-level occupancy, rental revenue, and NOI insights.",
            domain_label="Properties",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load property analytics.")
        st.exception(exc)


if __name__ == "__main__":
    main()

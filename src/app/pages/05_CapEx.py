"""CapEx Analytics AI Studio page (Milestone 6)."""

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
    page_title="CapEx Analytics · AI Studio",
    page_icon="🏗️",
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
    selected_month: str,
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

    by_market = (
        filtered.groupby(["market_name", "region"], as_index=False)
        .agg(
            Properties=("property_id", "nunique"),
            Investments=("investment_count", "sum"),
            Total_CapEx=("total_capex_amount", "sum"),
        )
        .sort_values("Total_CapEx", ascending=False)
        .reset_index(drop=True)
    )
    by_market["Avg_Investment"] = (
        by_market["Total_CapEx"] / by_market["Investments"].replace(0, pd.NA)
    ).fillna(0.0)
    by_market["Share_%"] = (
        (by_market["Total_CapEx"] / total_investment * 100.0)
        if total_investment > 0
        else 0.0
    )

    by_category = (
        filtered.groupby("category", as_index=False)
        .agg(
            Properties=("property_id", "nunique"),
            Investments=("investment_count", "sum"),
            Total_CapEx=("total_capex_amount", "sum"),
        )
        .sort_values("Total_CapEx", ascending=False)
        .reset_index(drop=True)
    )
    by_category["Avg_Investment"] = (
        by_category["Total_CapEx"] / by_category["Investments"].replace(0, pd.NA)
    ).fillna(0.0)
    by_category["Share_%"] = (
        (by_category["Total_CapEx"] / total_investment * 100.0)
        if total_investment > 0
        else 0.0
    )

    by_property = (
        filtered.groupby(["property_id", "market_name", "region"], as_index=False)
        .agg(
            Categories=("category", "nunique"),
            Investments=("investment_count", "sum"),
            Total_CapEx=("total_capex_amount", "sum"),
        )
        .sort_values("Total_CapEx", ascending=False)
        .reset_index(drop=True)
    )
    by_property["Avg_Investment"] = (
        by_property["Total_CapEx"] / by_property["Investments"].replace(0, pd.NA)
    ).fillna(0.0)

    top_mkt_name = str(by_market.iloc[0]["market_name"]) if not by_market.empty else "—"
    top_mkt_spend = float(by_market.iloc[0]["Total_CapEx"]) if not by_market.empty else 0.0
    top_mkt_share = float(by_market.iloc[0]["Share_%"]) if not by_market.empty else 0.0

    top_cat_name = str(by_category.iloc[0]["category"]) if not by_category.empty else "—"
    top_cat_spend = float(by_category.iloc[0]["Total_CapEx"]) if not by_category.empty else 0.0
    top_cat_share = float(by_category.iloc[0]["Share_%"]) if not by_category.empty else 0.0

    cards: List[Dict[str, Any]] = [
        {
            "label": "Total Investment",
            "value": f"${total_investment:,.2f}",
            "delta": f"{unique_props:,} properties",
            "delta_tone": "info",
            "caption": f"{len(filtered):,} summary records",
            "icon": "🏗️",
        },
        {
            "label": "Number of Investments",
            "value": f"{total_count:,}",
            "delta": f"{unique_cats:,} categories",
            "delta_tone": "neutral",
            "caption": "Capital projects & replacements",
            "icon": "🧾",
        },
        {
            "label": "Average Investment Amount",
            "value": f"${weighted_avg:,.2f}",
            "delta": "Weighted / Project",
            "delta_tone": "neutral",
            "caption": "Total CapEx / Investment Count",
            "icon": "⚖️",
        },
        {
            "label": "Avg CapEx / Property",
            "value": f"${avg_per_prop:,.2f}",
            "delta": "Property Intensity",
            "delta_tone": "neutral",
            "caption": "Mean spend across active CapEx assets",
            "icon": "🏢",
        },
        {
            "label": "Top CapEx Market",
            "value": top_mkt_name,
            "delta": f"{top_mkt_share:.1f}% share",
            "delta_tone": "success",
            "caption": f"${top_mkt_spend:,.0f} invested",
            "icon": "🌎",
        },
        {
            "label": "Top CapEx Category",
            "value": top_cat_name,
            "delta": f"{top_cat_share:.1f}% share",
            "delta_tone": "info",
            "caption": f"${top_cat_spend:,.0f} invested",
            "icon": "🛠️",
        },
    ]

    return {
        "cards": cards,
        "total_investment": total_investment,
        "total_count": total_count,
        "weighted_avg": weighted_avg,
        "unique_props": unique_props,
        "avg_per_prop": avg_per_prop,
        "by_market": by_market,
        "by_category": by_category,
        "by_property": by_property,
    }


def _render_market_and_category(summary: Dict[str, Any]) -> None:
    """Render investment by market and investment by category charts and tables."""
    render_section_header(
        title="Capital Allocation by Market & Category",
        subtitle="Regional capital deployment and project category concentration.",
        badge=f"${summary['total_investment']:,.0f} Total",
        badge_tone="info",
    )

    by_market = summary["by_market"]
    by_category = summary["by_category"]

    col_m, col_c = st.columns(2)
    with col_m:
        with chart_card(
            title="Investment by Market",
            subtitle="Total CapEx expenditure across markets ($)",
            badge=f"{len(by_market)} Markets",
            badge_tone="neutral",
        ):
            st.bar_chart(
                by_market.set_index("market_name")[["Total_CapEx"]].rename(
                    columns={"Total_CapEx": "Total CapEx ($)"}
                )
            )
            render_formatted_table(
                by_market,
                column_labels={
                    "market_name": "Market",
                    "region": "Region",
                    "Properties": "Properties",
                    "Investments": "Investments",
                    "Total_CapEx": "Total CapEx",
                    "Avg_Investment": "Avg / Investment",
                    "Share_%": "Share %",
                },
                formats={
                    "Properties": "{:,.0f}",
                    "Investments": "{:,.0f}",
                    "Total CapEx": "${:,.2f}",
                    "Avg / Investment": "${:,.2f}",
                    "Share %": "{:.1f}%",
                },
            )

    with col_c:
        with chart_card(
            title="Investment by Category",
            subtitle="Capital spend grouped by asset improvement category ($)",
            badge=f"{len(by_category)} Categories",
            badge_tone="neutral",
        ):
            st.bar_chart(
                by_category.set_index("category")[["Total_CapEx"]].rename(
                    columns={"Total_CapEx": "Total CapEx ($)"}
                )
            )
            render_formatted_table(
                by_category,
                column_labels={
                    "category": "Category",
                    "Properties": "Properties",
                    "Investments": "Investments",
                    "Total_CapEx": "Total CapEx",
                    "Avg_Investment": "Avg / Investment",
                    "Share_%": "Share %",
                },
                formats={
                    "Properties": "{:,.0f}",
                    "Investments": "{:,.0f}",
                    "Total CapEx": "${:,.2f}",
                    "Avg / Investment": "${:,.2f}",
                    "Share %": "{:.1f}%",
                },
            )


def _render_distribution_and_trend(
    filtered: pd.DataFrame,
    summary: Dict[str, Any],
) -> pd.DataFrame:
    """Render monthly CapEx cadence and property-level investment distribution."""
    render_section_header(
        title="Investment Distribution & Monthly Cadence",
        subtitle="Property-level spend dispersion and monthly capital deployment pace.",
        badge="Distribution",
        badge_tone="neutral",
    )

    monthly = (
        filtered.groupby("capex_month", as_index=False)
        .agg(
            Total_CapEx=("total_capex_amount", "sum"),
            Investments=("investment_count", "sum"),
            Sort_Dt=("capex_month_dt", "min"),
        )
    )
    if monthly["Sort_Dt"].notna().all():
        monthly = monthly.sort_values("Sort_Dt")
    else:
        monthly = monthly.sort_values("capex_month")

    by_property = summary["by_property"]

    left_col, right_col = st.columns(2)
    with left_col:
        with chart_card(
            title="Monthly CapEx Spend Trend",
            subtitle="Capital expenditure progression across CapEx months ($)",
            badge=f"{len(monthly)} Months",
            badge_tone="info",
        ):
            st.line_chart(
                monthly.set_index("capex_month")[["Total_CapEx"]].rename(
                    columns={"Total_CapEx": "Total CapEx ($)"}
                )
            )

    with right_col:
        with chart_card(
            title="Property Investment Distribution (Quartiles)",
            subtitle="Property count grouped by cumulative CapEx quartile tier",
            badge=f"{len(by_property):,} Properties",
            badge_tone="neutral",
        ):
            if by_property["Total_CapEx"].nunique() >= 4:
                bins = pd.qcut(by_property["Total_CapEx"], q=4, duplicates="drop")
                dist_df = (
                    bins.value_counts()
                    .sort_index()
                    .rename_axis("CapEx Spend Tier")
                    .to_frame(name="Properties")
                )
                dist_df.index = dist_df.index.map(
                    lambda interval: f"${interval.left:,.0f} - ${interval.right:,.0f}"
                )
                st.bar_chart(dist_df)
            else:
                st.bar_chart(
                    by_property.head(15)
                    .set_index("property_id")[["Total_CapEx"]]
                    .rename(columns={"Total_CapEx": "Total CapEx ($)"})
                )

            median_val = float(by_property["Total_CapEx"].median())
            p90_val = float(by_property["Total_CapEx"].quantile(0.9))
            max_val = float(by_property["Total_CapEx"].max())
            st.caption(
                f"Median / Property: ${median_val:,.0f} · "
                f"90th Percentile: ${p90_val:,.0f} · "
                f"Max: ${max_val:,.0f}"
            )

    return monthly


def _render_property_details_and_insights(
    filtered: pd.DataFrame,
    monthly: pd.DataFrame,
    summary: Dict[str, Any],
) -> None:
    """Render top CapEx properties, calculated insights, and detailed records expander."""
    by_property = summary["by_property"]
    by_market = summary["by_market"]
    by_category = summary["by_category"]

    render_section_header(
        title="Property-Level Investments & Business Insights",
        subtitle="Highest capital-intensity properties and computed capital allocation insights.",
    )

    with chart_card(
        title="Top 15 Properties by Total CapEx Investment",
        subtitle="Properties with the largest cumulative capital expenditure in the active filter",
        badge="Top Assets",
        badge_tone="info",
    ):
        top_15 = by_property.head(15)
        render_formatted_table(
            top_15,
            column_labels={
                "property_id": "Property ID",
                "market_name": "Market",
                "region": "Region",
                "Categories": "Categories",
                "Investments": "Investments",
                "Total_CapEx": "Total CapEx",
                "Avg_Investment": "Avg / Investment",
            },
            formats={
                "Categories": "{:,.0f}",
                "Investments": "{:,.0f}",
                "Total CapEx": "${:,.2f}",
                "Avg / Investment": "${:,.2f}",
            },
        )

    # Calculated insights
    total_inv = summary["total_investment"] or 1.0
    top_mkt = by_market.iloc[0]
    top_cat = by_category.iloc[0]
    p90_cutoff = float(by_property["Total_CapEx"].quantile(0.9))
    top_decile_props = by_property[by_property["Total_CapEx"] >= p90_cutoff]
    top_decile_share = float(top_decile_props["Total_CapEx"].sum()) / total_inv * 100.0
    peak_month_row = monthly.loc[monthly["Total_CapEx"].idxmax()]

    c1, c2 = st.columns(2)
    with c1:
        render_insight_card(
            title="Market & Category Concentration",
            body=(
                f"{top_mkt['market_name']} drew the largest regional CapEx share at "
                f"${top_mkt['Total_CapEx']:,.0f} ({top_mkt['Share_%']:.1f}%), while "
                f"{top_cat['category']} was the #1 investment category at "
                f"${top_cat['Total_CapEx']:,.0f} ({top_cat['Share_%']:.1f}% across "
                f"{int(top_cat['Investments']):,} investments)."
            ),
            tone="info",
            tag="Calculated",
        )
    with c2:
        render_insight_card(
            title="Capital Skew & Peak Deployment",
            body=(
                f"The top {len(top_decile_props)} properties (>= ${p90_cutoff:,.0f}) account for "
                f"{top_decile_share:.1f}% of filtered CapEx spend. Peak monthly deployment occurred "
                f"in {peak_month_row['capex_month']} (${peak_month_row['Total_CapEx']:,.0f}). "
                f"Cross-check high-CapEx properties against Maintenance costs to confirm post-upgrade savings."
            ),
            tone="success" if top_decile_share < 40 else "warning",
            tag="Calculated + Action",
        )

    with st.expander("View Property-Level CapEx Summary Records"):
        render_formatted_table(
            filtered.sort_values("total_capex_amount", ascending=False),
            column_labels={
                "capex_month": "Month",
                "property_id": "Property ID",
                "market_name": "Market",
                "region": "Region",
                "category": "Category",
                "investment_count": "Investments",
                "total_capex_amount": "Total CapEx",
                "avg_capex_amount": "Avg CapEx",
            },
            formats={
                "Investments": "{:,.0f}",
                "Total CapEx": "${:,.2f}",
                "Avg CapEx": "${:,.2f}",
            },
        )


def main() -> None:
    """Render the CapEx Analytics AI Studio page."""
    apply_theme()
    render_header("CapEx")

    try:
        with st.spinner("Loading CapEx analytics from Databricks Gold layer..."):
            payload = load_capex_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="CapEx Analytics",
                description="Capital expenditure analytics across markets, categories, and properties.",
                domain_label="CapEx",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No CapEx Data Found",
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

        # Ordered months newest-first when parseable
        month_order = (
            df[["capex_month", "capex_month_dt"]]
            .drop_duplicates()
            .sort_values(["capex_month_dt", "capex_month"], ascending=[False, False])
        )
        months = ["All Months"] + month_order["capex_month"].tolist()
        markets = ["All Markets"] + sorted(df["market_name"].dropna().unique().tolist())
        categories = ["All Categories"] + sorted(df["category"].dropna().unique().tolist())

        with st.container(border=True):
            f1, f2, f3, f4, f5 = st.columns([1.8, 1.3, 1.3, 1.2, 0.9])
            with f1:
                search_prop = st.text_input(
                    "Search Property ID / Category",
                    placeholder="e.g., PROP-001 or Roof...",
                )
            with f2:
                selected_market = st.selectbox("Market", markets)
            with f3:
                selected_category = st.selectbox("Category", categories)
            with f4:
                selected_month = st.selectbox("CapEx Month", months)
            with f5:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", use_container_width=True):
                    load_capex_data.clear()
                    st.rerun()

        filtered = _apply_capex_filters(
            df=df,
            search_prop=search_prop,
            selected_market=selected_market,
            selected_category=selected_category,
            selected_month=selected_month,
        )

        render_page_header(
            title="CapEx Analytics",
            description=(
                "Capital expenditure allocation across regional markets, improvement categories, "
                "monthly cadence, and property-level investment profiles."
            ),
            domain_label="CapEx · AI Studio",
            reporting_period=f"{selected_month} · {selected_market} · {selected_category}",
            status_text=freshness_badge,
            status_tone="success",
        )

        if filtered.empty:
            render_empty_state(
                "No CapEx Records Match Selected Filters",
                "Adjust the property search, market, category, or month filters to view results.",
                tone="warning",
            )
            st.stop()

        summary = _compute_capex_summary(filtered)

        render_section_header(
            title="Executive CapEx KPIs",
            subtitle="Total investment volume, project counts, average project size, and top drivers.",
            badge=f"{summary['total_count']:,} Investments",
            badge_tone="neutral",
        )
        render_kpi_row(summary["cards"])

        _render_market_and_category(summary)
        monthly = _render_distribution_and_trend(filtered=filtered, summary=summary)
        _render_property_details_and_insights(
            filtered=filtered,
            monthly=monthly,
            summary=summary,
        )

    except Exception as exc:
        render_page_header(
            title="CapEx Analytics",
            description="Capital expenditure analytics across markets, categories, and properties.",
            domain_label="CapEx",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load CapEx analytics.")
        st.exception(exc)


if __name__ == "__main__":
    main()


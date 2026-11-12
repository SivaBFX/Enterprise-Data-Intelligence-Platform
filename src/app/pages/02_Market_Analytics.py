"""Market Analytics AI Studio page (Milestone 3)."""

from typing import Any, Dict, Optional

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
    pct_change,
    render_empty_state,
    render_formatted_table,
    render_header,
    render_insight_card,
    render_kpi_row,
    render_page_header,
    render_section_header,
)

NUMERIC_COLS = [
    "property_count",
    "total_occupied_days",
    "total_service_days",
    "total_rental_revenue",
    "total_noi",
    "total_opex",
    "net_operating_revenue",
]

st.set_page_config(
    page_title="Market Analytics · AI Studio",
    page_icon="🌎",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def load_market_data() -> Dict[str, Any]:
    """Load and normalize monthly market Gold data with Delta freshness."""
    table_name = resolve_table_name(
        "MARKET_MONTHLY_TABLE", "workspace.gold.gold_market_monthly"
    )
    df = query_table(table_name, limit=1000)

    if not df.empty:
        df = coerce_numeric(df, NUMERIC_COLS)
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        df = df.dropna(subset=["month"]).copy()
        df["occupancy_pct"] = (
            df["total_occupied_days"]
            / df["total_service_days"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)
        df["expense_ratio_pct"] = (
            df["total_opex"]
            / df["net_operating_revenue"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)

    freshness = get_table_freshness(table_name)
    return {"table_name": table_name, "df": df, "freshness": freshness}


def _aggregate_market_slice(slice_df: pd.DataFrame) -> Dict[str, float]:
    """Aggregate core market KPIs for a month/market slice."""
    properties = float(slice_df["property_count"].sum())
    occupied_days = float(slice_df["total_occupied_days"].sum())
    service_days = float(slice_df["total_service_days"].sum())
    occupancy = (occupied_days / service_days * 100.0) if service_days else 0.0

    revenue = float(slice_df["total_rental_revenue"].sum())
    noi = float(slice_df["total_noi"].sum())
    opex = float(slice_df["total_opex"].sum())
    net_operating_revenue = float(slice_df["net_operating_revenue"].sum())

    expense_ratio = (
        opex / net_operating_revenue * 100.0 if net_operating_revenue else 0.0
    )
    noi_margin = (noi / revenue * 100.0) if revenue else 0.0

    return {
        "properties": properties,
        "occupied_days": occupied_days,
        "service_days": service_days,
        "occupancy": occupancy,
        "revenue": revenue,
        "noi": noi,
        "opex": opex,
        "net_operating_revenue": net_operating_revenue,
        "expense_ratio": expense_ratio,
        "noi_margin": noi_margin,
    }


def _build_kpi_cards(
    current: Dict[str, float],
    previous: Optional[Dict[str, float]],
    period_label: str,
    scope_label: str,
) -> list:
    """Build the 6 executive market KPI cards with MoM deltas."""
    occ_delta = (
        current["occupancy"] - previous["occupancy"] if previous is not None else None
    )
    rev_delta = (
        pct_change(current["revenue"], previous["revenue"])
        if previous is not None
        else None
    )
    noi_delta = (
        pct_change(current["noi"], previous["noi"]) if previous is not None else None
    )
    opex_delta = (
        pct_change(current["opex"], previous["opex"]) if previous is not None else None
    )
    exp_ratio_delta = (
        current["expense_ratio"] - previous["expense_ratio"]
        if previous is not None
        else None
    )

    return [
        {
            "label": "Properties",
            "value": f"{int(current['properties']):,}",
            "delta": scope_label,
            "delta_tone": "neutral",
            "caption": f"Period: {period_label}",
            "icon": "🏢",
        },
        {
            "label": "Weighted Occupancy",
            "value": f"{current['occupancy']:.2f}%",
            "delta": f"{occ_delta:+.2f} pp MoM" if occ_delta is not None else "Selected Month",
            "delta_tone": "success" if (occ_delta is None or occ_delta >= 0) else "warning",
            "caption": f"{int(current['occupied_days']):,} / {int(current['service_days']):,} days",
            "icon": "🔑",
        },
        {
            "label": "Rental Revenue",
            "value": f"${current['revenue']:,.2f}",
            "delta": f"{rev_delta:+.1f}% MoM" if rev_delta is not None else "Selected Month",
            "delta_tone": "success" if (rev_delta is None or rev_delta >= 0) else "warning",
            "caption": f"Scope: {scope_label}",
            "icon": "💵",
        },
        {
            "label": "Net Operating Income",
            "value": f"${current['noi']:,.2f}",
            "delta": f"{noi_delta:+.1f}% MoM" if noi_delta is not None else "Selected Month",
            "delta_tone": "success" if (noi_delta is None or noi_delta >= 0) else "danger",
            "caption": f"NOI margin: {current['noi_margin']:.1f}%",
            "icon": "📈",
        },
        {
            "label": "Operating Expenses",
            "value": f"${current['opex']:,.2f}",
            "delta": f"{opex_delta:+.1f}% MoM" if opex_delta is not None else "Selected Month",
            "delta_tone": "success" if (opex_delta is None or opex_delta <= 0) else "warning",
            "caption": "Lower MoM spend is favorable",
            "icon": "🧾",
        },
        {
            "label": "Operating Expense Ratio",
            "value": f"{current['expense_ratio']:.2f}%",
            "delta": (
                f"{exp_ratio_delta:+.2f} pp MoM"
                if exp_ratio_delta is not None
                else "Selected Month"
            ),
            "delta_tone": (
                "success" if (exp_ratio_delta is None or exp_ratio_delta <= 0) else "warning"
            ),
            "caption": "OpEx / Net Operating Revenue",
            "icon": "⚖️",
        },
    ]


def _render_ranking_and_comparison(monthly: pd.DataFrame, period_label: str) -> pd.DataFrame:
    """Render market performance ranking table and NOI comparison chart."""
    render_section_header(
        title="Market Comparison & Performance Ranking",
        subtitle=f"Cross-market benchmark for {period_label}, ranked by Net Operating Income.",
        badge=f"{len(monthly)} Markets",
        badge_tone="info",
    )

    ranked = monthly.sort_values("total_noi", ascending=False).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    ranked["noi_margin_pct"] = (
        ranked["total_noi"]
        / ranked["total_rental_revenue"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    ranked["noi_per_property"] = (
        ranked["total_noi"] / ranked["property_count"].replace(0, pd.NA)
    ).fillna(0.0)

    left_col, right_col = st.columns([1.55, 1.0])
    with left_col:
        with chart_card(
            title="Market Performance Ranking",
            subtitle="Ranked by monthly NOI with occupancy, expense ratio, and unit economics",
            badge="Leaderboard",
            badge_tone="success",
        ):
            render_formatted_table(
                ranked,
                column_labels={
                    "rank": "Rank",
                    "market_name": "Market",
                    "region": "Region",
                    "property_count": "Properties",
                    "occupancy_pct": "Occupancy %",
                    "total_rental_revenue": "Rental Revenue",
                    "total_opex": "Operating Expenses",
                    "total_noi": "NOI",
                    "expense_ratio_pct": "Expense Ratio %",
                    "noi_per_property": "NOI / Property",
                },
                formats={
                    "Rank": "{:d}",
                    "Properties": "{:,.0f}",
                    "Occupancy %": "{:.2f}%",
                    "Rental Revenue": "${:,.2f}",
                    "Operating Expenses": "${:,.2f}",
                    "NOI": "${:,.2f}",
                    "Expense Ratio %": "{:.2f}%",
                    "NOI / Property": "${:,.0f}",
                },
            )

    with right_col:
        with chart_card(
            title="NOI Comparison by Market",
            subtitle=f"Monthly NOI contribution across markets ({period_label})",
            badge="NOI ($)",
            badge_tone="neutral",
        ):
            noi_bar = (
                ranked.set_index("market_name")[["total_noi"]]
                .rename(columns={"total_noi": "Net Operating Income ($)"})
            )
            st.bar_chart(noi_bar)

    return ranked


def _render_trends_and_opex(
    df: pd.DataFrame,
    trend_data: pd.DataFrame,
    ranked_monthly: pd.DataFrame,
    selected_market: str,
) -> pd.DataFrame:
    """Render monthly revenue, NOI, occupancy trends, and operating expense analysis."""
    render_section_header(
        title="Monthly Market Trends & Operating Expense Analysis",
        subtitle=f"Historical performance trajectory and cost efficiency for {selected_market}.",
        badge="12M History",
        badge_tone="neutral",
    )

    trend = (
        trend_data.groupby("month", as_index=False)
        .agg(
            {
                "total_rental_revenue": "sum",
                "total_noi": "sum",
                "total_opex": "sum",
                "net_operating_revenue": "sum",
                "total_occupied_days": "sum",
                "total_service_days": "sum",
            }
        )
        .sort_values("month")
    )
    trend["occupancy_pct"] = (
        trend["total_occupied_days"]
        / trend["total_service_days"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    trend["expense_ratio_pct"] = (
        trend["total_opex"]
        / trend["net_operating_revenue"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    trend["month_label"] = trend["month"].dt.strftime("%Y-%m")
    trend_indexed = trend.set_index("month_label")

    chart1, chart2 = st.columns(2)
    with chart1:
        with chart_card(
            title="Rental Revenue vs. NOI Trend",
            subtitle=f"Monthly revenue and NOI progression ({selected_market})",
            badge="Financials",
            badge_tone="info",
        ):
            st.line_chart(
                trend_indexed[["total_rental_revenue", "total_noi"]].rename(
                    columns={
                        "total_rental_revenue": "Rental Revenue ($)",
                        "total_noi": "Net Operating Income ($)",
                    }
                )
            )

    with chart2:
        avg_occ = float(trend_indexed["occupancy_pct"].mean())
        peak_month = trend_indexed["occupancy_pct"].idxmax()
        low_month = trend_indexed["occupancy_pct"].idxmin()
        with chart_card(
            title="Weighted Occupancy Trend",
            subtitle=f"Monthly occupied days / service days ({selected_market})",
            badge=f"Avg {avg_occ:.2f}%",
            badge_tone="success" if avg_occ >= 90 else "warning",
        ):
            st.line_chart(
                trend_indexed[["occupancy_pct"]].rename(
                    columns={"occupancy_pct": "Weighted Occupancy (%)"}
                )
            )
            st.caption(
                f"Peak: {peak_month} ({trend_indexed.loc[peak_month, 'occupancy_pct']:.2f}%) · "
                f"Low: {low_month} ({trend_indexed.loc[low_month, 'occupancy_pct']:.2f}%)"
            )

    opex_left, opex_right = st.columns(2)
    with opex_left:
        with chart_card(
            title="Operating Expenses vs. NOI by Market",
            subtitle="Selected month cost vs. net operating income comparison ($)",
            badge="Cost Structure",
            badge_tone="neutral",
        ):
            opex_bar = (
                ranked_monthly.set_index("market_name")[["total_opex", "total_noi"]]
                .rename(
                    columns={
                        "total_opex": "Operating Expenses ($)",
                        "total_noi": "Net Operating Income ($)",
                    }
                )
            )
            st.bar_chart(opex_bar)

    with opex_right:
        avg_exp = float(trend_indexed["expense_ratio_pct"].mean())
        with chart_card(
            title="Operating Expense Ratio Trend",
            subtitle=f"Monthly OpEx as a % of Net Operating Revenue ({selected_market})",
            badge=f"Avg {avg_exp:.1f}%",
            badge_tone="neutral",
        ):
            st.line_chart(
                trend_indexed[["expense_ratio_pct"]].rename(
                    columns={"expense_ratio_pct": "Expense Ratio (%)"}
                )
            )

    # Multi-market trajectory breakdown across all 5 markets
    with chart_card(
        title="Cross-Market Trajectory Comparison",
        subtitle="Monthly progression across all markets for NOI and Weighted Occupancy",
        badge="5 Markets",
        badge_tone="info",
    ):
        multi = df.copy()
        multi["month_label"] = multi["month"].dt.strftime("%Y-%m")
        tab_noi, tab_occ, tab_exp = st.tabs(
            ["NOI by Market", "Occupancy % by Market", "Expense Ratio % by Market"]
        )
        with tab_noi:
            piv_noi = multi.pivot_table(
                index="month_label",
                columns="market_name",
                values="total_noi",
                aggfunc="sum",
            ).sort_index()
            st.line_chart(piv_noi)
        with tab_occ:
            piv_occ = multi.pivot_table(
                index="month_label",
                columns="market_name",
                values="occupancy_pct",
                aggfunc="mean",
            ).sort_index()
            st.line_chart(piv_occ)
        with tab_exp:
            piv_exp = multi.pivot_table(
                index="month_label",
                columns="market_name",
                values="expense_ratio_pct",
                aggfunc="mean",
            ).sort_index()
            st.line_chart(piv_exp)

    return trend


def _render_market_insights(
    ranked_monthly: pd.DataFrame,
    current_kpis: Dict[str, float],
    prev_kpis: Optional[Dict[str, float]],
    selected_market: str,
    period_label: str,
) -> None:
    """Render deterministic, Gold-backed market insights and operational actions."""
    render_section_header(
        title="Market Business Insights",
        subtitle="Calculated market dispersion, efficiency benchmarks, and rule-based focus areas.",
        badge="Calculated Metrics",
        badge_tone="success",
    )

    total_monthly_noi = float(ranked_monthly["total_noi"].sum()) or 1.0
    top_mkt = ranked_monthly.iloc[0]
    bottom_mkt = ranked_monthly.iloc[-1]
    top_share = float(top_mkt["total_noi"]) / total_monthly_noi * 100.0

    best_occ = ranked_monthly.loc[ranked_monthly["occupancy_pct"].idxmax()]
    low_occ = ranked_monthly.loc[ranked_monthly["occupancy_pct"].idxmin()]
    occ_spread = float(best_occ["occupancy_pct"]) - float(low_occ["occupancy_pct"])

    best_eff = ranked_monthly.loc[ranked_monthly["expense_ratio_pct"].idxmin()]
    high_cost = ranked_monthly.loc[ranked_monthly["expense_ratio_pct"].idxmax()]

    col1, col2 = st.columns(2)
    with col1:
        render_insight_card(
            title="NOI Leader & Portfolio Contribution",
            body=(
                f"In {period_label}, {top_mkt['market_name']} ranked #1 with "
                f"${top_mkt['total_noi']:,.0f} NOI ({top_share:.1f}% of monthly portfolio NOI, "
                f"${top_mkt['noi_per_property']:,.0f} per property), while {bottom_mkt['market_name']} "
                f"ranked #{int(bottom_mkt['rank'])} at ${bottom_mkt['total_noi']:,.0f}."
            ),
            tone="success",
            tag="Calculated",
        )
        render_insight_card(
            title="Occupancy Spread Across Markets",
            body=(
                f"{best_occ['market_name']} led occupancy at {best_occ['occupancy_pct']:.2f}% "
                f"compared with {low_occ['market_name']} at {low_occ['occupancy_pct']:.2f}% "
                f"— a {occ_spread:.2f} percentage-point gap."
            ),
            tone="info" if occ_spread < 5 else "warning",
            tag="Calculated",
        )

    with col2:
        render_insight_card(
            title="Operating Expense Efficiency",
            body=(
                f"{best_eff['market_name']} operated most leanly at a {best_eff['expense_ratio_pct']:.2f}% "
                f"expense ratio, whereas {high_cost['market_name']} carried the highest ratio at "
                f"{high_cost['expense_ratio_pct']:.2f}% (${high_cost['total_opex']:,.0f} OpEx)."
            ),
            tone="info",
            tag="Calculated",
        )

        if prev_kpis is not None:
            noi_mom = pct_change(current_kpis["noi"], prev_kpis["noi"])
            occ_mom = current_kpis["occupancy"] - prev_kpis["occupancy"]
            mom_txt = (
                f"{selected_market} NOI changed {noi_mom:+.1f}% MoM and occupancy shifted "
                f"{occ_mom:+.2f} pp vs. prior month. "
                if noi_mom is not None
                else ""
            )
        else:
            mom_txt = f"{selected_market} is on the earliest available reporting month. "

        render_insight_card(
            title="Recommended Market Focus",
            body=(
                f"{mom_txt}Prioritize expense benchmarking in {high_cost['market_name']} "
                f"({high_cost['expense_ratio_pct']:.1f}% expense ratio) and leasing velocity "
                f"reviews in {low_occ['market_name']} ({low_occ['occupancy_pct']:.2f}% occupancy)."
            ),
            tone="neutral",
            tag="Rule-Based Action",
        )


def main() -> None:
    """Render the Market Analytics AI Studio page."""
    apply_theme()
    render_header("Markets")

    try:
        with st.spinner("Loading market performance data from Databricks Gold layer..."):
            payload = load_market_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Market Analytics",
                description="Compare residential property performance across markets.",
                domain_label="Markets",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No Market Data Available",
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

        months = sorted(
            [pd.Timestamp(m) for m in df["month"].dropna().unique()],
            reverse=True,
        )
        market_names = ["All Markets"] + sorted(df["market_name"].dropna().unique().tolist())

        # Filter bar inside a clean AI Studio card
        with st.container(border=True):
            f_col1, f_col2, f_col3 = st.columns([2.2, 2.2, 0.9])
            with f_col1:
                selected_month = st.selectbox(
                    "Reporting Month",
                    months,
                    format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"),
                )
            with f_col2:
                selected_market = st.selectbox("Market", market_names)
            with f_col3:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", use_container_width=True):
                    load_market_data.clear()
                    st.rerun()

        period_label = pd.Timestamp(selected_month).strftime("%B %Y")

        render_page_header(
            title="Market Analytics",
            description=(
                "Executive regional benchmarking across occupancy, rental revenue, "
                "operating expenses, and net operating income."
            ),
            domain_label="Markets · AI Studio",
            reporting_period=f"{period_label} · {selected_market}",
            status_text=freshness_badge,
            status_tone="success",
        )

        monthly = df[df["month"] == selected_month].copy()

        if selected_market != "All Markets":
            filtered = monthly[monthly["market_name"] == selected_market].copy()
            trend_data = df[df["market_name"] == selected_market].copy()
        else:
            filtered = monthly.copy()
            trend_data = df.copy()

        if filtered.empty:
            render_empty_state(
                "No Matching Market Records",
                "No records matched the selected Reporting Month and Market filters.",
                tone="warning",
            )
            st.stop()

        # Find prior month for MoM comparison
        month_idx = months.index(selected_month)
        prev_month = months[month_idx + 1] if month_idx + 1 < len(months) else None
        prev_kpis: Optional[Dict[str, float]] = None
        if prev_month is not None:
            prev_slice = df[df["month"] == prev_month]
            if selected_market != "All Markets":
                prev_slice = prev_slice[prev_slice["market_name"] == selected_market]
            if not prev_slice.empty:
                prev_kpis = _aggregate_market_slice(prev_slice)

        current_kpis = _aggregate_market_slice(filtered)

        render_section_header(
            title="Executive Market KPIs",
            subtitle=f"Aggregated performance for {selected_market} in {period_label}.",
            badge=period_label,
            badge_tone="neutral",
        )
        render_kpi_row(
            _build_kpi_cards(
                current=current_kpis,
                previous=prev_kpis,
                period_label=period_label,
                scope_label=selected_market,
            )
        )

        ranked_monthly = _render_ranking_and_comparison(
            monthly=monthly, period_label=period_label
        )
        _render_trends_and_opex(
            df=df,
            trend_data=trend_data,
            ranked_monthly=ranked_monthly,
            selected_market=selected_market,
        )
        _render_market_insights(
            ranked_monthly=ranked_monthly,
            current_kpis=current_kpis,
            prev_kpis=prev_kpis,
            selected_market=selected_market,
            period_label=period_label,
        )

        with st.expander("View detailed market records"):
            st.dataframe(
                df.sort_values(["month", "market_name"], ascending=[False, True]),
                use_container_width=True,
                hide_index=True,
            )

    except Exception as exc:
        render_page_header(
            title="Market Analytics",
            description="Compare residential property performance across markets.",
            domain_label="Markets",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load market analytics.")
        st.exception(exc)


if __name__ == "__main__":
    main()

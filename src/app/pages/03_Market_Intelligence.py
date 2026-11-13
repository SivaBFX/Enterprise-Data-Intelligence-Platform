"""Market Intelligence enterprise analytical dashboard.

Provides regional benchmarking, market-level property counts, occupancy comparisons,
operating expense ratios, and dedicated market drill-downs.
"""

from typing import Any, Dict, List, Optional

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
    page_title="Market Intelligence · Enterprise SaaS",
    page_icon=":material/public:",
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
        df["noi_margin_pct"] = (
            df["total_noi"]
            / df["total_rental_revenue"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)
        df["opex_ratio_pct"] = (
            df["total_opex"]
            / df["total_rental_revenue"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)

    freshness = get_table_freshness(table_name)
    return {"table_name": table_name, "df": df, "freshness": freshness}


def _aggregate_market_slice(slice_df: pd.DataFrame) -> Dict[str, float]:
    """Aggregate a cohort slice of market monthly records into top-line KPIs."""
    if slice_df.empty:
        return {
            "properties": 0,
            "occupied_days": 0,
            "service_days": 0,
            "occupancy": 0.0,
            "revenue": 0.0,
            "noi": 0.0,
            "opex": 0.0,
            "net_operating_revenue": 0.0,
            "expense_ratio": 0.0,
            "noi_margin": 0.0,
            "property_count": 0,
            "total_rental_revenue": 0.0,
            "total_opex": 0.0,
            "total_noi": 0.0,
            "occupancy_pct": 0.0,
            "noi_margin_pct": 0.0,
            "opex_ratio_pct": 0.0,
            "total_occupied_days": 0,
            "total_service_days": 0,
        }

    prop_count = int(slice_df["property_count"].sum())
    rev = float(slice_df["total_rental_revenue"].sum())
    opex = float(slice_df["total_opex"].sum())
    noi = float(slice_df["total_noi"].sum())
    net_rev = float(slice_df["net_operating_revenue"].sum()) if "net_operating_revenue" in slice_df.columns else rev
    occ_days = float(slice_df["total_occupied_days"].sum())
    svc_days = float(slice_df["total_service_days"].sum())
    occupancy = (occ_days / svc_days * 100.0) if svc_days else 0.0
    noi_margin = (noi / rev * 100.0) if rev else 0.0
    opex_ratio = (opex / rev * 100.0) if rev else 0.0

    return {
        "properties": prop_count,
        "occupied_days": int(occ_days),
        "service_days": int(svc_days),
        "occupancy": occupancy,
        "revenue": rev,
        "noi": noi,
        "opex": opex,
        "net_operating_revenue": net_rev,
        "expense_ratio": opex_ratio,
        "noi_margin": noi_margin,
        "property_count": prop_count,
        "total_rental_revenue": rev,
        "total_opex": opex,
        "total_noi": noi,
        "occupancy_pct": occupancy,
        "noi_margin_pct": noi_margin,
        "opex_ratio_pct": opex_ratio,
        "total_occupied_days": int(occ_days),
        "total_service_days": int(svc_days),
    }


def _build_kpi_cards(
    current: Dict[str, float],
    previous: Optional[Dict[str, float]],
    period_label: str,
    scope_label: str,
) -> List[Dict[str, Any]]:
    """Construct executive KPI cards with period-over-period comparisons."""
    rev_delta = (
        pct_change(current["total_rental_revenue"], previous["total_rental_revenue"])
        if previous
        else None
    )
    noi_delta = (
        pct_change(current["total_noi"], previous["total_noi"]) if previous else None
    )
    occ_diff = (
        (current["occupancy_pct"] - previous["occupancy_pct"]) if previous else None
    )
    margin_diff = (
        (current["noi_margin_pct"] - previous["noi_margin_pct"]) if previous else None
    )

    return [
        {
            "label": "Total Properties",
            "value": f"{int(current['property_count']):,}",
            "delta": f"{scope_label}",
            "delta_tone": "neutral",
            "caption": f"Assets in {period_label}",
        },
        {
            "label": "Weighted Occupancy",
            "value": f"{current['occupancy_pct']:.2f}%",
            "delta": (
                f"{occ_diff:+.2f} pts MoM" if occ_diff is not None else "Baseline"
            ),
            "delta_tone": (
                "success"
                if (occ_diff or 0) >= 0
                else ("danger" if (occ_diff or 0) < -1 else "warning")
            ),
            "caption": f"{current['total_occupied_days']:,} / {current['total_service_days']:,} days",
        },
        {
            "label": "Total Rental Revenue",
            "value": f"${current['total_rental_revenue']:,.2f}",
            "delta": (
                f"{rev_delta:+.1f}% MoM" if rev_delta is not None else "Current Month"
            ),
            "delta_tone": (
                "success"
                if (rev_delta or 0) >= 0
                else ("danger" if (rev_delta or 0) < -5 else "warning")
            ),
            "caption": "Gross rental income",
        },
        {
            "label": "Total OpEx",
            "value": f"${current['total_opex']:,.2f}",
            "delta": f"{current['opex_ratio_pct']:.1f}% of revenue",
            "delta_tone": "neutral",
            "caption": "Operating expenditures",
        },
        {
            "label": "Net Operating Income",
            "value": f"${current['total_noi']:,.2f}",
            "delta": (
                f"{noi_delta:+.1f}% MoM" if noi_delta is not None else "Current Month"
            ),
            "delta_tone": "success" if (noi_delta or 0) >= 0 else "danger",
            "caption": "Rental revenue minus OpEx",
        },
        {
            "label": "NOI Margin",
            "value": f"{current['noi_margin_pct']:.1f}%",
            "delta": (
                f"{margin_diff:+.1f} pts MoM" if margin_diff is not None else "Baseline"
            ),
            "delta_tone": "success" if (margin_diff or 0) >= 0 else "warning",
            "caption": "NOI / Rental Revenue",
        },
    ]


def main() -> None:
    """Render the Market Intelligence enterprise page."""
    apply_theme()
    render_header("Market Intelligence")

    try:
        with st.spinner("Loading market performance data from Databricks Gold layer..."):
            payload = load_market_data()

        df = payload["df"]
        if df.empty:
            render_page_header(
                title="Market Intelligence",
                description="Compare residential property performance across markets.",
                domain_label="Market Intelligence",
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

        with st.container(border=True):
            f_col1, f_col2, f_col3 = st.columns([2.2, 2.2, 0.9])
            with f_col1:
                selected_month = st.selectbox(
                    "Reporting Month",
                    months,
                    format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"),
                )
            with f_col2:
                selected_market = st.selectbox("Market Filter", market_names)
            with f_col3:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Data", key="market_refresh_btn", use_container_width=True):
                    load_market_data.clear()
                    st.rerun()

        period_label = pd.Timestamp(selected_month).strftime("%B %Y")

        render_page_header(
            title="Market Intelligence",
            description="Regional benchmarking across occupancy, rental revenue, operating expenses, and net operating income.",
            domain_label="Portfolio Intelligence",
            reporting_period=f"{period_label} · {selected_market}",
            status_text=freshness_badge,
            status_tone="success",
        )

        monthly = df[df["month"] == selected_month].copy()
        if selected_market != "All Markets":
            filtered = monthly[monthly["market_name"] == selected_market].copy()
        else:
            filtered = monthly.copy()

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
                previous=None,
                period_label=period_label,
                scope_label=selected_market,
            )
        )

        with chart_card(
            title="Market Comparison & Rankings",
            subtitle=f"Comparing all markets for {period_label}",
        ):
            render_formatted_table(
                monthly.sort_values("total_noi", ascending=False),
                column_labels={
                    "market_name": "Market",
                    "region": "Region",
                    "property_count": "Properties",
                    "occupancy_pct": "Occupancy (%)",
                    "total_rental_revenue": "Revenue ($)",
                    "total_opex": "OpEx ($)",
                    "total_noi": "Total NOI ($)",
                    "noi_margin_pct": "NOI Margin (%)",
                },
                formats={
                    "occupancy_pct": "{:.2f}%",
                    "total_rental_revenue": "${:,.2f}",
                    "total_opex": "${:,.2f}",
                    "total_noi": "${:,.2f}",
                    "noi_margin_pct": "{:.2f}%",
                },
            )

        with chart_card(
            title="Net Operating Income by Market",
            subtitle=f"Contribution to portfolio NOI in {period_label}",
        ):
            mkt_noi = monthly.set_index("market_name")["total_noi"].sort_values(ascending=False)
            st.bar_chart(mkt_noi, color="#119B78")

    except Exception as exc:
        render_page_header(
            title="Market Intelligence",
            description="Compare residential property performance across markets.",
            domain_label="Market Intelligence",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load market intelligence.")
        st.exception(exc)


if __name__ == "__main__":
    main()

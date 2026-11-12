"""Executive Portfolio AI Studio dashboard (Milestone 2)."""

import html
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from utils.database import (
    coerce_numeric,
    get_table_freshness,
    get_table_row_count,
    query_table,
    resolve_table_name,
    run_query,
)
from utils.genie import (
    SUGGESTED_QUESTIONS,
    GenieResponse,
    ask_genie,
    is_genie_configured,
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
    status_badge_html,
)

LOW_OCCUPANCY_THRESHOLD_PCT = 85.0

st.set_page_config(
    page_title="Property Intelligence · AI Studio",
    page_icon="🏢",
    layout="wide",
)


def _sort_portfolio_months(df: pd.DataFrame) -> pd.DataFrame:
    """Sort monthly portfolio KPI records chronologically."""
    ordered = df.copy()
    parsed = pd.to_datetime(ordered["month_year"], errors="coerce")
    if parsed.notna().all():
        ordered["_sort_key"] = parsed
    else:
        ordered["_sort_key"] = ordered["month_year"].astype(str)
    ordered = ordered.sort_values("_sort_key").drop(columns=["_sort_key"]).reset_index(drop=True)
    return ordered


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_data() -> Dict[str, Any]:
    """Load all verified Gold datasets and table freshness metadata."""
    portfolio_table = resolve_table_name(
        "PORTFOLIO_KPIS_TABLE", "workspace.gold.gold_portfolio_kpis"
    )
    market_table = resolve_table_name(
        "MARKET_MONTHLY_TABLE", "workspace.gold.gold_market_monthly"
    )
    property_table = resolve_table_name(
        "PROPERTY_PERFORMANCE_TABLE", "workspace.gold.gold_property_performance"
    )
    maintenance_table = resolve_table_name(
        "MAINTENANCE_TABLE", "workspace.gold.gold_maintenance_summary"
    )
    capex_table = resolve_table_name(
        "CAPEX_TABLE", "workspace.gold.gold_capex_summary"
    )

    portfolio_df = query_table(portfolio_table, limit=100)
    market_df = query_table(market_table, limit=1000)
    property_df = query_table(property_table, limit=1000)
    maintenance_df = query_table(maintenance_table, limit=1000)

    if not portfolio_df.empty:
        portfolio_df = coerce_numeric(
            portfolio_df,
            [
                "total_properties",
                "total_occupied_days",
                "total_service_days",
                "total_rental_revenue",
                "total_noi",
            ],
        )
        portfolio_df = _sort_portfolio_months(portfolio_df)
        portfolio_df["occupancy_pct"] = (
            portfolio_df["total_occupied_days"]
            / portfolio_df["total_service_days"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)

    if not market_df.empty:
        market_df = coerce_numeric(
            market_df,
            [
                "property_count",
                "total_occupied_days",
                "total_service_days",
                "total_rental_revenue",
                "total_noi",
                "total_opex",
                "net_operating_revenue",
            ],
        )
        market_df["month_dt"] = pd.to_datetime(market_df["month"], errors="coerce")
        market_df["occupancy_pct"] = (
            market_df["total_occupied_days"]
            / market_df["total_service_days"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)
        market_df["expense_ratio_pct"] = (
            market_df["total_opex"]
            / market_df["net_operating_revenue"].replace(0, pd.NA)
            * 100.0
        ).fillna(0.0)

    if not property_df.empty:
        property_df = coerce_numeric(
            property_df,
            [
                "bedrooms",
                "total_occupied_days",
                "total_service_days",
                "overall_occupancy_pct",
                "total_rental_revenue",
                "total_noi",
                "avg_monthly_noi",
                "operating_expense_ratio_pct",
            ],
        )

    if not maintenance_df.empty:
        maintenance_df = coerce_numeric(
            maintenance_df,
            [
                "total_work_orders",
                "total_maintenance_cost",
                "avg_work_order_cost",
                "avg_completion_days",
                "open_work_orders",
                "in_progress_work_orders",
                "completed_work_orders",
                "cancelled_work_orders",
            ],
        )

    freshness = {
        portfolio_table: get_table_freshness(portfolio_table),
        market_table: get_table_freshness(market_table),
        property_table: get_table_freshness(property_table),
        maintenance_table: get_table_freshness(maintenance_table),
        capex_table: get_table_freshness(capex_table),
    }

    capex_rows = get_table_row_count(capex_table)
    capex_totals = {"total_capex_amount": 0.0, "investment_count": 0}
    try:
        capex_agg = run_query(
            f"SELECT COALESCE(SUM(total_capex_amount), 0) AS total_capex_amount, "
            f"COALESCE(SUM(investment_count), 0) AS investment_count "
            f"FROM {capex_table}"
        )
        if not capex_agg.empty:
            capex_agg = coerce_numeric(capex_agg, ["total_capex_amount", "investment_count"])
            capex_totals["total_capex_amount"] = float(capex_agg.iloc[0]["total_capex_amount"])
            capex_totals["investment_count"] = int(capex_agg.iloc[0]["investment_count"])
    except Exception:
        pass

    return {
        "tables": {
            "portfolio": portfolio_table,
            "market": market_table,
            "property": property_table,
            "maintenance": maintenance_table,
            "capex": capex_table,
        },
        "portfolio_df": portfolio_df,
        "market_df": market_df,
        "property_df": property_df,
        "maintenance_df": maintenance_df,
        "capex_rows": capex_rows,
        "capex_totals": capex_totals,
        "freshness": freshness,
    }


def compute_portfolio_summary(
    portfolio_df: pd.DataFrame,
    maintenance_df: pd.DataFrame,
    capex_totals: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute top-level KPI values and period-over-period comparisons."""
    latest = portfolio_df.iloc[-1]
    prev = portfolio_df.iloc[-2] if len(portfolio_df) >= 2 else None

    total_properties = int(latest["total_properties"])
    occupancy = float(latest["occupancy_pct"])
    latest_revenue = float(latest["total_rental_revenue"])
    latest_noi = float(latest["total_noi"])

    noi_margin = (latest_noi / latest_revenue * 100.0) if latest_revenue else 0.0
    cum_revenue = float(portfolio_df["total_rental_revenue"].sum())

    occ_delta = (occupancy - float(prev["occupancy_pct"])) if prev is not None else None
    rev_delta = (
        pct_change(latest_revenue, float(prev["total_rental_revenue"]))
        if prev is not None
        else None
    )
    noi_delta = (
        pct_change(latest_noi, float(prev["total_noi"]))
        if prev is not None
        else None
    )
    prop_delta = (
        total_properties - int(prev["total_properties"]) if prev is not None else 0
    )

    total_maint_cost = (
        float(maintenance_df["total_maintenance_cost"].sum())
        if not maintenance_df.empty
        else 0.0
    )
    total_work_orders = (
        int(maintenance_df["total_work_orders"].sum())
        if not maintenance_df.empty
        else 0
    )
    active_work_orders = (
        int(
            maintenance_df["open_work_orders"].sum()
            + maintenance_df["in_progress_work_orders"].sum()
        )
        if not maintenance_df.empty
        else 0
    )

    cards = [
        {
            "label": "Total Properties",
            "value": f"{total_properties:,}",
            "delta": f"{prop_delta:+d} MoM" if prev is not None and prop_delta != 0 else "Active Portfolio",
            "delta_tone": "success" if prop_delta >= 0 else "warning",
            "caption": f"Period: {latest['month_year']}",
            "icon": "🏢",
        },
        {
            "label": "Weighted Occupancy",
            "value": f"{occupancy:.2f}%",
            "delta": f"{occ_delta:+.2f} pp MoM" if occ_delta is not None else "Latest Month",
            "delta_tone": "success" if (occ_delta is None or occ_delta >= 0) else "warning",
            "caption": f"{int(latest['total_occupied_days']):,} / {int(latest['total_service_days']):,} days",
            "icon": "🔑",
        },
        {
            "label": "Rental Revenue",
            "value": f"${latest_revenue:,.0f}",
            "delta": f"{rev_delta:+.1f}% MoM" if rev_delta is not None else "Latest Month",
            "delta_tone": "success" if (rev_delta is None or rev_delta >= 0) else "warning",
            "caption": f"Cumulative ({len(portfolio_df)}M): ${cum_revenue:,.0f}",
            "icon": "💵",
        },
        {
            "label": "Net Operating Income",
            "value": f"${latest_noi:,.0f}",
            "delta": f"{noi_delta:+.1f}% MoM" if noi_delta is not None else "Latest Month",
            "delta_tone": "success" if (noi_delta is None or noi_delta >= 0) else "danger",
            "caption": f"NOI margin: {noi_margin:.1f}%",
            "icon": "📈",
        },
        {
            "label": "Maintenance Cost",
            "value": f"${total_maint_cost:,.0f}",
            "delta": f"{active_work_orders:,} active WOs",
            "delta_tone": "warning" if active_work_orders > 0 else "success",
            "caption": f"{total_work_orders:,} total work orders",
            "icon": "🔧",
        },
        {
            "label": "CapEx Investment",
            "value": f"${float(capex_totals.get('total_capex_amount', 0.0)):,.0f}",
            "delta": f"{int(capex_totals.get('investment_count', 0)):,} investments",
            "delta_tone": "info",
            "caption": (
                f"Avg ${float(capex_totals['total_capex_amount']) / int(capex_totals['investment_count']):,.0f} / investment"
                if int(capex_totals.get("investment_count", 0)) > 0
                else "From gold_capex_summary"
            ),
            "icon": "🏗️",
        },
    ]

    return {
        "cards": cards,
        "latest_month": str(latest["month_year"]),
        "history_start": str(portfolio_df.iloc[0]["month_year"]),
        "history_months": len(portfolio_df),
        "occupancy": occupancy,
        "occ_delta": occ_delta,
        "latest_revenue": latest_revenue,
        "rev_delta": rev_delta,
        "latest_noi": latest_noi,
        "noi_delta": noi_delta,
        "noi_margin": noi_margin,
        "total_maint_cost": total_maint_cost,
        "active_work_orders": active_work_orders,
        "total_work_orders": total_work_orders,
    }


def build_decision_queues(
    market_df: pd.DataFrame,
    property_df: pd.DataFrame,
    maintenance_df: pd.DataFrame,
    portfolio_occupancy: float,
) -> Dict[str, Any]:
    """Identify flagged properties and markets requiring executive attention."""
    low_occ_df = pd.DataFrame()
    low_noi_df = pd.DataFrame()
    high_maint_df = pd.DataFrame()
    attention_markets_df = pd.DataFrame()

    if not property_df.empty:
        low_occ_df = (
            property_df[property_df["overall_occupancy_pct"] < LOW_OCCUPANCY_THRESHOLD_PCT]
            .sort_values("overall_occupancy_pct", ascending=True)
            .copy()
        )

        negative_noi = property_df[property_df["total_noi"] <= 0].sort_values(
            "total_noi", ascending=True
        )
        if not negative_noi.empty:
            low_noi_df = negative_noi.copy()
            noi_mode = "negative"
        else:
            low_noi_df = property_df.nsmallest(10, "total_noi").copy()
            noi_mode = "bottom10"
    else:
        noi_mode = "empty"

    if not maintenance_df.empty:
        p90_cost = float(maintenance_df["total_maintenance_cost"].quantile(0.9))
        high_maint_df = (
            maintenance_df[maintenance_df["total_maintenance_cost"] >= p90_cost]
            .sort_values("total_maintenance_cost", ascending=False)
            .copy()
        )
        maint_threshold = p90_cost
    else:
        maint_threshold = 0.0

    latest_markets = pd.DataFrame()
    if not market_df.empty:
        latest_dt = market_df["month_dt"].max()
        if pd.notna(latest_dt):
            latest_markets = market_df[market_df["month_dt"] == latest_dt].copy()
        else:
            latest_month_val = market_df["month"].max()
            latest_markets = market_df[market_df["month"] == latest_month_val].copy()

        if not latest_markets.empty:
            avg_exp_ratio = float(latest_markets["expense_ratio_pct"].mean())
            drivers: List[str] = []
            for _, row in latest_markets.iterrows():
                reasons = []
                if float(row["occupancy_pct"]) < portfolio_occupancy:
                    reasons.append("Below portfolio occupancy")
                if float(row["expense_ratio_pct"]) > avg_exp_ratio:
                    reasons.append("Above avg expense ratio")
                if float(row["total_noi"]) <= 0:
                    reasons.append("Non-positive NOI")
                drivers.append(", ".join(reasons) if reasons else "Within target range")
            latest_markets["attention_driver"] = drivers
            attention_markets_df = latest_markets[
                latest_markets["attention_driver"] != "Within target range"
            ].sort_values("total_noi", ascending=True)

    return {
        "low_occ_df": low_occ_df,
        "low_noi_df": low_noi_df,
        "noi_mode": noi_mode,
        "high_maint_df": high_maint_df,
        "maint_threshold": maint_threshold,
        "latest_markets": latest_markets,
        "attention_markets_df": attention_markets_df,
    }


def render_genie_bar() -> None:
    """Render the Databricks Genie natural-language question bar and answer box."""
    with chart_card(
        title="Ask Residential Property Intelligence Genie",
        subtitle="Query Gold portfolio, market, property, and maintenance datasets in natural language.",
        badge="Databricks Genie" if is_genie_configured() else "Not Configured",
        badge_tone="info" if is_genie_configured() else "warning",
    ):
        if "genie_question_input" not in st.session_state:
            st.session_state["genie_question_input"] = ""
        if "genie_last_response" not in st.session_state:
            st.session_state["genie_last_response"] = None
        if "genie_conversation_id" not in st.session_state:
            st.session_state["genie_conversation_id"] = None

        triggered_question: Optional[str] = None

        input_col, ask_col, clear_col = st.columns([5.2, 1.2, 1.0])
        with input_col:
            question_text = st.text_input(
                "Ask a business question",
                key="genie_question_input",
                placeholder="e.g., Which market had the highest NOI margin in the latest month?",
                label_visibility="collapsed",
            )
        with ask_col:
            if st.button("Ask Genie", type="primary", use_container_width=True):
                triggered_question = question_text
        with clear_col:
            if st.button("New Topic", use_container_width=True):
                st.session_state["genie_conversation_id"] = None
                st.session_state["genie_last_response"] = None
                st.rerun()

        st.caption("Suggested executive questions:")
        s_cols = st.columns(len(SUGGESTED_QUESTIONS))
        for idx, (col, suggestion) in enumerate(zip(s_cols, SUGGESTED_QUESTIONS)):
            with col:
                if st.button(suggestion, key=f"genie_suggest_{idx}", use_container_width=True):
                    triggered_question = suggestion

        if triggered_question is not None:
            with st.spinner("Consulting Databricks Genie..."):
                response = ask_genie(
                    question=triggered_question,
                    conversation_id=st.session_state.get("genie_conversation_id"),
                )
            st.session_state["genie_last_response"] = response
            if response.success and response.conversation_id:
                st.session_state["genie_conversation_id"] = response.conversation_id

        last_resp: Optional[GenieResponse] = st.session_state.get("genie_last_response")
        if last_resp is None:
            return

        st.divider()
        if not last_resp.success:
            st.warning(last_resp.error_message or "Genie could not complete this request.")
            return

        st.markdown(
            f"{status_badge_html('AI-Generated (Genie)', tone='info')} "
            f"&nbsp; **Question:** {html.escape(last_resp.question)}",
            unsafe_allow_html=True,
        )

        if last_resp.text_answers:
            for answer_block in last_resp.text_answers:
                st.markdown(answer_block)
        elif last_resp.sql_description:
            st.markdown(last_resp.sql_description)

        if last_resp.dataframe is not None and not last_resp.dataframe.empty:
            st.dataframe(last_resp.dataframe, use_container_width=True, hide_index=True)

        if last_resp.sql_query:
            with st.expander("View SQL generated by Genie"):
                st.code(last_resp.sql_query, language="sql")


def render_performance_section(
    portfolio_df: pd.DataFrame,
    latest_markets: pd.DataFrame,
) -> None:
    """Render portfolio financial trends, occupancy trend, and market snapshot."""
    render_section_header(
        title="Portfolio Performance",
        subtitle="12-month revenue, net operating income, occupancy trajectory, and market comparison.",
        badge="Gold Layer Metrics",
        badge_tone="success",
    )

    trend_df = portfolio_df.set_index("month_year")

    col_left, col_right = st.columns(2)
    with col_left:
        with chart_card(
            title="Rental Revenue & NOI Trend",
            subtitle="Monthly portfolio top-line revenue vs. net operating income ($)",
            badge=f"{len(portfolio_df)} Months",
            badge_tone="neutral",
        ):
            fin_chart = trend_df[["total_rental_revenue", "total_noi"]].rename(
                columns={
                    "total_rental_revenue": "Rental Revenue ($)",
                    "total_noi": "Net Operating Income ($)",
                }
            )
            st.line_chart(fin_chart)

    with col_right:
        avg_occ = float(portfolio_df["occupancy_pct"].mean())
        peak_row = portfolio_df.loc[portfolio_df["occupancy_pct"].idxmax()]
        low_row = portfolio_df.loc[portfolio_df["occupancy_pct"].idxmin()]

        with chart_card(
            title="Weighted Occupancy Trend",
            subtitle="Portfolio occupied days as a share of total service days (%)",
            badge=f"Avg {avg_occ:.2f}%",
            badge_tone="success" if avg_occ >= 90 else "warning",
        ):
            occ_chart = trend_df[["occupancy_pct"]].rename(
                columns={"occupancy_pct": "Weighted Occupancy (%)"}
            )
            st.line_chart(occ_chart)
            st.caption(
                f"Peak: {peak_row['month_year']} ({peak_row['occupancy_pct']:.2f}%) · "
                f"Low: {low_row['month_year']} ({low_row['occupancy_pct']:.2f}%)"
            )

    if not latest_markets.empty:
        m_left, m_right = st.columns([1.45, 1.0])
        with m_left:
            with chart_card(
                title="Market Performance Snapshot",
                subtitle="Latest reporting month comparison across all regional markets",
                badge=f"{len(latest_markets)} Markets",
                badge_tone="neutral",
            ):
                render_formatted_table(
                    latest_markets.sort_values("total_noi", ascending=False),
                    column_labels={
                        "market_name": "Market",
                        "region": "Region",
                        "property_count": "Properties",
                        "occupancy_pct": "Occupancy %",
                        "total_rental_revenue": "Rental Revenue",
                        "total_opex": "OpEx",
                        "total_noi": "NOI",
                        "expense_ratio_pct": "Expense Ratio %",
                    },
                    formats={
                        "Properties": "{:,.0f}",
                        "Occupancy %": "{:.2f}%",
                        "Rental Revenue": "${:,.0f}",
                        "OpEx": "${:,.0f}",
                        "NOI": "${:,.0f}",
                        "Expense Ratio %": "{:.1f}%",
                    },
                )

        with m_right:
            with chart_card(
                title="NOI by Market",
                subtitle="Latest reporting month net operating income contribution ($)",
                badge="Ranking",
                badge_tone="info",
            ):
                noi_bar = (
                    latest_markets.sort_values("total_noi", ascending=False)
                    .set_index("market_name")[["total_noi"]]
                    .rename(columns={"total_noi": "Net Operating Income ($)"})
                )
                st.bar_chart(noi_bar)


def render_decision_queue_section(queues: Dict[str, Any]) -> None:
    """Render operational decision queues for low occupancy, NOI, maintenance, and markets."""
    low_occ_df = queues["low_occ_df"]
    low_noi_df = queues["low_noi_df"]
    high_maint_df = queues["high_maint_df"]
    attention_markets_df = queues["attention_markets_df"]

    total_flagged = (
        len(low_occ_df)
        + (len(low_noi_df) if queues["noi_mode"] == "negative" else 0)
        + len(high_maint_df)
        + len(attention_markets_df)
    )

    render_section_header(
        title="Executive Decision Queue",
        subtitle="Prioritized assets and markets requiring operational review based on Gold thresholds.",
        badge=f"{total_flagged} Flagged Items",
        badge_tone="warning" if total_flagged > 0 else "success",
    )

    with st.container(border=True):
        tab_occ, tab_noi, tab_maint, tab_mkt = st.tabs(
            [
                f"Low Occupancy ({len(low_occ_df)})",
                f"Negative / Low NOI ({len(low_noi_df)})",
                f"High Maintenance Cost ({len(high_maint_df)})",
                f"Markets Attention ({len(attention_markets_df)})",
            ]
        )

        with tab_occ:
            if low_occ_df.empty:
                render_empty_state(
                    "No Properties Below 85% Occupancy",
                    "All portfolio properties currently meet or exceed the 85.0% occupancy threshold.",
                    tone="success",
                )
            else:
                st.caption(
                    f"Showing properties with overall occupancy below {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}%."
                )
                render_formatted_table(
                    low_occ_df,
                    column_labels={
                        "property_id": "Property ID",
                        "market_name": "Market",
                        "property_type": "Type",
                        "overall_occupancy_pct": "Occupancy %",
                        "total_noi": "Total NOI",
                        "operating_expense_ratio_pct": "Expense Ratio %",
                    },
                    formats={
                        "Occupancy %": "{:.2f}%",
                        "Total NOI": "${:,.0f}",
                        "Expense Ratio %": "{:.1f}%",
                    },
                )

        with tab_noi:
            if low_noi_df.empty:
                render_empty_state(
                    "No NOI Records Available",
                    "Property performance records could not be evaluated.",
                    tone="neutral",
                )
            else:
                if queues["noi_mode"] == "negative":
                    st.caption("Showing properties with non-positive total NOI (<= $0).")
                else:
                    st.caption(
                        "No properties have negative total NOI; showing the 10 lowest-NOI properties for margin review."
                    )
                render_formatted_table(
                    low_noi_df,
                    column_labels={
                        "property_id": "Property ID",
                        "market_name": "Market",
                        "property_type": "Type",
                        "overall_occupancy_pct": "Occupancy %",
                        "total_rental_revenue": "Rental Revenue",
                        "total_noi": "Total NOI",
                        "avg_monthly_noi": "Avg Monthly NOI",
                    },
                    formats={
                        "Occupancy %": "{:.2f}%",
                        "Rental Revenue": "${:,.0f}",
                        "Total NOI": "${:,.0f}",
                        "Avg Monthly NOI": "${:,.0f}",
                    },
                )

        with tab_maint:
            if high_maint_df.empty:
                render_empty_state(
                    "No Maintenance Records Available",
                    "Maintenance summary data could not be loaded.",
                    tone="neutral",
                )
            else:
                st.caption(
                    f"Showing top-decile maintenance spend properties (>= ${queues['maint_threshold']:,.0f})."
                )
                render_formatted_table(
                    high_maint_df,
                    column_labels={
                        "property_id": "Property ID",
                        "market_name": "Market",
                        "region": "Region",
                        "total_maintenance_cost": "Maintenance Cost",
                        "total_work_orders": "Total WOs",
                        "open_work_orders": "Open WOs",
                        "in_progress_work_orders": "In Progress",
                        "avg_completion_days": "Avg Completion (Days)",
                    },
                    formats={
                        "Maintenance Cost": "${:,.0f}",
                        "Total WOs": "{:,.0f}",
                        "Open WOs": "{:,.0f}",
                        "In Progress": "{:,.0f}",
                        "Avg Completion (Days)": "{:.1f}",
                    },
                )

        with tab_mkt:
            if attention_markets_df.empty:
                render_empty_state(
                    "All Markets Within Baseline",
                    "No regional markets fell below portfolio occupancy or above average expense ratio in the latest month.",
                    tone="success",
                )
            else:
                st.caption(
                    "Markets trailing portfolio weighted occupancy or exceeding average operating expense ratio in the latest month."
                )
                render_formatted_table(
                    attention_markets_df,
                    column_labels={
                        "market_name": "Market",
                        "region": "Region",
                        "property_count": "Properties",
                        "occupancy_pct": "Occupancy %",
                        "total_noi": "NOI",
                        "expense_ratio_pct": "Expense Ratio %",
                        "attention_driver": "Attention Driver",
                    },
                    formats={
                        "Properties": "{:,.0f}",
                        "Occupancy %": "{:.2f}%",
                        "NOI": "${:,.0f}",
                        "Expense Ratio %": "{:.1f}%",
                    },
                )


def render_insights_and_operations(
    summary: Dict[str, Any],
    queues: Dict[str, Any],
    data: Dict[str, Any],
) -> None:
    """Render calculated insights, rule-based recommendations, and freshness metadata."""
    render_section_header(
        title="Business Insights & Platform Status",
        subtitle="Deterministic Gold-data calculations separated clearly from operational recommendations and source freshness.",
    )

    left_col, right_col = st.columns([1.2, 1.0])

    latest_markets = queues["latest_markets"]
    property_df = data["property_df"]
    maintenance_df = data["maintenance_df"]

    with left_col:
        with chart_card(
            title="Calculated Insights & Recommended Actions",
            subtitle="Every figure below is computed directly from loaded Unity Catalog Gold tables.",
            badge="Calculated Metrics",
            badge_tone="success",
        ):
            # 1. Financial momentum insight
            rev_delta_txt = (
                f"{summary['rev_delta']:+.1f}% MoM"
                if summary["rev_delta"] is not None
                else "baseline month"
            )
            noi_delta_txt = (
                f"{summary['noi_delta']:+.1f}% MoM"
                if summary["noi_delta"] is not None
                else "baseline month"
            )
            render_insight_card(
                title="Portfolio Profitability & Margin",
                body=(
                    f"In {summary['latest_month']}, rental revenue reached ${summary['latest_revenue']:,.0f} "
                    f"({rev_delta_txt}) and NOI reached ${summary['latest_noi']:,.0f} ({noi_delta_txt}), "
                    f"delivering an operating margin of {summary['noi_margin']:.1f}%."
                ),
                tone="success" if summary["latest_noi"] > 0 else "danger",
                tag="Calculated",
            )

            # 2. Market spread insight
            if not latest_markets.empty:
                top_mkt = latest_markets.loc[latest_markets["total_noi"].idxmax()]
                low_occ_mkt = latest_markets.loc[latest_markets["occupancy_pct"].idxmin()]
                render_insight_card(
                    title="Market Performance Dispersion",
                    body=(
                        f"{top_mkt['market_name']} led regional NOI at ${top_mkt['total_noi']:,.0f} "
                        f"({top_mkt['occupancy_pct']:.2f}% occupancy), whereas {low_occ_mkt['market_name']} "
                        f"recorded the lowest occupancy at {low_occ_mkt['occupancy_pct']:.2f}% "
                        f"with a {low_occ_mkt['expense_ratio_pct']:.1f}% expense ratio."
                    ),
                    tone="info",
                    tag="Calculated",
                )

            # 3. Maintenance concentration insight
            if not maintenance_df.empty and not queues["high_maint_df"].empty:
                top_decile_cost = float(queues["high_maint_df"]["total_maintenance_cost"].sum())
                total_cost = summary["total_maint_cost"] or 1.0
                cost_share = top_decile_cost / total_cost * 100.0
                render_insight_card(
                    title="Maintenance Cost & Backlog Concentration",
                    body=(
                        f"The top {len(queues['high_maint_df'])} maintenance-spend properties represent "
                        f"{cost_share:.1f}% (${top_decile_cost:,.0f}) of total maintenance spend. "
                        f"{summary['active_work_orders']:,} work orders remain open or in progress."
                    ),
                    tone="warning" if summary["active_work_orders"] > 0 else "success",
                    tag="Calculated",
                )

            # 4. Rule-based suggested actions (distinct from Genie AI)
            low_occ_count = len(queues["low_occ_df"])
            if not property_df.empty:
                neg_count = int((property_df["total_noi"] <= 0).sum())
                action_parts = []
                if low_occ_count > 0:
                    action_parts.append(
                        f"Audit leasing and pricing on the {low_occ_count} properties below "
                        f"{LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% occupancy."
                    )
                if neg_count > 0:
                    action_parts.append(
                        f"Conduct margin recovery reviews on {neg_count} properties with non-positive NOI."
                    )
                if not queues["attention_markets_df"].empty:
                    flagged_names = ", ".join(
                        queues["attention_markets_df"]["market_name"].astype(str).tolist()
                    )
                    action_parts.append(
                        f"Prioritize regional operator check-ins for: {flagged_names}."
                    )
                if not action_parts:
                    action_parts.append(
                        "Continue routine monthly leasing and preventive maintenance monitoring; no critical thresholds breached."
                    )

                render_insight_card(
                    title="Recommended Operational Next Steps",
                    body=" ".join(action_parts),
                    tone="neutral",
                    tag="Rule-Based Action",
                )

    with right_col:
        with chart_card(
            title="Data Freshness & Source Registry",
            subtitle="Unity Catalog Gold tables and Delta Lake commit metadata",
            badge="Unity Catalog",
            badge_tone="success",
        ):
            freshness_rows = []
            dataset_labels = [
                ("Portfolio KPIs", data["tables"]["portfolio"], len(data["portfolio_df"])),
                ("Market Monthly", data["tables"]["market"], len(data["market_df"])),
                ("Property Performance", data["tables"]["property"], len(data["property_df"])),
                ("Maintenance Summary", data["tables"]["maintenance"], len(data["maintenance_df"])),
                ("CapEx Summary", data["tables"]["capex"], data["capex_rows"]),
            ]
            for label, table_fqn, row_cnt in dataset_labels:
                meta = data["freshness"].get(table_fqn, {})
                if meta.get("status") == "available":
                    freshness_str = f"v{meta.get('version')} · {meta.get('timestamp')}"
                else:
                    freshness_str = "Live SQL Connected"
                freshness_rows.append(
                    {
                        "Dataset": label,
                        "Table": table_fqn.split(".")[-1],
                        "Rows": f"{row_cnt:,}" if row_cnt is not None else "—",
                        "Freshness": freshness_str,
                    }
                )

            st.dataframe(
                pd.DataFrame(freshness_rows),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"History span: {summary['history_start']} to {summary['latest_month']} "
                f"({summary['history_months']} months) · "
                f"Warehouse: {'Configured' if os.getenv('DATABRICKS_WAREHOUSE_ID') else 'Missing'} · "
                f"Genie: {'Configured' if is_genie_configured() else 'Missing'}"
            )
            st.caption(
                "Note: Pipeline orchestration run logs (`workspace.monitoring` / `workspace.audit`) "
                "will be integrated after schema verification."
            )


def main() -> None:
    """Render the Executive Portfolio AI Studio dashboard."""
    apply_theme()
    render_header("Portfolio")

    try:
        with st.spinner("Loading executive portfolio intelligence from Databricks Gold layer..."):
            data = load_dashboard_data()

        portfolio_df = data["portfolio_df"]
        if portfolio_df.empty:
            render_page_header(
                title="Executive Portfolio Overview",
                description="Residential property intelligence command center.",
                domain_label="Portfolio",
                status_text="No Records",
                status_tone="warning",
            )
            render_empty_state(
                "No Portfolio KPI Records Found",
                f"Table {data['tables']['portfolio']} returned zero rows.",
                tone="warning",
            )
            st.stop()

        summary = compute_portfolio_summary(
            portfolio_df=portfolio_df,
            maintenance_df=data["maintenance_df"],
            capex_totals=data["capex_totals"],
        )

        # Freshness text from primary portfolio table if Delta history is accessible
        primary_freshness = data["freshness"].get(data["tables"]["portfolio"], {})
        if primary_freshness.get("status") == "available":
            freshness_badge = f"Gold Synced · {primary_freshness['timestamp']}"
        else:
            freshness_badge = "Gold Layer Connected"

        render_page_header(
            title="Executive Portfolio Overview",
            description=(
                "AI-assisted residential property command center combining Gold financial KPIs, "
                "market dispersion, operational decision queues, and Databricks Genie."
            ),
            domain_label="Portfolio · AI Studio",
            reporting_period=f"{summary['latest_month']} ({summary['history_months']}M History)",
            status_text=freshness_badge,
            status_tone="success",
        )

        toolbar_left, toolbar_right = st.columns([5.5, 1.0])
        with toolbar_left:
            st.caption(
                f"Connected to `{data['tables']['portfolio']}` and companion Unity Catalog Gold datasets."
            )
        with toolbar_right:
            if st.button("Refresh Data", use_container_width=True):
                load_dashboard_data.clear()
                st.rerun()

        render_genie_bar()

        render_section_header(
            title="Executive Portfolio KPIs",
            subtitle=f"Headline performance metrics as of {summary['latest_month']} with month-over-month comparisons.",
            badge=f"Period: {summary['latest_month']}",
            badge_tone="neutral",
        )
        render_kpi_row(summary["cards"])

        queues = build_decision_queues(
            market_df=data["market_df"],
            property_df=data["property_df"],
            maintenance_df=data["maintenance_df"],
            portfolio_occupancy=summary["occupancy"],
        )

        render_performance_section(
            portfolio_df=portfolio_df,
            latest_markets=queues["latest_markets"],
        )

        render_decision_queue_section(queues)
        render_insights_and_operations(summary=summary, queues=queues, data=data)

        with st.expander("View monthly portfolio data"):
            st.dataframe(
                portfolio_df.sort_values("month_year", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

    except Exception as exc:
        render_page_header(
            title="Executive Portfolio Overview",
            description="Residential property intelligence command center.",
            domain_label="Portfolio",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load portfolio intelligence data from Databricks.")
        st.exception(exc)


if __name__ == "__main__":
    main()

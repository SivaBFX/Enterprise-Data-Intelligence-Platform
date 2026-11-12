"""Executive Portfolio AI Studio dashboard."""

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
    render_genie_response,
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

PERSONA_ROLES = [
    ("Portfolio Exec", "All KPIs & decision queues across 5 markets"),
    ("Market Ops", "Regional NOI, occupancy, and OpEx dispersion"),
    ("Asset Manager", "Property-level occupancy & negative NOI watchlist"),
    ("Maint & CapEx", "Work-order backlogs, SLAs, and CapEx alignment"),
]

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
    ordered = (
        ordered.sort_values("_sort_key")
        .drop(columns=["_sort_key"])
        .reset_index(drop=True)
    )
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

    capex_amt = float(capex_totals.get("total_capex_amount", 0.0))
    capex_cnt = int(capex_totals.get("investment_count", 0))

    cards = [
        {
            "label": "Total Properties",
            "value": f"{total_properties:,}",
            "delta": f"{prop_delta:+d} MoM" if prev is not None and prop_delta != 0 else "Gold · Live",
            "delta_tone": "success" if prop_delta >= 0 else "warning",
            "caption": f"Active residential assets ({latest['month_year']})",
            "source_table": "gold_portfolio_kpis",
        },
        {
            "label": "Weighted Occupancy",
            "value": f"{occupancy:.2f}%",
            "delta": f"{occ_delta:+.2f} pp MoM" if occ_delta is not None else "Latest Month",
            "delta_tone": "success" if (occ_delta is None or occ_delta >= 0) else "warning",
            "caption": f"{int(latest['total_occupied_days']):,} / {int(latest['total_service_days']):,} service days",
            "source_table": "gold_portfolio_kpis",
        },
        {
            "label": "Rental Revenue",
            "value": f"${latest_revenue:,.0f}",
            "delta": f"{rev_delta:+.1f}% MoM" if rev_delta is not None else "Latest Month",
            "delta_tone": "success" if (rev_delta is None or rev_delta >= 0) else "warning",
            "caption": f"12M cumulative: ${cum_revenue:,.0f}",
            "source_table": "gold_portfolio_kpis",
        },
        {
            "label": "Net Operating Income",
            "value": f"${latest_noi:,.0f}",
            "delta": f"{noi_delta:+.1f}% MoM" if noi_delta is not None else "Latest Month",
            "delta_tone": "success" if (noi_delta is None or noi_delta >= 0) else "danger",
            "caption": f"Operating margin: {noi_margin:.1f}%",
            "source_table": "gold_portfolio_kpis",
        },
        {
            "label": "Maintenance Cost",
            "value": f"${total_maint_cost:,.0f}",
            "delta": f"{active_work_orders:,} active WOs",
            "delta_tone": "warning" if active_work_orders > 0 else "success",
            "caption": f"{total_work_orders:,} total work orders",
            "source_table": "gold_maintenance_summary",
        },
        {
            "label": "CapEx Investment",
            "value": f"${capex_amt:,.0f}",
            "delta": f"{capex_cnt:,} investments",
            "delta_tone": "info",
            "caption": (
                f"Avg ${capex_amt / capex_cnt:,.0f} / project"
                if capex_cnt > 0
                else "Capital improvement spend"
            ),
            "source_table": "gold_capex_summary",
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


def _build_decision_items(
    summary: Dict[str, Any],
    queues: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Construct interactive AI Studio decision cards from real Gold queue counts."""
    items: List[Dict[str, Any]] = []

    low_occ = queues["low_occ_df"]
    if not low_occ.empty:
        top_mkt = str(low_occ["market_name"].mode().iloc[0])
        items.append(
            {
                "id": "low_occ",
                "title": f"Review {len(low_occ)} properties below {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% occupancy",
                "short_sub": f"Highest concentration in {top_mkt}",
                "owner": "Asset Manager · Leasing Ops",
                "badge_1": "Gold Triggered",
                "badge_2": "Needs Review",
                "tone": "warning",
                "summary": (
                    f"{len(low_occ)} residential properties are operating below the {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% "
                    f"occupancy threshold, led by {low_occ.iloc[0]['property_id']} "
                    f"({low_occ.iloc[0]['overall_occupancy_pct']:.1f}% in {low_occ.iloc[0]['market_name']})."
                ),
                "impact": f"{len(low_occ)} assets impacted",
                "threshold": f"< {LOW_OCCUPANCY_THRESHOLD_PCT:.0f}% occupancy",
                "guardrail": "Prioritize rent concessions & renewal outreach",
                "genie_prompt": "Which properties have occupancy below 85% and what is their NOI?",
                "page_path": "pages/03_Property_Analytics.py",
                "page_label": "Inspect in Properties",
                "df": low_occ[
                    ["property_id", "market_name", "property_type", "overall_occupancy_pct", "total_noi"]
                ],
            }
        )

    low_noi = queues["low_noi_df"]
    if not low_noi.empty:
        is_neg = queues["noi_mode"] == "negative"
        items.append(
            {
                "id": "low_noi",
                "title": (
                    f"Audit {len(low_noi)} properties with non-positive NOI"
                    if is_neg
                    else "Review bottom-10 lowest-NOI properties"
                ),
                "short_sub": (
                    f"Lowest asset: {low_noi.iloc[0]['property_id']} (${low_noi.iloc[0]['total_noi']:,.0f})"
                ),
                "owner": "Portfolio Exec · Finance",
                "badge_1": "Gold Triggered" if is_neg else "Watchlist",
                "badge_2": "Margin Action" if is_neg else "Within Policy",
                "tone": "danger" if is_neg else "info",
                "summary": (
                    f"{len(low_noi)} properties have cumulative NOI <= $0, dragging portfolio margin "
                    f"({summary['noi_margin']:.1f}%)."
                    if is_neg
                    else f"No properties have negative total NOI; reviewing the 10 lowest-NOI properties starting at ${low_noi.iloc[0]['total_noi']:,.0f}."
                ),
                "impact": f"${low_noi['total_noi'].sum():,.0f} combined NOI",
                "threshold": "NOI <= $0" if is_neg else "Bottom 10 NOI",
                "guardrail": "Expense & rent-roll variance audit",
                "genie_prompt": "Which 10 properties have the lowest NOI and highest expense ratio?",
                "page_path": "pages/03_Property_Analytics.py",
                "page_label": "Open Property Watchlist",
                "df": low_noi[
                    ["property_id", "market_name", "overall_occupancy_pct", "total_rental_revenue", "total_noi"]
                ],
            }
        )

    high_maint = queues["high_maint_df"]
    if not high_maint.empty:
        top_prop = high_maint.iloc[0]
        items.append(
            {
                "id": "high_maint",
                "title": f"Triage {len(high_maint)} top-decile maintenance cost properties",
                "short_sub": f"{summary['active_work_orders']:,} active work orders open/in progress",
                "owner": "Maint & CapEx · Field Ops",
                "badge_1": "Gold Triggered",
                "badge_2": "Cost & Backlog",
                "tone": "warning",
                "summary": (
                    f"Top-decile properties (>= ${queues['maint_threshold']:,.0f}) represent "
                    f"${high_maint['total_maintenance_cost'].sum():,.0f} in maintenance spend. "
                    f"{top_prop['property_id']} ({top_prop['market_name']}) leads at ${top_prop['total_maintenance_cost']:,.0f}."
                ),
                "impact": f"${high_maint['total_maintenance_cost'].sum():,.0f} spend",
                "threshold": f">= ${queues['maint_threshold']:,.0f} (P90)",
                "guardrail": "Evaluate preventive CapEx vs. repeat repairs",
                "genie_prompt": "Which properties have the highest maintenance costs and open work orders?",
                "page_path": "pages/04_Maintenance.py",
                "page_label": "Open Maintenance Queue",
                "df": high_maint[
                    ["property_id", "market_name", "total_maintenance_cost", "open_work_orders", "in_progress_work_orders"]
                ],
            }
        )

    att_mkts = queues["attention_markets_df"]
    if not att_mkts.empty:
        names = ", ".join(att_mkts["market_name"].astype(str).tolist())
        items.append(
            {
                "id": "att_markets",
                "title": f"Benchmark {len(att_mkts)} markets trailing portfolio targets",
                "short_sub": names,
                "owner": "Market Ops · Regional Leads",
                "badge_1": "Gold Triggered",
                "badge_2": "Market Watch",
                "tone": "info",
                "summary": (
                    f"{names} trailed portfolio occupancy ({summary['occupancy']:.2f}%) or exceeded "
                    f"average operating expense ratio in {summary['latest_month']}."
                ),
                "impact": f"{int(att_mkts['property_count'].sum()):,} market properties",
                "threshold": "Below avg occ / above avg OpEx",
                "guardrail": "Regional operator check-in",
                "genie_prompt": "Compare all markets by NOI, occupancy, and operating expense ratio.",
                "page_path": "pages/02_Market_Analytics.py",
                "page_label": "Open Market Analytics",
                "df": att_mkts[
                    ["market_name", "region", "property_count", "occupancy_pct", "total_noi", "expense_ratio_pct"]
                ],
            }
        )

    return items


def _render_hero_and_personas(decision_count: int, summary: Dict[str, Any]) -> str:
    """Render AI Studio hero headline on the left and role focus pills on the right."""
    st.session_state.setdefault("ai_active_persona", "Portfolio Exec")
    active_role = st.session_state["ai_active_persona"]

    left_col, right_col = st.columns([1.22, 1.28])
    with left_col:
        headline = (
            f"{decision_count} decision{'s' if decision_count != 1 else ''} need you today"
            if decision_count > 0
            else "All portfolio metrics within baseline"
        )
        period_badge_text = (
            f"Gold Layer · {summary['latest_month']} · {summary['history_months']}M"
        )
        pill_html = (
            '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">'
            '<span style="font-size:0.72rem;font-weight:750;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#0c6b53;">PORTFOLIO · EXECUTIVE</span>'
            f'{status_badge_html(period_badge_text, tone="neutral")}'
            "</div>"
        )
        st.markdown(pill_html, unsafe_allow_html=True)
        st.markdown(
            f'<h1 style="font-size:1.85rem;font-weight:750;color:#111827;'
            f'letter-spacing:-0.03em;margin:0 0 4px 0;line-height:1.15;">{headline}</h1>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Monitor NOI margins ({summary['noi_margin']:.1f}%), weighted occupancy ({summary['occupancy']:.2f}%), "
            f"and operational exceptions across 5 residential markets."
        )

    with right_col:
        st.caption("View as · focus perspectives mapped to Portfolio")
        p_cols = st.columns([1.15, 0.96, 1.15, 1.14])
        for col, (role_name, _) in zip(p_cols, PERSONA_ROLES):
            with col:
                is_selected = active_role == role_name
                if st.button(
                    role_name,
                    key=f"persona_btn_{role_name}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["ai_active_persona"] = role_name
                    st.rerun()

    return active_role


def render_genie_bar() -> None:
    """Render the sleek AI Studio Genie search bar and response box."""
    st.session_state.setdefault("genie_question_input", "")
    st.session_state.setdefault("genie_last_response", None)
    st.session_state.setdefault("genie_conversation_id", None)
    st.session_state.setdefault("genie_home_pending", None)

    triggered_question: Optional[str] = st.session_state.pop("genie_home_pending", None)

    with st.container(border=True):
        input_col, ask_col, clear_col, full_col = st.columns([4.7, 1.15, 0.95, 1.25])
        with input_col:
            question_text = st.text_input(
                "Ask a business question",
                key="genie_question_input",
                placeholder='Ask about Portfolio, e.g. "Which market delivered the highest NOI margin?"',
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
        with full_col:
            st.page_link(
                "pages/08_Genie_Assistant.py",
                label="Full Genie Chat",
            )

        s_cols = st.columns(len(SUGGESTED_QUESTIONS))
        for idx, (col, suggestion) in enumerate(zip(s_cols, SUGGESTED_QUESTIONS)):
            with col:
                if st.button(
                    suggestion, key=f"genie_suggest_{idx}", use_container_width=True
                ):
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
        if last_resp is not None:
            st.divider()
            clicked_followup = render_genie_response(
                last_resp,
                key_prefix="home_genie",
                show_followups=True,
            )
            if clicked_followup:
                st.session_state["genie_home_pending"] = clicked_followup
                st.rerun()


def _render_decision_orchestration_center(
    summary: Dict[str, Any],
    queues: Dict[str, Any],
    data: Dict[str, Any],
) -> None:
    """Render Screenshot-1 style 3-column Decision Queue, Detail Card, and Orchestration."""
    decisions = _build_decision_items(summary=summary, queues=queues)
    st.session_state.setdefault("selected_decision_idx", 0)
    if decisions and st.session_state["selected_decision_idx"] >= len(decisions):
        st.session_state["selected_decision_idx"] = 0

    col_queue, col_detail, col_orch = st.columns([1.05, 1.85, 1.0])

    with col_queue:
        st.markdown(
            '<div class="ai-micro-label" style="margin-bottom:8px;">DECISION QUEUE</div>',
            unsafe_allow_html=True,
        )
        if not decisions:
            render_empty_state(
                "Queue Clear",
                "No portfolio or market thresholds breached.",
                tone="success",
            )
        else:
            for idx, item in enumerate(decisions):
                is_active = st.session_state["selected_decision_idx"] == idx
                with st.container(border=True):
                    badges_html = (
                        f"{status_badge_html(item['badge_1'], tone='neutral')} "
                        f"{status_badge_html(item['badge_2'], tone=item['tone'])}"
                    )
                    st.markdown(
                        f'<div style="font-size:0.86rem;font-weight:700;color:#111827;'
                        f'line-height:1.3;margin-bottom:3px;">{html.escape(item["title"])}</div>'
                        f'<div style="font-size:0.76rem;color:#6b7280;margin-bottom:6px;">'
                        f'{html.escape(item["short_sub"])}</div>'
                        f'<div style="margin-bottom:6px;">{badges_html}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Inspecting" if is_active else "Open Decision",
                        key=f"decision_select_{idx}",
                        type="primary" if is_active else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["selected_decision_idx"] = idx
                        st.rerun()

    with col_detail:
        st.markdown(
            '<div class="ai-micro-label" style="margin-bottom:8px;">DECISION BRIEF</div>',
            unsafe_allow_html=True,
        )
        if decisions:
            active_item = decisions[st.session_state["selected_decision_idx"]]
            with st.container(border=True):
                st.caption(f"Computed from Unity Catalog Gold · Owner: {active_item['owner']}")
                st.markdown(
                    f'<h3 style="margin:2px 0 6px 0;font-size:1.22rem;color:#111827;">'
                    f'{html.escape(active_item["title"])}</h3>',
                    unsafe_allow_html=True,
                )
                st.markdown(active_item["summary"])

                t1, t2, t3 = st.columns(3)
                with t1:
                    st.markdown(
                        f'<div class="ai-stat-tile">'
                        f'<div class="ai-stat-tile-label">Calculated Impact</div>'
                        f'<div class="ai-stat-tile-value">{html.escape(active_item["impact"])}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with t2:
                    st.markdown(
                        f'<div class="ai-stat-tile tone-success">'
                        f'<div class="ai-stat-tile-label">Gold Threshold</div>'
                        f'<div class="ai-stat-tile-value">{html.escape(active_item["threshold"])}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with t3:
                    st.markdown(
                        f'<div class="ai-stat-tile tone-warning">'
                        f'<div class="ai-stat-tile-label">Policy Guardrail</div>'
                        f'<div class="ai-stat-tile-value">{html.escape(active_item["guardrail"])}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                b1, b2 = st.columns([1.2, 1.2])
                with b1:
                    if st.button(
                        "Ask Genie for Brief",
                        key="decision_ask_genie",
                        type="primary",
                        use_container_width=True,
                    ):
                        st.session_state["genie_home_pending"] = active_item["genie_prompt"]
                        st.rerun()
                with b2:
                    st.page_link(
                        active_item["page_path"],
                        label=active_item["page_label"],
                    )

                with st.expander(f"View Supporting Gold Records ({len(active_item['df'])})"):
                    st.dataframe(
                        active_item["df"],
                        use_container_width=True,
                        hide_index=True,
                    )

    with col_orch:
        h_left, h_right = st.columns([1.6, 1.0])
        with h_left:
            st.markdown(
                '<div class="ai-micro-label" style="margin-bottom:8px;">YOUR ORCHESTRATION</div>',
                unsafe_allow_html=True,
            )
        with h_right:
            st.page_link("pages/06_Data_Products.py", label="See all")

        primary_freshness = data["freshness"].get(data["tables"]["portfolio"], {})
        sync_label = (
            f"v{primary_freshness.get('version')}"
            if primary_freshness.get("status") == "available"
            else f"{summary['history_months']}M Live"
        )

        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                f'<strong style="font-size:0.86rem;color:#111827;">Gold Layer Sync</strong>'
                f'{status_badge_html(sync_label, tone="success")}'
                f"</div>"
                f'<div style="font-size:0.77rem;color:#6b7280;margin:4px 0 6px 0;">'
                f'Latest period {summary["latest_month"]} across 6 Unity Catalog tables</div>'
                f'<div style="font-size:0.72rem;color:#0c6b53;font-weight:600;">SQL Warehouse · Connected</div>',
                unsafe_allow_html=True,
            )

        with st.container(border=True):
            genie_badge = "Ready" if is_genie_configured() else "Check Env"
            genie_tone = "info" if is_genie_configured() else "warning"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                f'<strong style="font-size:0.86rem;color:#111827;">Genie & Specialist Agents</strong>'
                f'{status_badge_html(genie_badge, tone=genie_tone)}'
                f"</div>"
                f'<div style="font-size:0.77rem;color:#6b7280;margin:4px 0 6px 0;">'
                f'Natural-language Q&A + 4 traceable Gold analysts</div>',
                unsafe_allow_html=True,
            )
            st.page_link("pages/07_Agents.py", label="Open Specialist Agents")

        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                f'<strong style="font-size:0.86rem;color:#111827;">Data Products Catalog</strong>'
                f'{status_badge_html("6 Products", tone="neutral")}'
                f"</div>"
                f'<div style="font-size:0.77rem;color:#6b7280;margin:4px 0 6px 0;">'
                f'Schemas, row counts, completeness checks, and KPI glossary</div>',
                unsafe_allow_html=True,
            )
            st.page_link("pages/06_Data_Products.py", label="Inspect Data Products")


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


def render_insights_and_operations(
    summary: Dict[str, Any],
    queues: Dict[str, Any],
    data: Dict[str, Any],
) -> None:
    """Render calculated insights, rule-based actions, and freshness metadata."""
    render_section_header(
        title="Calculated Insights & Source Freshness",
        subtitle="Deterministic Gold-data calculations paired with live Unity Catalog freshness.",
    )

    left_col, right_col = st.columns([1.2, 1.0])
    latest_markets = queues["latest_markets"]
    maintenance_df = data["maintenance_df"]

    with left_col:
        with chart_card(
            title="Portfolio Takeaways",
            subtitle="Computed directly from loaded Unity Catalog Gold tables",
            badge="Calculated Metrics",
            badge_tone="success",
        ):
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

            if not latest_markets.empty:
                top_mkt = latest_markets.loc[latest_markets["total_noi"].idxmax()]
                low_occ_mkt = latest_markets.loc[latest_markets["occupancy_pct"].idxmin()]
                render_insight_card(
                    title="Market Performance Dispersion",
                    body=(
                        f"{top_mkt['market_name']} led regional NOI at ${top_mkt['total_noi']:,.0f} "
                        f"({top_mkt['occupancy_pct']:.2f}% occupancy), whereas {low_occ_mkt['market_name']} "
                        f"recorded the lowest occupancy at {low_occ_mkt['occupancy_pct']:.2f}%."
                    ),
                    tone="info",
                    tag="Calculated",
                )

            if not maintenance_df.empty and not queues["high_maint_df"].empty:
                top_decile_cost = float(queues["high_maint_df"]["total_maintenance_cost"].sum())
                total_cost = summary["total_maint_cost"] or 1.0
                cost_share = top_decile_cost / total_cost * 100.0
                render_insight_card(
                    title="Maintenance Cost & Backlog Concentration",
                    body=(
                        f"The top {len(queues['high_maint_df'])} maintenance-spend properties represent "
                        f"{cost_share:.1f}% (${top_decile_cost:,.0f}) of maintenance spend with "
                        f"{summary['active_work_orders']:,} active work orders."
                    ),
                    tone="warning" if summary["active_work_orders"] > 0 else "success",
                    tag="Calculated",
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
                freshness_str = (
                    f"v{meta.get('version')} · {meta.get('timestamp')}"
                    if meta.get("status") == "available"
                    else "Live SQL Connected"
                )
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

            if st.button("Refresh Gold Data", use_container_width=True):
                load_dashboard_data.clear()
                st.rerun()


def main() -> None:
    """Render the Executive Portfolio AI Studio dashboard."""
    apply_theme()
    render_header(active_page="Portfolio", active_section="Today")

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
        queues = build_decision_queues(
            market_df=data["market_df"],
            property_df=data["property_df"],
            maintenance_df=data["maintenance_df"],
            portfolio_occupancy=summary["occupancy"],
        )
        decisions = _build_decision_items(summary=summary, queues=queues)

        active_role = _render_hero_and_personas(
            decision_count=len(decisions), summary=summary
        )

        render_genie_bar()

        # YOUR METRICS header strip matching AI Studio layout
        m_left, m_right = st.columns([1.2, 2.0])
        with m_left:
            st.markdown(
                '<div class="ai-micro-label" style="margin:0.45rem 0 0.4rem 0;">YOUR METRICS</div>',
                unsafe_allow_html=True,
            )
        with m_right:
            st.markdown(
                f'<div style="text-align:right;font-size:0.76rem;color:#6b7280;margin:0.45rem 0 0.4rem 0;">'
                f'Mapped to {active_role} from Gold views · {summary["latest_month"]}</div>',
                unsafe_allow_html=True,
            )

        render_kpi_row(summary["cards"])

        _render_decision_orchestration_center(summary=summary, queues=queues, data=data)

        render_performance_section(
            portfolio_df=portfolio_df,
            latest_markets=queues["latest_markets"],
        )

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

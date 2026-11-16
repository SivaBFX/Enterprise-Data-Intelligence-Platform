"""Specialist Gold-data analysts and business decision support agents (Milestone 8)."""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import pandas as pd

from utils.database import coerce_numeric, query_table, resolve_table_name


@dataclass(frozen=True)
class AgentSpec:
    """Metadata and governance profile for a specialist decision-support agent."""

    key: str
    name: str
    icon: str
    role: str
    implementation_label: str
    approved_tables: List[str]
    capabilities: List[str]
    sample_questions: List[str]


@dataclass
class AgentResult:
    """Traceable analytical output from a specialist agent run."""

    agent_name: str
    question: str
    implementation_mode: str
    summary: str
    findings: List[str] = field(default_factory=list)
    evidence_df: Optional[pd.DataFrame] = None
    trace_sql: str = ""
    source_tables: List[str] = field(default_factory=list)
    recommended_action: str = ""
    simulated_preview: Optional[str] = None


AGENT_SPECS: List[AgentSpec] = [
    AgentSpec(
        key="portfolio",
        name="Portfolio Performance Analyst",
        icon=":material/query_stats:",
        role="Evaluates revenue momentum, NOI margins, occupancy health, and asset-level outliers.",
        implementation_label="Implemented · Gold Data + Optional Genie",
        approved_tables=[
            "workspace.gold.gold_portfolio_kpis",
            "workspace.gold.gold_property_performance",
        ],
        capabilities=[
            "Monthly revenue and NOI margin trajectory",
            "Portfolio weighted occupancy & MoM variance",
            "Low-occupancy (<85%) and non-positive NOI flagging",
        ],
        sample_questions=[
            "What is the latest portfolio NOI margin and MoM trajectory?",
            "Which properties pose the largest occupancy or negative NOI risk?",
            "Summarize 12-month revenue and occupancy performance.",
        ],
    ),
    AgentSpec(
        key="market",
        name="Market Intelligence Assistant",
        icon=":material/public:",
        role="Benchmarks regional markets on NOI, occupancy dispersion, and operating expense efficiency.",
        implementation_label="Implemented · Gold Data + Optional Genie",
        approved_tables=["workspace.gold.gold_market_monthly"],
        capabilities=[
            "Latest-month cross-market NOI ranking",
            "Operating expense ratio benchmarking",
            "Market occupancy gap identification",
        ],
        sample_questions=[
            "Which markets lead and lag in NOI and occupancy?",
            "Which markets have the highest operating expense ratios?",
            "Compare unit NOI per property across regional markets.",
        ],
    ),
    AgentSpec(
        key="maintenance",
        name="Maintenance Analyst",
        icon=":material/build:",
        role="Identifies high-cost assets, active work-order backlogs, and completion SLA bottlenecks.",
        implementation_label="Implemented · Gold Data + Optional Genie",
        approved_tables=["workspace.gold.gold_maintenance_summary"],
        capabilities=[
            "Top-decile maintenance cost concentration",
            "Open and in-progress backlog triage",
            "Weighted completion-time SLA benchmarking",
        ],
        sample_questions=[
            "Which properties drive the highest maintenance costs?",
            "Where is active open/in-progress work-order backlog concentrated?",
            "Which markets have the slowest work-order completion times?",
        ],
    ),
    AgentSpec(
        key="capex",
        name="CapEx Analyst",
        icon=":material/account_balance:",
        role="Tracks capital investment allocation across markets, categories, and high-intensity properties.",
        implementation_label="Implemented · Gold Data + Optional Genie",
        approved_tables=["workspace.gold.gold_capex_summary"],
        capabilities=[
            "Total and average CapEx investment sizing",
            "Category and regional capital concentration",
            "Top capital-intensive properties review",
        ],
        sample_questions=[
            "Which categories and markets account for the most CapEx spend?",
            "Which properties received the largest capital investments?",
            "What is the average investment size across categories?",
        ],
    ),
]

AGENT_SPEC_MAP: Dict[str, AgentSpec] = {spec.key: spec for spec in AGENT_SPECS}


def _run_portfolio_analyst(question: str) -> AgentResult:
    """Analyze portfolio KPIs and property risk from approved Gold tables."""
    kpi_table = resolve_table_name(
        "PORTFOLIO_KPIS_TABLE", "workspace.gold.gold_portfolio_kpis"
    )
    prop_table = resolve_table_name(
        "PROPERTY_PERFORMANCE_TABLE", "workspace.gold.gold_property_performance"
    )

    kpi_df = query_table(kpi_table, limit=100)
    prop_df = query_table(prop_table, limit=1000)

    if kpi_df.empty:
        return AgentResult(
            agent_name="Portfolio Performance Analyst",
            question=question,
            implementation_mode="Implemented · Deterministic Gold Data",
            summary="No portfolio KPI records were returned from Unity Catalog.",
            source_tables=[kpi_table],
        )

    kpi_df = coerce_numeric(
        kpi_df,
        [
            "total_properties",
            "total_occupied_days",
            "total_service_days",
            "total_rental_revenue",
            "total_noi",
        ],
    )
    parsed_dates = pd.to_datetime(kpi_df["month_year"], errors="coerce")
    kpi_df["_sort"] = parsed_dates if parsed_dates.notna().all() else kpi_df["month_year"].astype(str)
    kpi_df = kpi_df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)
    kpi_df["occupancy_pct"] = (
        kpi_df["total_occupied_days"]
        / kpi_df["total_service_days"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    kpi_df["noi_margin_pct"] = (
        kpi_df["total_noi"]
        / kpi_df["total_rental_revenue"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)

    latest = kpi_df.iloc[-1]
    prev = kpi_df.iloc[-2] if len(kpi_df) >= 2 else None
    noi_change_txt = ""
    if prev is not None and float(prev["total_noi"]):
        noi_pct = (
            (float(latest["total_noi"]) - float(prev["total_noi"]))
            / abs(float(prev["total_noi"]))
            * 100.0
        )
        noi_change_txt = f" ({noi_pct:+.1f}% MoM)"

    findings = [
        f"Latest month ({latest['month_year']}): {int(latest['total_properties']):,} properties, "
        f"{latest['occupancy_pct']:.2f}% weighted occupancy, ${latest['total_rental_revenue']:,.0f} revenue, "
        f"and ${latest['total_noi']:,.0f} NOI{noi_change_txt} ({latest['noi_margin_pct']:.1f}% margin).",
        f"Cumulative rental revenue across {len(kpi_df)} months totals "
        f"${kpi_df['total_rental_revenue'].sum():,.0f} with cumulative NOI of "
        f"${kpi_df['total_noi'].sum():,.0f}.",
    ]

    q_lower = question.lower()
    risk_focused = any(
        w in q_lower for w in ["risk", "low", "negative", "underperform", "propert"]
    )

    if risk_focused and not prop_df.empty:
        prop_df = coerce_numeric(
            prop_df,
            [
                "overall_occupancy_pct",
                "total_rental_revenue",
                "total_noi",
                "operating_expense_ratio_pct",
            ],
        )
        flagged = prop_df[
            (prop_df["overall_occupancy_pct"] < 85.0) | (prop_df["total_noi"] <= 0)
        ].sort_values("total_noi", ascending=True)
        low_occ_cnt = int((prop_df["overall_occupancy_pct"] < 85.0).sum())
        neg_noi_cnt = int((prop_df["total_noi"] <= 0).sum())
        findings.append(
            f"Asset risk scan: {low_occ_cnt} properties fall below 85.0% occupancy and "
            f"{neg_noi_cnt} properties report non-positive total NOI."
        )
        evidence_df = (flagged if not flagged.empty else prop_df.nsmallest(10, "total_noi"))[
            [
                "property_id",
                "market_name",
                "property_type",
                "overall_occupancy_pct",
                "total_rental_revenue",
                "total_noi",
                "operating_expense_ratio_pct",
            ]
        ].head(15)
        trace_sql = (
            "SELECT property_id, market_name, property_type, overall_occupancy_pct,\n"
            "       total_rental_revenue, total_noi, operating_expense_ratio_pct\n"
            f"FROM {prop_table}\n"
            "WHERE overall_occupancy_pct < 85.0 OR total_noi <= 0\n"
            "ORDER BY total_noi ASC LIMIT 15;"
        )
        rec = "Prioritize leasing incentives and OpEx audits on the flagged properties above."
    else:
        evidence_df = kpi_df[
            [
                "month_year",
                "total_properties",
                "occupancy_pct",
                "total_rental_revenue",
                "total_noi",
                "noi_margin_pct",
            ]
        ].sort_values("month_year", ascending=False)
        trace_sql = (
            "SELECT month_year, total_properties,\n"
            "       (total_occupied_days / NULLIF(total_service_days, 0)) * 100 AS occupancy_pct,\n"
            "       total_rental_revenue, total_noi,\n"
            "       (total_noi / NULLIF(total_rental_revenue, 0)) * 100 AS noi_margin_pct\n"
            f"FROM {kpi_table}\n"
            "ORDER BY month_year DESC;"
        )
        rec = "Monitor MoM NOI margin and inspect markets showing occupancy compression."

    return AgentResult(
        agent_name="Portfolio Performance Analyst",
        question=question,
        implementation_mode="Implemented · Deterministic Gold Data",
        summary=(
            f"Evaluated {len(kpi_df)} reporting months from `{kpi_table}` and "
            f"{len(prop_df)} property records from `{prop_table}`."
        ),
        findings=findings,
        evidence_df=evidence_df,
        trace_sql=trace_sql,
        source_tables=[kpi_table, prop_table],
        recommended_action=rec,
        simulated_preview=(
            f"[SIMULATED DEMO ONLY] Executive Brief Draft: Portfolio NOI stands at "
            f"${latest['total_noi']:,.0f} ({latest['noi_margin_pct']:.1f}% margin) for "
            f"{latest['month_year']}. No external email or workflow ticket was sent."
        ),
    )


def _run_market_assistant(question: str) -> AgentResult:
    """Analyze market rankings, occupancy, and expense ratios from Gold market data."""
    market_table = resolve_table_name(
        "MARKET_MONTHLY_TABLE", "workspace.gold.gold_market_monthly"
    )
    df = query_table(market_table, limit=1000)
    if df.empty:
        return AgentResult(
            agent_name="Market Intelligence Assistant",
            question=question,
            implementation_mode="Implemented · Deterministic Gold Data",
            summary="No market records were returned from Unity Catalog.",
            source_tables=[market_table],
        )

    df = coerce_numeric(
        df,
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
    df["month"] = pd.to_datetime(df["month"], errors="coerce")
    df = df.dropna(subset=["month"])
    latest_month = df["month"].max()
    latest = df[df["month"] == latest_month].copy()

    latest["occupancy_pct"] = (
        latest["total_occupied_days"]
        / latest["total_service_days"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    latest["expense_ratio_pct"] = (
        latest["total_opex"]
        / latest["net_operating_revenue"].replace(0, pd.NA)
        * 100.0
    ).fillna(0.0)
    latest["noi_per_property"] = (
        latest["total_noi"] / latest["property_count"].replace(0, pd.NA)
    ).fillna(0.0)

    sort_col = (
        "expense_ratio_pct"
        if any(w in question.lower() for w in ["expense", "opex", "cost"])
        else "total_noi"
    )
    ranked = latest.sort_values(sort_col, ascending=(sort_col == "expense_ratio_pct"))

    top_noi = latest.loc[latest["total_noi"].idxmax()]
    low_occ = latest.loc[latest["occupancy_pct"].idxmin()]
    high_exp = latest.loc[latest["expense_ratio_pct"].idxmax()]

    period_str = pd.Timestamp(latest_month).strftime("%B %Y")
    findings = [
        f"Top NOI market in {period_str}: {top_noi['market_name']} at ${top_noi['total_noi']:,.0f} "
        f"(${top_noi['noi_per_property']:,.0f}/property, {top_noi['occupancy_pct']:.2f}% occupancy).",
        f"Lowest occupancy market: {low_occ['market_name']} at {low_occ['occupancy_pct']:.2f}%.",
        f"Highest operating expense ratio: {high_exp['market_name']} at {high_exp['expense_ratio_pct']:.2f}% "
        f"(${high_exp['total_opex']:,.0f} OpEx).",
    ]

    evidence_df = ranked[
        [
            "market_name",
            "region",
            "property_count",
            "occupancy_pct",
            "total_rental_revenue",
            "total_opex",
            "total_noi",
            "expense_ratio_pct",
            "noi_per_property",
        ]
    ]
    trace_sql = (
        "SELECT market_name, region, property_count,\n"
        "       (total_occupied_days / NULLIF(total_service_days, 0)) * 100 AS occupancy_pct,\n"
        "       total_rental_revenue, total_opex, total_noi,\n"
        "       (total_opex / NULLIF(net_operating_revenue, 0)) * 100 AS expense_ratio_pct\n"
        f"FROM {market_table}\n"
        f"WHERE month = (SELECT MAX(month) FROM {market_table})\n"
        f"ORDER BY {sort_col} {'ASC' if sort_col == 'expense_ratio_pct' else 'DESC'};"
    )

    return AgentResult(
        agent_name="Market Intelligence Assistant",
        question=question,
        implementation_mode="Implemented · Deterministic Gold Data",
        summary=f"Evaluated {len(latest)} regional markets for {period_str} from `{market_table}`.",
        findings=findings,
        evidence_df=evidence_df,
        trace_sql=trace_sql,
        source_tables=[market_table],
        recommended_action=(
            f"Review vendor/OpEx contracts in {high_exp['market_name']} "
            f"and leasing conversion in {low_occ['market_name']}."
        ),
        simulated_preview=(
            f"[SIMULATED DEMO ONLY] Regional Ops Memo Preview for {high_exp['market_name']}: "
            f"Expense ratio at {high_exp['expense_ratio_pct']:.1f}%. No message dispatched."
        ),
    )


def _run_maintenance_analyst(question: str) -> AgentResult:
    """Analyze work-order backlog, cost concentration, and completion SLAs."""
    maint_table = resolve_table_name(
        "MAINTENANCE_TABLE", "workspace.gold.gold_maintenance_summary"
    )
    df = query_table(maint_table, limit=1000)
    if df.empty:
        return AgentResult(
            agent_name="Maintenance Analyst",
            question=question,
            implementation_mode="Implemented · Deterministic Gold Data",
            summary="No maintenance summary records were returned.",
            source_tables=[maint_table],
        )

    df = coerce_numeric(
        df,
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
    df["active_backlog"] = df["open_work_orders"] + df["in_progress_work_orders"]

    total_cost = float(df["total_maintenance_cost"].sum())
    total_orders = int(df["total_work_orders"].sum())
    active_backlog = int(df["active_backlog"].sum())
    completed_sum = float(df["completed_work_orders"].sum())
    weighted_days = (
        float((df["avg_completion_days"] * df["completed_work_orders"]).sum()) / completed_sum
        if completed_sum > 0
        else 0.0
    )

    q_lower = question.lower()
    if any(w in q_lower for w in ["backlog", "open", "progress"]):
        evidence_df = df.sort_values(
            ["active_backlog", "total_maintenance_cost"], ascending=[False, False]
        ).head(15)
        order_clause = "(open_work_orders + in_progress_work_orders) DESC"
    elif any(w in q_lower for w in ["slow", "time", "day", "sla", "completion"]):
        evidence_df = (
            df[df["completed_work_orders"] > 0]
            .sort_values("avg_completion_days", ascending=False)
            .head(15)
        )
        order_clause = "avg_completion_days DESC"
    else:
        evidence_df = df.sort_values("total_maintenance_cost", ascending=False).head(15)
        order_clause = "total_maintenance_cost DESC"

    top_prop = df.loc[df["total_maintenance_cost"].idxmax()]
    findings = [
        f"Portfolio maintenance totals ${total_cost:,.0f} across {total_orders:,} work orders "
        f"({active_backlog:,} open or in progress).",
        f"Weighted average completion time is {weighted_days:.1f} days across completed orders.",
        f"Highest-spend property is {top_prop['property_id']} ({top_prop['market_name']}) "
        f"at ${top_prop['total_maintenance_cost']:,.0f} ({int(top_prop['active_backlog'])} active WOs).",
    ]

    cols = [
        "property_id",
        "market_name",
        "region",
        "total_work_orders",
        "open_work_orders",
        "in_progress_work_orders",
        "completed_work_orders",
        "total_maintenance_cost",
        "avg_completion_days",
    ]
    trace_sql = (
        f"SELECT {', '.join(cols)}\n"
        f"FROM {maint_table}\n"
        f"ORDER BY {order_clause} LIMIT 15;"
    )

    return AgentResult(
        agent_name="Maintenance Analyst",
        question=question,
        implementation_mode="Implemented · Deterministic Gold Data",
        summary=f"Analyzed {len(df)} property maintenance summaries from `{maint_table}`.",
        findings=findings,
        evidence_df=evidence_df[cols],
        trace_sql=trace_sql,
        source_tables=[maint_table],
        recommended_action=(
            f"Dispatch field teams to clear the {active_backlog:,} active work orders and audit "
            f"repeat repairs on {top_prop['property_id']}."
        ),
        simulated_preview=(
            f"[SIMULATED DEMO ONLY] Dispatch Escalation Draft for {top_prop['property_id']}: "
            f"Total spend ${top_prop['total_maintenance_cost']:,.0f}. No work-order system updated."
        ),
    )


def _run_capex_analyst(question: str) -> AgentResult:
    """Analyze capital investments by category, market, and property."""
    capex_table = resolve_table_name(
        "CAPEX_TABLE", "workspace.gold.gold_capex_summary"
    )
    df = query_table(capex_table, limit=50000)
    if df.empty:
        return AgentResult(
            agent_name="CapEx Analyst",
            question=question,
            implementation_mode="Implemented · Deterministic Gold Data",
            summary="No CapEx records were returned from Unity Catalog.",
            source_tables=[capex_table],
        )

    df = coerce_numeric(
        df,
        ["market_id", "investment_count", "total_capex_amount", "avg_capex_amount"],
    )
    total_capex = float(df["total_capex_amount"].sum())
    total_inv = int(df["investment_count"].sum())
    weighted_avg = total_capex / total_inv if total_inv > 0 else 0.0

    by_cat = (
        df.groupby("category", as_index=False)
        .agg(
            Properties=("property_id", "nunique"),
            Investments=("investment_count", "sum"),
            Total_CapEx=("total_capex_amount", "sum"),
        )
        .sort_values("Total_CapEx", ascending=False)
    )
    by_cat["Avg_Per_Investment"] = (
        by_cat["Total_CapEx"] / by_cat["Investments"].replace(0, pd.NA)
    ).fillna(0.0)

    by_mkt = (
        df.groupby(["market_name", "region"], as_index=False)
        .agg(
            Properties=("property_id", "nunique"),
            Investments=("investment_count", "sum"),
            Total_CapEx=("total_capex_amount", "sum"),
        )
        .sort_values("Total_CapEx", ascending=False)
    )

    top_cat = by_cat.iloc[0]
    top_mkt = by_mkt.iloc[0]
    findings = [
        f"Total CapEx equals ${total_capex:,.2f} across {total_inv:,} investments "
        f"(weighted average ${weighted_avg:,.2f} per investment).",
        f"Top investment category: {top_cat['category']} at ${top_cat['Total_CapEx']:,.0f} "
        f"({top_cat['Total_CapEx'] / (total_capex or 1.0) * 100:.1f}% of total).",
        f"Top investment market: {top_mkt['market_name']} at ${top_mkt['Total_CapEx']:,.0f}.",
    ]

    q_lower = question.lower()
    if "propert" in q_lower:
        evidence_df = (
            df.groupby(["property_id", "market_name", "region"], as_index=False)
            .agg(
                Categories=("category", "nunique"),
                Investments=("investment_count", "sum"),
                Total_CapEx=("total_capex_amount", "sum"),
            )
            .sort_values("Total_CapEx", ascending=False)
            .head(15)
        )
        trace_sql = (
            "SELECT property_id, market_name, region,\n"
            "       COUNT(DISTINCT category) AS Categories,\n"
            "       SUM(investment_count) AS Investments,\n"
            "       SUM(total_capex_amount) AS Total_CapEx\n"
            f"FROM {capex_table}\n"
            "GROUP BY property_id, market_name, region\n"
            "ORDER BY Total_CapEx DESC LIMIT 15;"
        )
    elif "market" in q_lower and "category" not in q_lower:
        evidence_df = by_mkt
        trace_sql = (
            "SELECT market_name, region,\n"
            "       COUNT(DISTINCT property_id) AS Properties,\n"
            "       SUM(investment_count) AS Investments,\n"
            "       SUM(total_capex_amount) AS Total_CapEx\n"
            f"FROM {capex_table}\n"
            "GROUP BY market_name, region\n"
            "ORDER BY Total_CapEx DESC;"
        )
    else:
        evidence_df = by_cat
        trace_sql = (
            "SELECT category,\n"
            "       COUNT(DISTINCT property_id) AS Properties,\n"
            "       SUM(investment_count) AS Investments,\n"
            "       SUM(total_capex_amount) AS Total_CapEx,\n"
            "       SUM(total_capex_amount) / NULLIF(SUM(investment_count), 0) AS Avg_Per_Investment\n"
            f"FROM {capex_table}\n"
            "GROUP BY category\n"
            "ORDER BY Total_CapEx DESC;"
        )

    return AgentResult(
        agent_name="CapEx Analyst",
        question=question,
        implementation_mode="Implemented · Deterministic Gold Data",
        summary=f"Evaluated {len(df):,} CapEx summary records across {df['property_id'].nunique():,} properties.",
        findings=findings,
        evidence_df=evidence_df,
        trace_sql=trace_sql,
        source_tables=[capex_table],
        recommended_action=(
            f"Review ROI and post-upgrade maintenance reductions in {top_mkt['market_name']} "
            f"and {top_cat['category']} projects."
        ),
        simulated_preview=(
            f"[SIMULATED DEMO ONLY] Capital Committee Summary: {top_cat['category']} leads "
            f"spend at ${top_cat['Total_CapEx']:,.0f}. No budget approval workflow triggered."
        ),
    )


AGENT_RUNNERS: Dict[str, Callable[[str], AgentResult]] = {
    "portfolio": _run_portfolio_analyst,
    "market": _run_market_assistant,
    "maintenance": _run_maintenance_analyst,
    "capex": _run_capex_analyst,
}


def run_agent_analysis(agent_key: str, question: str) -> AgentResult:
    """Execute the requested specialist Gold-data agent."""
    runner = AGENT_RUNNERS.get(agent_key)
    if runner is None:
        raise ValueError(f"Unknown agent key: {agent_key!r}")
    return runner(question.strip() or AGENT_SPEC_MAP[agent_key].sample_questions[0])


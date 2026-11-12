"""Data Products Catalog, Governance, and Business Definitions page (Milestone 9)."""

from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from utils.database import (
    get_table_freshness,
    get_table_row_count,
    query_table,
    resolve_table_name,
    run_query,
)
from utils.ui import (
    apply_theme,
    chart_card,
    render_empty_state,
    render_header,
    render_kpi_row,
    render_page_header,
    render_section_header,
    status_badge_html,
)

st.set_page_config(
    page_title="Data Products · Property Intelligence AI Studio",
    page_icon="📦",
    layout="wide",
)

DATA_PRODUCTS: List[Dict[str, Any]] = [
    {
        "key": "portfolio_kpis",
        "name": "Portfolio Monthly KPIs",
        "env_var": "PORTFOLIO_KPIS_TABLE",
        "default_table": "workspace.gold.gold_portfolio_kpis",
        "domain": "Portfolio",
        "grain": "1 row per reporting month",
        "description": (
            "Executive monthly rollup of portfolio property count, occupied vs. service days, "
            "total rental revenue, and net operating income (NOI)."
        ),
        "definitions": [
            "Weighted Occupancy (%) = total_occupied_days / total_service_days * 100",
            "NOI Margin (%) = total_noi / total_rental_revenue * 100",
        ],
        "page_path": "app.py",
        "page_label": "Open Portfolio Overview",
        "page_icon": "🏠",
        "key_columns": ["month_year", "total_properties", "total_rental_revenue", "total_noi"],
    },
    {
        "key": "market_monthly",
        "name": "Market Monthly Performance",
        "env_var": "MARKET_MONTHLY_TABLE",
        "default_table": "workspace.gold.gold_market_monthly",
        "domain": "Markets",
        "grain": "1 row per market per month",
        "description": (
            "Regional market benchmarking table tracking property counts, occupancy days, "
            "rental revenue, operating expenses, net operating revenue, and NOI across all 5 markets."
        ),
        "definitions": [
            "Operating Expense Ratio (%) = total_opex / net_operating_revenue * 100",
            "NOI per Property = total_noi / property_count",
        ],
        "page_path": "pages/02_Market_Analytics.py",
        "page_label": "Open Market Analytics",
        "page_icon": "🌎",
        "key_columns": ["month", "market_name", "region", "total_rental_revenue", "total_noi"],
    },
    {
        "key": "property_performance",
        "name": "Property Performance Summary",
        "env_var": "PROPERTY_PERFORMANCE_TABLE",
        "default_table": "workspace.gold.gold_property_performance",
        "domain": "Properties",
        "grain": "1 row per property",
        "description": (
            "Asset-level cumulative performance summary across 300 residential properties with "
            "property attributes, overall occupancy, NOI, average monthly NOI, and expense ratio."
        ),
        "definitions": [
            "Underperforming Occupancy Watchlist = overall_occupancy_pct < 85.0%",
            "Negative NOI Flag = total_noi <= 0",
        ],
        "page_path": "pages/03_Property_Analytics.py",
        "page_label": "Open Property Analytics",
        "page_icon": "🏢",
        "key_columns": ["property_id", "market_name", "property_type", "total_noi"],
    },
    {
        "key": "maintenance_summary",
        "name": "Maintenance Operations Summary",
        "env_var": "MAINTENANCE_TABLE",
        "default_table": "workspace.gold.gold_maintenance_summary",
        "domain": "Maintenance",
        "grain": "1 row per property",
        "description": (
            "Property-grain maintenance work-order lifecycle summary covering completed, open, "
            "in-progress, and cancelled counts, maintenance spend, and average completion days."
        ),
        "definitions": [
            "Completion Rate (%) = completed_work_orders / total_work_orders * 100",
            "Weighted Avg Completion (Days) = SUM(avg_completion_days * completed_work_orders) / SUM(completed_work_orders)",
            "Active Backlog = open_work_orders + in_progress_work_orders",
        ],
        "page_path": "pages/04_Maintenance.py",
        "page_label": "Open Maintenance Analytics",
        "page_icon": "🔧",
        "key_columns": ["property_id", "market_name", "total_work_orders", "total_maintenance_cost"],
    },
    {
        "key": "capex_summary",
        "name": "CapEx Investment Summary",
        "env_var": "CAPEX_TABLE",
        "default_table": "workspace.gold.gold_capex_summary",
        "domain": "CapEx",
        "grain": "Property × month × category",
        "description": (
            "Capital expenditure summary tracking investment counts, total spend, and average project "
            "cost across properties, regional markets, months, and improvement categories."
        ),
        "definitions": [
            "Weighted Avg Investment = SUM(total_capex_amount) / SUM(investment_count)",
            "Category Share (%) = category total_capex_amount / portfolio total_capex_amount * 100",
        ],
        "page_path": "pages/05_CapEx.py",
        "page_label": "Open CapEx Analytics",
        "page_icon": "🏗️",
        "key_columns": ["property_id", "market_name", "capex_month", "category", "total_capex_amount"],
    },
    {
        "key": "property_monthly",
        "name": "Property Monthly Granular Facts",
        "env_var": "PROPERTY_MONTHLY_TABLE",
        "default_table": "workspace.gold.gold_property_monthly",
        "domain": "Properties",
        "grain": "Property × reporting month",
        "description": (
            "Monthly property-level Gold table supporting longitudinal asset tracking and "
            "Databricks Genie natural-language time-series queries."
        ),
        "definitions": [
            "Serves as the granular time-series foundation alongside Property Performance Summary.",
        ],
        "page_path": "pages/08_Genie_Assistant.py",
        "page_label": "Query via Genie Assistant",
        "page_icon": "✨",
        "key_columns": [],
    },
]


def _inspect_table_schema(table_fqn: str) -> pd.DataFrame:
    """Return cleaned column schema from DESCRIBE TABLE, or empty DataFrame."""
    try:
        desc_df = run_query(f"DESCRIBE TABLE {table_fqn}")
        if desc_df.empty or "col_name" not in desc_df.columns:
            return pd.DataFrame()
        cleaned = desc_df[
            desc_df["col_name"].notna()
            & (desc_df["col_name"].astype(str).str.strip() != "")
            & (~desc_df["col_name"].astype(str).str.strip().str.startswith("#"))
        ].copy()
        keep_cols = [c for c in ["col_name", "data_type", "comment"] if c in cleaned.columns]
        return cleaned[keep_cols].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def _evaluate_data_quality(
    table_fqn: str,
    row_count: Optional[int],
    key_columns: List[str],
) -> Dict[str, Any]:
    """Run live non-destructive completeness checks on a Unity Catalog table."""
    if row_count is None:
        return {
            "label": "Unavailable",
            "tone": "danger",
            "detail": "Could not query table metadata from SQL Warehouse.",
        }
    if row_count == 0:
        return {
            "label": "Empty Table",
            "tone": "warning",
            "detail": "Table is accessible but contains 0 rows.",
        }
    if not key_columns:
        return {
            "label": "Available (Row Check)",
            "tone": "info",
            "detail": f"{row_count:,} rows verified via live SQL COUNT(*).",
        }

    try:
        null_exprs = ", ".join(
            f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS null_{col}"
            for col in key_columns
        )
        null_df = run_query(f"SELECT {null_exprs} FROM {table_fqn}")
        if null_df.empty:
            return {
                "label": "Available",
                "tone": "info",
                "detail": f"{row_count:,} rows verified.",
            }
        total_nulls = int(
            sum(int(null_df.iloc[0][c] or 0) for c in null_df.columns)
        )
        if total_nulls == 0:
            return {
                "label": "Passed (0 Nulls)",
                "tone": "success",
                "detail": f"{row_count:,} rows · 0 nulls across {len(key_columns)} key columns.",
            }
        return {
            "label": f"Attention ({total_nulls} Nulls)",
            "tone": "warning",
            "detail": f"{total_nulls:,} null values detected across key columns.",
        }
    except Exception as exc:
        return {
            "label": "Available",
            "tone": "info",
            "detail": f"{row_count:,} rows verified (null check skipped: {type(exc).__name__}).",
        }


@st.cache_data(ttl=300, show_spinner=False)
def load_data_products_catalog() -> List[Dict[str, Any]]:
    """Collect live row counts, Delta freshness, schemas, and quality status for all Gold products."""
    catalog: List[Dict[str, Any]] = []
    for spec in DATA_PRODUCTS:
        table_fqn = resolve_table_name(spec["env_var"], spec["default_table"])
        row_count = get_table_row_count(table_fqn)
        freshness = get_table_freshness(table_fqn)
        schema_df = _inspect_table_schema(table_fqn)
        dq = _evaluate_data_quality(
            table_fqn=table_fqn,
            row_count=row_count,
            key_columns=spec["key_columns"],
        )

        if freshness.get("status") == "available":
            refresh_str = f"v{freshness.get('version')} · {freshness.get('timestamp')}"
        else:
            refresh_str = "Live SQL Connected (History restricted)"

        catalog.append(
            {
                **spec,
                "table_fqn": table_fqn,
                "row_count": row_count,
                "freshness": freshness,
                "refresh_str": refresh_str,
                "schema_df": schema_df,
                "dq": dq,
            }
        )
    return catalog


def _render_glossary_section() -> None:
    """Render standardized enterprise business KPI definitions."""
    render_section_header(
        title="Standardized Business Glossary",
        subtitle="Consistent metric formulas enforced across Portfolio, Markets, Properties, Maintenance, and CapEx.",
        badge="Governance",
        badge_tone="neutral",
    )

    glossary_rows = [
        {
            "Metric": "Weighted Occupancy (%)",
            "Formula": "SUM(total_occupied_days) / SUM(total_service_days) * 100",
            "Source Table": "gold_portfolio_kpis / gold_market_monthly",
        },
        {
            "Metric": "Net Operating Income (NOI)",
            "Formula": "SUM(total_noi)",
            "Source Table": "gold_portfolio_kpis / gold_market_monthly / gold_property_performance",
        },
        {
            "Metric": "Operating Expense Ratio (%)",
            "Formula": "SUM(total_opex) / SUM(net_operating_revenue) * 100",
            "Source Table": "gold_market_monthly",
        },
        {
            "Metric": "Weighted Avg Completion Time",
            "Formula": "SUM(avg_completion_days * completed_work_orders) / SUM(completed_work_orders)",
            "Source Table": "gold_maintenance_summary",
        },
        {
            "Metric": "Weighted Avg CapEx Investment",
            "Formula": "SUM(total_capex_amount) / SUM(investment_count)",
            "Source Table": "gold_capex_summary",
        },
    ]

    with chart_card(
        title="Enterprise KPI Definitions",
        subtitle="Approved definitions used by analytics dashboards, specialist agents, and Genie",
        badge="Single Source of Truth",
        badge_tone="success",
    ):
        st.dataframe(
            pd.DataFrame(glossary_rows),
            use_container_width=True,
            hide_index=True,
        )


def main() -> None:
    """Render the Data Products Catalog and Governance page."""
    apply_theme()
    render_header(active_page="", active_section="Data Products")

    try:
        with st.spinner("Inspecting Unity Catalog Gold data products..."):
            catalog = load_data_products_catalog()

        total_products = len(catalog)
        available_count = sum(1 for item in catalog if item["row_count"] is not None)
        total_rows = sum(item["row_count"] or 0 for item in catalog)
        passed_dq = sum(1 for item in catalog if item["dq"]["tone"] == "success")

        render_page_header(
            title="Gold Data Products Catalog",
            description=(
                "Curated Unity Catalog Gold datasets powering Property Intelligence AI Studio, "
                "complete with live row counts, Delta refresh history, data quality status, and business definitions."
            ),
            domain_label="Data Products · workspace.gold",
            reporting_period=f"{available_count}/{total_products} Gold Tables Live",
            status_text="Unity Catalog Connected" if available_count > 0 else "Check Warehouse",
            status_tone="success" if available_count > 0 else "warning",
        )

        # Filters + Refresh
        with st.container(border=True):
            f1, f2, f3 = st.columns([2.2, 1.5, 0.9])
            with f1:
                search_text = st.text_input(
                    "Search Data Products",
                    placeholder="Search by table name, domain, or KPI definition...",
                )
            with f2:
                domains = ["All Domains"] + sorted(
                    list({item["domain"] for item in catalog})
                )
                selected_domain = st.selectbox("Domain", domains)
            with f3:
                st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                if st.button("Refresh Catalog", use_container_width=True):
                    load_data_products_catalog.clear()
                    st.rerun()

        render_kpi_row(
            [
                {
                    "label": "Gold Data Products",
                    "value": f"{total_products}",
                    "delta": "Unity Catalog",
                    "delta_tone": "info",
                    "caption": "Catalog: workspace · Schema: gold",
                    "icon": "📦",
                },
                {
                    "label": "Live Accessible Tables",
                    "value": f"{available_count} / {total_products}",
                    "delta": "SQL Verified" if available_count == total_products else "Partial",
                    "delta_tone": "success" if available_count == total_products else "warning",
                    "caption": "Queried via SQL Warehouse",
                    "icon": "✅",
                },
                {
                    "label": "Total Gold Records",
                    "value": f"{total_rows:,}",
                    "delta": "Live COUNT(*)",
                    "delta_tone": "neutral",
                    "caption": "Across all curated Gold datasets",
                    "icon": "🗂️",
                },
                {
                    "label": "Key Completeness Checks",
                    "value": f"{passed_dq} Passed",
                    "delta": "Runtime SQL DQ",
                    "delta_tone": "success" if passed_dq > 0 else "neutral",
                    "caption": "Non-null validation on mapped keys",
                    "icon": "🛡️",
                },
            ]
        )

        # Apply search & domain filters
        filtered_catalog = []
        cleaned_search = (search_text or "").strip().lower()
        for item in catalog:
            if selected_domain != "All Domains" and item["domain"] != selected_domain:
                continue
            if cleaned_search:
                haystack = " ".join(
                    [
                        item["name"],
                        item["table_fqn"],
                        item["domain"],
                        item["description"],
                        " ".join(item["definitions"]),
                    ]
                ).lower()
                if cleaned_search not in haystack:
                    continue
            filtered_catalog.append(item)

        if not filtered_catalog:
            render_empty_state(
                "No Matching Data Products",
                "Adjust the domain filter or search keyword to view available Gold datasets.",
                tone="warning",
            )
            st.stop()

        # Overview table
        render_section_header(
            title="Gold Dataset Inventory",
            subtitle="Live row counts, Delta commit freshness, and completeness status.",
            badge=f"{len(filtered_catalog)} Shown",
            badge_tone="info",
        )

        summary_rows = [
            {
                "Data Product": item["name"],
                "Unity Catalog Table": item["table_fqn"],
                "Domain": item["domain"],
                "Grain": item["grain"],
                "Rows": f"{item['row_count']:,}" if item["row_count"] is not None else "—",
                "Last Refresh": item["refresh_str"],
                "Quality Status": item["dq"]["label"],
            }
            for item in filtered_catalog
        ]
        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True,
        )

        # Detailed Data Product Cards
        render_section_header(
            title="Data Product Details & Schema Explorer",
            subtitle="Business definitions, live schemas, sample rows, and direct navigation links.",
        )

        for item in filtered_catalog:
            with chart_card(
                title=f"{item['page_icon']} {item['name']}",
                subtitle=f"{item['table_fqn']} · Grain: {item['grain']}",
                badge=item["dq"]["label"],
                badge_tone=item["dq"]["tone"],
            ):
                row_badge = status_badge_html(
                    f"{item['row_count']:,} rows" if item["row_count"] is not None else "Row count N/A",
                    tone="neutral",
                )
                refresh_badge = status_badge_html(
                    item["refresh_str"],
                    tone="success" if item["freshness"].get("status") == "available" else "info",
                )
                domain_badge = status_badge_html(item["domain"], tone="info")
                st.markdown(
                    f"{domain_badge} {row_badge} {refresh_badge}",
                    unsafe_allow_html=True,
                )

                st.markdown(item["description"])
                st.caption(f"Quality check: {item['dq']['detail']}")

                st.markdown("**Business Definitions:**")
                for defn in item["definitions"]:
                    st.markdown(f"- `{defn}`")

                link_col, _ = st.columns([1.8, 3.2])
                with link_col:
                    st.page_link(
                        item["page_path"],
                        label=item["page_label"],
                        icon=item["page_icon"],
                    )

                with st.expander(f"Inspect Schema & Sample Rows ({item['table_fqn'].split('.')[-1]})"):
                    s_col, p_col = st.columns([1.0, 1.4])
                    with s_col:
                        st.markdown("**Live Column Schema (`DESCRIBE TABLE`)**")
                        if not item["schema_df"].empty:
                            st.dataframe(
                                item["schema_df"],
                                use_container_width=True,
                                hide_index=True,
                            )
                        else:
                            st.caption("Schema metadata unavailable.")
                    with p_col:
                        st.markdown("**Sample Preview (Top 5 Rows)**")
                        try:
                            sample_df = query_table(item["table_fqn"], limit=5)
                            st.dataframe(
                                sample_df,
                                use_container_width=True,
                                hide_index=True,
                            )
                        except Exception as sample_exc:
                            st.caption(f"Preview unavailable: {sample_exc}")

        _render_glossary_section()

    except Exception as exc:
        render_page_header(
            title="Gold Data Products Catalog",
            description="Unity Catalog Gold dataset directory and governance.",
            domain_label="Data Products",
            status_text="Connection Issue",
            status_tone="danger",
        )
        st.error("Unable to load Data Products catalog.")
        st.exception(exc)


if __name__ == "__main__":
    main()


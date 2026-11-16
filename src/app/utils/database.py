"""Databricks SQL Warehouse connectivity and Gold-layer query helpers."""

import os
import re
import time
from typing import Any, Dict, Iterable, Optional

import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

from utils.monitoring import record_event

_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_`.-]+$")
_READ_ONLY_PREFIX_RE = re.compile(r"^(SELECT|WITH|DESCRIBE|SHOW)\b", re.IGNORECASE)
_FORBIDDEN_SQL_RE = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|MERGE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def _validate_table_identifier(table_name: str) -> str:
    """Validate a Unity Catalog table identifier before interpolating into SQL."""
    cleaned = (table_name or "").strip()
    if not cleaned or not _VALID_IDENTIFIER_RE.match(cleaned):
        raise ValueError(f"Invalid Unity Catalog table identifier: {table_name!r}")
    return cleaned


def validate_read_only_sql(sql_query: str) -> str:
    """Ensure SQL statements executed by the app are single, read-only queries."""
    cleaned = (sql_query or "").strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()

    if not cleaned:
        raise ValueError("SQL query must not be empty.")
    if ";" in cleaned or "--" in cleaned or "/*" in cleaned:
        raise ValueError("Stacked SQL statements and inline comments are not permitted.")
    if not _READ_ONLY_PREFIX_RE.match(cleaned):
        raise ValueError("Only SELECT, WITH, DESCRIBE, and SHOW statements are permitted.")
    if _FORBIDDEN_SQL_RE.search(cleaned):
        raise ValueError("Mutating or DDL SQL keywords are not permitted.")
    return cleaned


def _get_config_value(key: str, default: str = "") -> str:
    """Read configuration value from OS environment or Streamlit secrets."""
    val = os.getenv(key, "").strip()
    if not val:
        try:
            import streamlit as st
            val = str(st.secrets.get(key, "")).strip()
        except Exception:
            val = ""
    return val or default


def resolve_table_name(env_var: str, default_table: str) -> str:
    """Resolve a configured table name from environment with a verified fallback."""
    configured = _get_config_value(env_var)
    return _validate_table_identifier(configured or default_table)


def get_connection():
    """Create a Databricks SQL Warehouse connection using Databricks SDK auth."""
    # Ensure Databricks host/token in st.secrets are propagated to os.environ for Databricks SDK
    for secret_key in ("DATABRICKS_HOST", "DATABRICKS_TOKEN"):
        s_val = _get_config_value(secret_key)
        if s_val and secret_key not in os.environ:
            os.environ[secret_key] = s_val

    cfg = Config()

    warehouse_id = _get_config_value("DATABRICKS_WAREHOUSE_ID")

    if not warehouse_id:
        raise ValueError(
            "SQL Warehouse resource is not configured.\n"
            "If running locally, set DATABRICKS_WAREHOUSE_ID in .streamlit/secrets.toml or your environment."
        )

    server_hostname = cfg.host.replace("https://", "").replace("http://", "")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    )


def run_query(sql_query: str) -> pd.DataFrame:
    """Execute a validated read-only SQL statement and record latency telemetry."""
    safe_sql = validate_read_only_sql(sql_query)
    started = time.perf_counter()
    target_preview = safe_sql.split()[0].upper()
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(safe_sql)
                rows = cursor.fetchall()
                columns = (
                    [column[0] for column in cursor.description]
                    if cursor.description
                    else []
                )
                df = pd.DataFrame(rows, columns=columns)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        record_event(
            category="sql",
            target=target_preview,
            status="ok",
            duration_ms=elapsed_ms,
            detail=f"rows={len(df)}",
        )
        return df
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        record_event(
            category="sql",
            target=target_preview,
            status="error",
            duration_ms=elapsed_ms,
            detail=type(exc).__name__,
        )
        raise


def query_table(table_name: str, limit: int = 10) -> pd.DataFrame:
    """Query rows from a Unity Catalog table up to the requested positive limit."""
    safe_table = _validate_table_identifier(table_name)
    safe_limit = max(1, int(limit))
    return run_query(f"SELECT * FROM {safe_table} LIMIT {safe_limit}")


def get_table_row_count(table_name: str) -> Optional[int]:
    """Return total row count for a table, or None if unavailable."""
    try:
        safe_table = _validate_table_identifier(table_name)
        df = run_query(f"SELECT COUNT(*) AS row_count FROM {safe_table}")
        if df.empty:
            return None
        return int(df.iloc[0]["row_count"])
    except Exception:
        return None


def get_table_freshness(table_name: str) -> Dict[str, Any]:
    """Inspect latest Delta Lake commit metadata via DESCRIBE HISTORY."""
    try:
        safe_table = _validate_table_identifier(table_name)
        history_df = run_query(f"DESCRIBE HISTORY {safe_table} LIMIT 1")
        if history_df.empty:
            return {"status": "unavailable", "table": safe_table}

        latest = history_df.iloc[0]
        timestamp_val = latest.get("timestamp")
        ts_str = (
            pd.to_datetime(timestamp_val).strftime("%Y-%m-%d %H:%M UTC")
            if pd.notna(timestamp_val)
            else "Unknown"
        )
        return {
            "status": "available",
            "table": safe_table,
            "version": int(latest["version"]) if pd.notna(latest.get("version")) else None,
            "timestamp": ts_str,
            "operation": str(latest.get("operation") or "WRITE"),
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "table": table_name,
            "reason": str(exc),
        }


def coerce_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Safely convert numeric or Decimal columns to floats on a copy of df."""
    cleaned = df.copy()
    for col in columns:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0.0)
    return cleaned

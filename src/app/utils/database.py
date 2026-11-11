"""Databricks SQL Warehouse connectivity and Gold-layer query helpers."""

import os
import re
from typing import Any, Dict, Optional

import pandas as pd
from databricks import sql
from databricks.sdk.core import Config

_VALID_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_`.-]+$")


def _validate_table_identifier(table_name: str) -> str:
    """Validate a Unity Catalog table identifier before interpolating into SQL."""
    cleaned = (table_name or "").strip()
    if not cleaned or not _VALID_IDENTIFIER_RE.match(cleaned):
        raise ValueError(f"Invalid Unity Catalog table identifier: {table_name!r}")
    return cleaned


def resolve_table_name(env_var: str, default_table: str) -> str:
    """Resolve a configured table name from environment with a verified fallback."""
    configured = os.getenv(env_var, "").strip()
    return _validate_table_identifier(configured or default_table)


def get_connection():
    """Create a Databricks SQL Warehouse connection using Databricks SDK auth."""
    cfg = Config()

    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")

    if not warehouse_id:
        raise ValueError("SQL Warehouse resource is not configured.")

    server_hostname = cfg.host.replace("https://", "").replace("http://", "")

    return sql.connect(
        server_hostname=server_hostname,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        credentials_provider=lambda: cfg.authenticate,
    )


def run_query(sql_query: str) -> pd.DataFrame:
    """Execute a read-only SQL statement and return results as a DataFrame."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = (
                [column[0] for column in cursor.description]
                if cursor.description
                else []
            )
            return pd.DataFrame(rows, columns=columns)


def query_table(table_name: str, limit: int = 10) -> pd.DataFrame:
    """Query rows from a Unity Catalog table up to the requested limit."""
    safe_table = _validate_table_identifier(table_name)
    return run_query(f"SELECT * FROM {safe_table} LIMIT {int(limit)}")


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

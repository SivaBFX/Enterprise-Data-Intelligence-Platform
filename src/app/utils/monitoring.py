"""Lightweight logging and in-session telemetry helpers for Databricks Apps."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

import streamlit as st

_LOGGER_NAME = "property_intelligence"
_MAX_SESSION_EVENTS = 50


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return a configured stream logger compatible with Databricks Apps logs."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def record_event(
    category: str,
    target: str,
    status: str,
    duration_ms: float,
    detail: str = "",
) -> None:
    """Log an operational event and store bounded telemetry in Streamlit session state."""
    logger = get_logger()
    msg = f"[{category}] target={target} status={status} duration_ms={duration_ms:.1f}"
    if detail:
        msg += f" detail={detail}"

    if status == "error":
        logger.error(msg)
    elif status == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)

    try:
        events: List[Dict[str, Any]] = st.session_state.setdefault(
            "app_telemetry_events", []
        )
        events.append(
            {
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "category": category,
                "target": target,
                "status": status,
                "duration_ms": round(float(duration_ms), 1),
                "detail": detail,
            }
        )
        if len(events) > _MAX_SESSION_EVENTS:
            del events[: len(events) - _MAX_SESSION_EVENTS]
    except Exception:
        # Session state is unavailable outside active Streamlit script runs (e.g., unit tests).
        pass


def get_recent_events() -> List[Dict[str, Any]]:
    """Return recent session telemetry events newest-first."""
    try:
        events = list(st.session_state.get("app_telemetry_events", []))
        return list(reversed(events))
    except Exception:
        return []


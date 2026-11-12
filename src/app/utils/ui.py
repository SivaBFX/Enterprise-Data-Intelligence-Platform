"""Shared AI Studio UI design system and reusable components."""

from contextlib import contextmanager
import html
from pathlib import Path
from typing import Iterable, Mapping, Optional

import pandas as pd
import streamlit as st

APP_ROOT = Path(__file__).resolve().parent.parent

# Centralized tone palette for status badges, KPI deltas, and insight cards.
TONE_STYLES = {
    "success": {
        "bg": "#e8f5f1",
        "border": "#a7dccb",
        "text": "#065f46",
        "dot": "#087f67",
        "accent": "#087f67",
    },
    "warning": {
        "bg": "#fef7e6",
        "border": "#f5d08a",
        "text": "#92400e",
        "dot": "#d97706",
        "accent": "#d97706",
    },
    "danger": {
        "bg": "#fef2f2",
        "border": "#fecaca",
        "text": "#991b1b",
        "dot": "#dc2626",
        "accent": "#dc2626",
    },
    "info": {
        "bg": "#eff6ff",
        "border": "#bfdbfe",
        "text": "#1e40af",
        "dot": "#2563eb",
        "accent": "#2563eb",
    },
    "neutral": {
        "bg": "#f1f5f9",
        "border": "#cbd5e1",
        "text": "#334155",
        "dot": "#64748b",
        "accent": "#64748b",
    },
}

TOP_NAV_ITEMS = [
    ("Today", "app.py", "🏠"),
    ("Data Products", "pages/06_Data_Products.py", "📦"),
    ("Agents", "pages/07_Agents.py", "🤖"),
]

DOMAIN_NAV_ITEMS = [
    ("Portfolio", "app.py", "🏠"),
    ("Markets", "pages/02_Market_Analytics.py", "🌎"),
    ("Properties", "pages/03_Property_Analytics.py", "🏢"),
    ("Maintenance", "pages/04_Maintenance.py", "🔧"),
    ("CapEx", "pages/05_CapEx.py", "🏗️"),
]


def _escape(value: object) -> str:
    """Escape dynamic text before embedding into HTML."""
    return html.escape(str(value), quote=True)


def _page_exists(relative_path: Optional[str]) -> bool:
    """Return True when a Streamlit page file exists relative to src/app."""
    if not relative_path:
        return False
    return (APP_ROOT / relative_path).is_file()


def _get_tone(tone: str) -> dict:
    """Return color tokens for a semantic tone with safe neutral fallback."""
    return TONE_STYLES.get(tone, TONE_STYLES["neutral"])


def _render_html(markup: str) -> None:
    """Render HTML without leading indentation so Markdown never treats it as code."""
    cleaned = "\n".join(line.lstrip() for line in markup.splitlines()).strip()
    st.markdown(cleaned, unsafe_allow_html=True)


def apply_theme() -> None:
    """Inject the AI Studio light theme stylesheet with accessible text contrast."""
    _render_html(
        """
<style>
:root {
    --ai-bg: #f6f8fb;
    --ai-surface: #ffffff;
    --ai-surface-subtle: #f1f5f9;
    --ai-border: #e2e8f0;
    --ai-border-strong: #cbd5e1;
    --ai-navy: #0f2544;
    --ai-text: #1e293b;
    --ai-body: #334155;
    --ai-muted: #475569;
    --ai-green: #087f67;
    --ai-green-hover: #066452;
    --ai-green-soft: #e8f5f1;
    --ai-green-border: #9fd4c5;
    --text-color: #1e293b;
    --background-color: #f6f8fb;
    --secondary-background-color: #ffffff;
    --primary-color: #087f67;
}

/* Base canvas and typography */
html, body, .stApp,
div[data-testid="stAppViewContainer"],
div[data-testid="stMain"] {
    background-color: var(--ai-bg) !important;
    color: var(--ai-text) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", Arial, sans-serif;
}

.main .block-container {
    max-width: 1420px;
    padding-top: 1.15rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Hide default sidebar navigation and style top toolbar cleanly */
section[data-testid="stSidebar"] {
    display: none !important;
}

header[data-testid="stHeader"] {
    background: rgba(246, 248, 251, 0.88) !important;
    color: var(--ai-muted) !important;
}

header[data-testid="stHeader"] svg,
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] span {
    color: var(--ai-muted) !important;
}

/* Global accessible text contrast */
.stApp p,
.stApp li,
.stApp label,
.stApp td,
.stApp th {
    color: var(--ai-body);
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6 {
    color: var(--ai-navy) !important;
    letter-spacing: -0.02em;
}

div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] li {
    color: var(--ai-body) !important;
}

div[data-testid="stMarkdownContainer"] strong,
div[data-testid="stMarkdownContainer"] b {
    color: var(--ai-navy) !important;
}

div[data-testid="stMarkdownContainer"] code {
    background-color: var(--ai-surface-subtle);
    color: var(--ai-navy);
    border: 1px solid var(--ai-border);
    border-radius: 5px;
    padding: 0.1rem 0.35rem;
}

div[data-testid="stCaptionContainer"],
div[data-testid="stCaptionContainer"] p,
div[data-testid="stCaptionContainer"] span,
.stCaption {
    color: var(--ai-muted) !important;
    opacity: 1 !important;
}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] label,
div[data-testid="stWidgetLabel"] span {
    color: var(--ai-text) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
}

/* Top header brand & profile chip */
.ai-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 2px 0;
}

.ai-brand-mark {
    width: 40px;
    height: 40px;
    border-radius: 11px;
    background: linear-gradient(135deg, #e8f5f1 0%, #d3ede5 100%);
    border: 1px solid var(--ai-green-border);
    color: var(--ai-green);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    font-weight: 700;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(8, 127, 103, 0.08);
}

.ai-brand-title {
    font-size: 1.32rem;
    font-weight: 750;
    color: var(--ai-navy);
    line-height: 1.18;
    letter-spacing: -0.025em;
}

.ai-brand-subtitle {
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--ai-muted);
    margin-top: 2px;
}

.ai-user-chip {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 999px;
    padding: 5px 12px 5px 6px;
    box-shadow: 0 1px 3px rgba(15, 37, 68, 0.04);
    margin-left: auto;
    width: fit-content;
    max-width: 100%;
}

.ai-user-avatar {
    width: 30px;
    height: 30px;
    border-radius: 999px;
    background: var(--ai-navy);
    color: #ffffff;
    font-size: 0.75rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0.03em;
}

.ai-user-meta {
    display: flex;
    flex-direction: column;
    line-height: 1.15;
    min-width: 0;
}

.ai-user-name {
    font-size: 0.8rem;
    font-weight: 650;
    color: var(--ai-navy);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.ai-user-role {
    font-size: 0.7rem;
    color: var(--ai-muted);
    white-space: nowrap;
}

.ai-hairline {
    border-top: 1px solid var(--ai-border);
    margin: 0.65rem 0 0.75rem 0;
}

.ai-domain-row-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.45rem;
}

.ai-domain-label {
    color: var(--ai-muted);
    font-size: 0.7rem;
    font-weight: 750;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

/* Navigation links (top workspace & data domain pills) */
.ai-nav-active-marker {
    display: none;
}

div[data-testid="stPageLink"] {
    width: 100%;
}

div[data-testid="stPageLink"] a {
    width: 100% !important;
    min-height: 40px;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px;
    padding: 0.45rem 0.8rem !important;
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border) !important;
    border-radius: 10px !important;
    color: var(--ai-text) !important;
    text-decoration: none !important;
    box-shadow: 0 1px 2px rgba(15, 37, 68, 0.03);
    transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

div[data-testid="stPageLink"] a p,
div[data-testid="stPageLink"] a span,
div[data-testid="stPageLink"] a div {
    color: var(--ai-text) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
}

div[data-testid="stPageLink"] a:hover {
    background-color: #f0f8f5 !important;
    border-color: var(--ai-green-border) !important;
}

div[data-testid="stPageLink"] a:hover p,
div[data-testid="stPageLink"] a:hover span,
div[data-testid="stPageLink"] a:hover div {
    color: var(--ai-green-hover) !important;
}

/* Active state via Streamlit aria-current OR explicit marker */
div[data-testid="stPageLink"] a[aria-current="page"],
div[data-testid="element-container"]:has(.ai-nav-active-marker) + div[data-testid="element-container"] div[data-testid="stPageLink"] a,
div[data-testid="stElementContainer"]:has(.ai-nav-active-marker) + div[data-testid="stElementContainer"] div[data-testid="stPageLink"] a {
    background-color: var(--ai-green-soft) !important;
    border: 1.5px solid var(--ai-green) !important;
    box-shadow: 0 2px 6px rgba(8, 127, 103, 0.12) !important;
}

div[data-testid="stPageLink"] a[aria-current="page"] p,
div[data-testid="stPageLink"] a[aria-current="page"] span,
div[data-testid="stPageLink"] a[aria-current="page"] div,
div[data-testid="element-container"]:has(.ai-nav-active-marker) + div[data-testid="element-container"] div[data-testid="stPageLink"] a p,
div[data-testid="element-container"]:has(.ai-nav-active-marker) + div[data-testid="element-container"] div[data-testid="stPageLink"] a span,
div[data-testid="element-container"]:has(.ai-nav-active-marker) + div[data-testid="element-container"] div[data-testid="stPageLink"] a div,
div[data-testid="stElementContainer"]:has(.ai-nav-active-marker) + div[data-testid="stElementContainer"] div[data-testid="stPageLink"] a p,
div[data-testid="stElementContainer"]:has(.ai-nav-active-marker) + div[data-testid="stElementContainer"] div[data-testid="stPageLink"] a span,
div[data-testid="stElementContainer"]:has(.ai-nav-active-marker) + div[data-testid="stElementContainer"] div[data-testid="stPageLink"] a div {
    color: var(--ai-green-hover) !important;
    font-weight: 700 !important;
}

/* Planned navigation pills (until upcoming page file is created) */
.ai-nav-pill-planned {
    width: 100%;
    min-height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    padding: 0.45rem 0.75rem;
    background-color: #f8fafc;
    border: 1px dashed var(--ai-border-strong);
    border-radius: 10px;
    color: var(--ai-muted);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: default;
}

.ai-nav-soon-tag {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: #e2e8f0;
    color: #334155;
    border-radius: 999px;
    padding: 1px 6px;
}

/* Consistent Page Header */
.ai-page-header {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 14px;
    padding: 1.15rem 1.35rem;
    margin: 0.35rem 0 1.15rem 0;
    box-shadow: 0 2px 8px rgba(15, 37, 68, 0.035);
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}

.ai-page-header-main {
    flex: 1 1 420px;
    min-width: 0;
}

.ai-page-eyebrow {
    font-size: 0.72rem;
    font-weight: 750;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ai-green);
    margin-bottom: 0.25rem;
}

.ai-page-title {
    font-size: 1.65rem;
    font-weight: 750;
    color: var(--ai-navy);
    letter-spacing: -0.025em;
    line-height: 1.2;
    margin: 0;
}

.ai-page-desc {
    font-size: 0.92rem;
    color: var(--ai-muted);
    margin: 0.35rem 0 0 0;
    line-height: 1.45;
}

.ai-page-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    justify-content: flex-end;
    padding-top: 0.15rem;
}

.ai-period-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.28rem 0.68rem;
    border-radius: 999px;
    background: var(--ai-surface-subtle);
    border: 1px solid var(--ai-border);
    color: var(--ai-navy);
    font-size: 0.78rem;
    font-weight: 600;
}

/* Status badges */
.ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.26rem 0.65rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 650;
    line-height: 1.2;
    border: 1px solid transparent;
    white-space: nowrap;
}

.ai-badge-dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    flex-shrink: 0;
}

/* Section Headers */
.ai-section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
    margin: 0.9rem 0 0.65rem 0;
    flex-wrap: wrap;
}

.ai-section-header.compact {
    margin: 0 0 0.65rem 0;
}

.ai-section-title {
    font-size: 1.08rem;
    font-weight: 700;
    color: var(--ai-navy);
    letter-spacing: -0.015em;
    line-height: 1.25;
}

.ai-section-subtitle {
    font-size: 0.84rem;
    color: var(--ai-muted);
    margin-top: 2px;
    line-height: 1.4;
}

/* Reusable KPI Cards */
.ai-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 0.85rem;
    margin-bottom: 1rem;
}

.ai-kpi-card {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow: 0 2px 8px rgba(15, 37, 68, 0.035);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 112px;
}

.ai-kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.ai-kpi-label {
    font-size: 0.8rem;
    font-weight: 650;
    color: var(--ai-muted);
}

.ai-kpi-icon {
    font-size: 1rem;
    line-height: 1;
}

.ai-kpi-value {
    font-size: 1.65rem;
    font-weight: 750;
    color: var(--ai-navy);
    letter-spacing: -0.025em;
    font-variant-numeric: tabular-nums;
    margin: 0.42rem 0 0.35rem 0;
    line-height: 1.15;
}

.ai-kpi-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
    flex-wrap: wrap;
}

.ai-kpi-caption {
    font-size: 0.76rem;
    color: var(--ai-muted);
}

/* Insight & Empty State Cards */
.ai-insight-card {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-left-width: 4px;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.65rem;
    box-shadow: 0 1px 4px rgba(15, 37, 68, 0.03);
}

.ai-insight-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
    flex-wrap: wrap;
}

.ai-insight-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--ai-navy);
}

.ai-insight-body {
    font-size: 0.86rem;
    color: var(--ai-body);
    line-height: 1.48;
}

.ai-empty-state {
    background: var(--ai-surface);
    border: 1px dashed var(--ai-border-strong);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
    margin: 0.5rem 0;
}

.ai-empty-title {
    font-size: 0.96rem;
    font-weight: 700;
    color: var(--ai-navy);
    margin-bottom: 0.25rem;
}

.ai-empty-msg {
    font-size: 0.86rem;
    color: var(--ai-muted);
}

/* Native Streamlit Metric Cards */
div[data-testid="stMetric"] {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 2px 8px rgba(15, 37, 68, 0.035);
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] label {
    color: var(--ai-muted) !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
}

div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] div {
    color: var(--ai-navy) !important;
    font-weight: 750 !important;
    font-variant-numeric: tabular-nums;
}

/* Native Containers / Chart Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border) !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 8px rgba(15, 37, 68, 0.03);
}

/* Buttons (secondary + primary with preserved white label) */
.stButton > button,
button[data-testid="stBaseButton-secondary"],
div[data-testid="stDownloadButton"] > button {
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border-strong) !important;
    border-radius: 9px !important;
    color: var(--ai-text) !important;
    font-weight: 600 !important;
}

.stButton > button p,
.stButton > button span,
button[data-testid="stBaseButton-secondary"] p,
button[data-testid="stBaseButton-secondary"] span {
    color: var(--ai-text) !important;
}

.stButton > button:hover,
button[data-testid="stBaseButton-secondary"]:hover {
    background-color: #f0f8f5 !important;
    border-color: var(--ai-green) !important;
    color: var(--ai-green-hover) !important;
}

.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: var(--ai-green) !important;
    border-color: var(--ai-green) !important;
    color: #ffffff !important;
}

.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] span,
div[data-testid="stFormSubmitButton"] button[kind="primary"] p,
div[data-testid="stFormSubmitButton"] button[kind="primary"] span {
    color: #ffffff !important;
}

.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    background-color: var(--ai-green-hover) !important;
    border-color: var(--ai-green-hover) !important;
}

/* Selectboxes, Inputs, Textareas, and Dropdown Popovers */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
    background-color: var(--ai-surface) !important;
    border-color: var(--ai-border-strong) !important;
    border-radius: 9px !important;
    color: var(--ai-navy) !important;
}

div[data-baseweb="select"] span,
div[data-baseweb="select"] div,
div[data-baseweb="select"] input,
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    color: var(--ai-navy) !important;
    -webkit-text-fill-color: var(--ai-navy) !important;
}

div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
}

div[data-baseweb="select"] svg {
    fill: var(--ai-muted) !important;
    color: var(--ai-muted) !important;
}

div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[data-testid="stSelectboxVirtualDropdown"],
ul[role="listbox"] {
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border) !important;
    color: var(--ai-text) !important;
}

ul[role="listbox"] li,
li[role="option"],
li[role="option"] span,
li[role="option"] div {
    color: var(--ai-text) !important;
    background-color: var(--ai-surface) !important;
}

li[role="option"]:hover,
li[role="option"][aria-selected="true"] {
    background-color: var(--ai-green-soft) !important;
    color: var(--ai-green-hover) !important;
}

/* Expanders */
div[data-testid="stExpander"] {
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border) !important;
    border-radius: 12px !important;
    overflow: hidden;
}

div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] summary svg {
    color: var(--ai-navy) !important;
    fill: var(--ai-navy) !important;
    font-weight: 600 !important;
}

/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 11px !important;
}

div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span,
div[data-testid="stAlert"] div {
    color: var(--ai-text) !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: var(--ai-muted) !important;
    font-weight: 600 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--ai-green-hover) !important;
}

/* DataFrames & Charts */
div[data-testid="stDataFrame"] {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 12px;
    overflow: hidden;
}

div[data-testid="stVegaLiteChart"],
div[data-testid="stArrowVegaLiteChart"] {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 12px;
    padding: 12px;
}

hr {
    border-color: var(--ai-border) !important;
    margin: 1.1rem 0 !important;
}

/* Responsive behavior */
@media (max-width: 992px) {
    .main .block-container {
        padding-left: 1.15rem;
        padding-right: 1.15rem;
    }

    .ai-page-title {
        font-size: 1.4rem;
    }
}

@media (max-width: 640px) {
    .main .block-container {
        padding-left: 0.75rem;
        padding-right: 0.75rem;
        padding-top: 0.75rem;
    }

    .ai-page-header {
        padding: 0.95rem 1rem;
    }

    .ai-user-chip {
        margin-left: 0;
    }

    .ai-kpi-grid {
        grid-template-columns: 1fr;
    }
}
</style>
        """
    )


def status_badge_html(label: str, tone: str = "neutral") -> str:
    """Return HTML for a consistent, accessible status badge."""
    palette = _get_tone(tone)
    return (
        f'<span class="ai-badge" style="background:{palette["bg"]};'
        f'border-color:{palette["border"]};color:{palette["text"]};">'
        f'<span class="ai-badge-dot" style="background:{palette["dot"]};"></span>'
        f"{_escape(label)}</span>"
    )


def render_status_badge(label: str, tone: str = "neutral") -> None:
    """Render a consistent status badge."""
    _render_html(status_badge_html(label, tone=tone))


def _render_nav_item(
    label: str,
    page_path: Optional[str],
    icon: str,
    is_active: bool = False,
) -> None:
    """Render a live page link when available, or a safe planned pill otherwise."""
    if _page_exists(page_path):
        if is_active:
            _render_html('<span class="ai-nav-active-marker"></span>')
        st.page_link(page_path, label=label, icon=icon)
        return

    _render_html(
        f'<div class="ai-nav-pill-planned" title="Available in a subsequent milestone">'
        f'<span>{_escape(icon)}</span>'
        f'<span>{_escape(label)}</span>'
        f'<span class="ai-nav-soon-tag">Planned</span>'
        f"</div>"
    )


def render_header(
    active_page: str = "Portfolio",
    active_section: str = "Today",
    user_name: str = "Executive Studio",
    user_role: str = "Portfolio Lead",
    user_initials: str = "ES",
) -> None:
    """Render the AI Studio top navigation bar and data domain selector."""
    brand_col, nav_col, profile_col = st.columns([2.2, 2.5, 1.3])

    with brand_col:
        _render_html(
            '<div class="ai-brand">'
            '<div class="ai-brand-mark">◈</div>'
            "<div>"
            '<div class="ai-brand-title">Property Intelligence</div>'
            '<div class="ai-brand-subtitle">AI Studio · Enterprise Data Intelligence Platform</div>'
            "</div>"
            "</div>"
        )

    with nav_col:
        nav_cols = st.columns(len(TOP_NAV_ITEMS))
        for col, (label, path, icon) in zip(nav_cols, TOP_NAV_ITEMS):
            with col:
                _render_nav_item(
                    label=label,
                    page_path=path,
                    icon=icon,
                    is_active=(active_section == label),
                )

    with profile_col:
        _render_html(
            '<div class="ai-user-chip">'
            f'<div class="ai-user-avatar">{_escape(user_initials)}</div>'
            '<div class="ai-user-meta">'
            f'<span class="ai-user-name">{_escape(user_name)}</span>'
            f'<span class="ai-user-role">{_escape(user_role)}</span>'
            "</div>"
            "</div>"
        )

    _render_html('<div class="ai-hairline"></div>')

    _render_html(
        '<div class="ai-domain-row-header">'
        '<div class="ai-domain-label">DATA DOMAIN</div>'
        "</div>"
    )

    domain_cols = st.columns(len(DOMAIN_NAV_ITEMS))
    for col, (label, path, icon) in zip(domain_cols, DOMAIN_NAV_ITEMS):
        with col:
            _render_nav_item(
                label=label,
                page_path=path,
                icon=icon,
                is_active=(active_page == label),
            )

    _render_html('<div class="ai-hairline"></div>')


def render_page_header(
    title: str,
    description: str = "",
    domain_label: Optional[str] = None,
    reporting_period: Optional[str] = None,
    status_text: Optional[str] = None,
    status_tone: str = "success",
) -> None:
    """Render a consistent enterprise page header with optional period and status."""
    eyebrow_html = (
        f'<div class="ai-page-eyebrow">{_escape(domain_label)}</div>'
        if domain_label
        else ""
    )
    desc_html = (
        f'<p class="ai-page-desc">{_escape(description)}</p>'
        if description
        else ""
    )

    meta_parts = []
    if reporting_period:
        meta_parts.append(
            f'<span class="ai-period-pill">Reporting Period: {_escape(reporting_period)}</span>'
        )
    if status_text:
        meta_parts.append(status_badge_html(status_text, tone=status_tone))

    meta_html = (
        f'<div class="ai-page-meta">{"".join(meta_parts)}</div>'
        if meta_parts
        else ""
    )

    _render_html(
        '<div class="ai-page-header">'
        '<div class="ai-page-header-main">'
        f"{eyebrow_html}"
        f'<h1 class="ai-page-title">{_escape(title)}</h1>'
        f"{desc_html}"
        "</div>"
        f"{meta_html}"
        "</div>"
    )


def render_section_header(
    title: str,
    subtitle: Optional[str] = None,
    badge: Optional[str] = None,
    badge_tone: str = "neutral",
    compact: bool = False,
) -> None:
    """Render a reusable section heading with optional subtitle and badge."""
    sub_html = (
        f'<div class="ai-section-subtitle">{_escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    badge_html = status_badge_html(badge, tone=badge_tone) if badge else ""
    compact_cls = " compact" if compact else ""

    _render_html(
        f'<div class="ai-section-header{compact_cls}">'
        "<div>"
        f'<div class="ai-section-title">{_escape(title)}</div>'
        f"{sub_html}"
        "</div>"
        f"{badge_html}"
        "</div>"
    )


def kpi_card_html(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_tone: str = "neutral",
    caption: Optional[str] = None,
    icon: Optional[str] = None,
) -> str:
    """Build HTML for a single enterprise KPI card."""
    icon_html = f'<span class="ai-kpi-icon">{_escape(icon)}</span>' if icon else ""
    delta_html = status_badge_html(delta, tone=delta_tone) if delta else ""
    caption_html = (
        f'<span class="ai-kpi-caption">{_escape(caption)}</span>'
        if caption
        else ""
    )
    footer_html = (
        f'<div class="ai-kpi-footer">{delta_html}{caption_html}</div>'
        if (delta_html or caption_html)
        else ""
    )

    return (
        '<div class="ai-kpi-card">'
        '<div class="ai-kpi-top">'
        f'<span class="ai-kpi-label">{_escape(label)}</span>'
        f"{icon_html}"
        "</div>"
        f'<div class="ai-kpi-value">{_escape(value)}</div>'
        f"{footer_html}"
        "</div>"
    )


def render_kpi_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_tone: str = "neutral",
    caption: Optional[str] = None,
    icon: Optional[str] = None,
) -> None:
    """Render a single KPI card inside any Streamlit layout container."""
    _render_html(
        kpi_card_html(
            label=label,
            value=value,
            delta=delta,
            delta_tone=delta_tone,
            caption=caption,
            icon=icon,
        )
    )


def render_kpi_row(cards: Iterable[Mapping[str, object]]) -> None:
    """Render a responsive grid of KPI cards from a sequence of card dictionaries."""
    card_markup = "".join(
        kpi_card_html(
            label=str(card.get("label", "")),
            value=str(card.get("value", "")),
            delta=card.get("delta"),
            delta_tone=str(card.get("delta_tone", "neutral")),
            caption=card.get("caption"),
            icon=card.get("icon"),
        )
        for card in cards
    )
    _render_html(f'<div class="ai-kpi-grid">{card_markup}</div>')


@contextmanager
def chart_card(
    title: str,
    subtitle: Optional[str] = None,
    badge: Optional[str] = None,
    badge_tone: str = "neutral",
):
    """Context manager wrapping charts or tables inside a styled AI Studio card."""
    with st.container(border=True):
        render_section_header(
            title=title,
            subtitle=subtitle,
            badge=badge,
            badge_tone=badge_tone,
            compact=True,
        )
        yield


def render_insight_card(
    title: str,
    body: str,
    tone: str = "info",
    tag: Optional[str] = None,
) -> None:
    """Render a calculated insight or recommendation card with semantic accent."""
    palette = _get_tone(tone)
    tag_html = status_badge_html(tag, tone=tone) if tag else ""

    _render_html(
        f'<div class="ai-insight-card" style="border-left-color:{palette["accent"]};">'
        '<div class="ai-insight-head">'
        f'<div class="ai-insight-title">{_escape(title)}</div>'
        f"{tag_html}"
        "</div>"
        f'<div class="ai-insight-body">{_escape(body)}</div>'
        "</div>"
    )


def render_empty_state(title: str, message: str, tone: str = "neutral") -> None:
    """Render an accessible empty or informational state panel."""
    badge_html = status_badge_html("Notice", tone=tone)
    _render_html(
        '<div class="ai-empty-state">'
        f'<div style="margin-bottom:0.45rem;">{badge_html}</div>'
        f'<div class="ai-empty-title">{_escape(title)}</div>'
        f'<div class="ai-empty-msg">{_escape(message)}</div>'
        "</div>"
    )


def pct_change(current: float, previous: float) -> Optional[float]:
    """Compute percentage change safely when previous value is non-zero."""
    if not previous:
        return None
    return ((current - previous) / abs(previous)) * 100.0


def render_formatted_table(
    df: pd.DataFrame,
    column_labels: Mapping[str, str],
    formats: Mapping[str, str],
) -> None:
    """Rename selected columns, apply display formatting, and render a dataframe."""
    renamed = df[list(column_labels.keys())].rename(columns=column_labels)
    try:
        styled = renamed.style.format(formats)
        st.dataframe(styled, use_container_width=True, hide_index=True)
    except (AttributeError, ImportError):
        formatted = renamed.copy()
        for col, fmt in formats.items():
            if col in formatted.columns:
                formatted[col] = formatted[col].map(
                    lambda val: fmt.format(val) if pd.notna(val) else "—"
                )
        st.dataframe(formatted, use_container_width=True, hide_index=True)

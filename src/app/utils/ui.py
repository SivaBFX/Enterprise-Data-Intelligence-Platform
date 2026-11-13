"""Shared AI Studio UI design system and reusable components."""

from contextlib import contextmanager
import html
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd
import streamlit as st

APP_ROOT = Path(__file__).resolve().parent.parent

# Centralized tone palette for status badges, KPI deltas, and insight cards.
TONE_STYLES = {
    "success": {
        "bg": "#e7f5ee",
        "border": "#a7dcc0",
        "text": "#0b5e42",
        "dot": "#0c6b53",
        "accent": "#0c6b53",
    },
    "warning": {
        "bg": "#fef6e5",
        "border": "#f4ce82",
        "text": "#8a4b08",
        "dot": "#d97706",
        "accent": "#d97706",
    },
    "danger": {
        "bg": "#fef0f0",
        "border": "#f8baba",
        "text": "#9b1c1c",
        "dot": "#dc2626",
        "accent": "#dc2626",
    },
    "info": {
        "bg": "#eef5ff",
        "border": "#bfd7fe",
        "text": "#1e40af",
        "dot": "#2563eb",
        "accent": "#2563eb",
    },
    "neutral": {
        "bg": "#f1f3f6",
        "border": "#d6dbe3",
        "text": "#374151",
        "dot": "#6b7280",
        "accent": "#6b7280",
    },
}

SIDEBAR_NAV_GROUPS = [
    {
        "group": "OVERVIEW",
        "items": [
            ("Executive Overview", "app.py", ":material/dashboard:"),
        ],
    },
    {
        "group": "PORTFOLIO INTELLIGENCE",
        "items": [
            ("Property Intelligence", "pages/02_Property_Intelligence.py", ":material/apartment:"),
            ("Market Intelligence", "pages/03_Market_Intelligence.py", ":material/public:"),
            ("Maintenance Intelligence", "pages/04_Maintenance_Intelligence.py", ":material/build:"),
            ("Investment & CapEx", "pages/05_Investment_CapEx.py", ":material/account_balance:"),
        ],
    },
    {
        "group": "ANALYTICS & AI",
        "items": [
            ("Performance Analytics", "pages/06_Performance_Analytics.py", ":material/insights:"),
            ("AI Business Assistant", "pages/07_AI_Business_Assistant.py", ":material/auto_awesome:"),
        ],
    },
    {
        "group": "SYSTEM & HEALTH",
        "items": [
            ("Data & Platform Health", "pages/08_Data_Platform_Health.py", ":material/health_and_safety:"),
        ],
    },
]

ALL_SAAS_PAGES = [item for group in SIDEBAR_NAV_GROUPS for item in group["items"]]

TOP_NAV_ITEMS = [
    ("Executive Overview", "app.py", ":material/dashboard:"),
    ("Performance Analytics", "pages/06_Performance_Analytics.py", ":material/insights:"),
    ("Data & Platform Health", "pages/08_Data_Platform_Health.py", ":material/health_and_safety:"),
]

DOMAIN_NAV_ITEMS = [
    ("Executive Overview", "app.py", ":material/dashboard:"),
    ("Property Intelligence", "pages/02_Property_Intelligence.py", ":material/apartment:"),
    ("Market Intelligence", "pages/03_Market_Intelligence.py", ":material/public:"),
    ("Maintenance Intelligence", "pages/04_Maintenance_Intelligence.py", ":material/build:"),
    ("Investment & CapEx", "pages/05_Investment_CapEx.py", ":material/account_balance:"),
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
    """Inject the AI Studio light theme stylesheet with zero header overlap."""
    _render_html(
        """
<style>
:root {
    --saas-sidebar: #172433;
    --saas-sidebar-border: #223348;
    --saas-sidebar-hover: #1E2F42;
    --saas-sidebar-active: #1E2F42;
    --saas-sidebar-text: #8C9BAE;
    --saas-sidebar-text-hover: #FFFFFF;
    --saas-bg: #F5F7FA;
    --saas-card: #FFFFFF;
    --saas-border: #E5EAF0;
    --saas-border-strong: #D1D9E2;
    --saas-text-primary: #202B38;
    --saas-text-secondary: #758294;
    --saas-green: #119B78;
    --saas-green-hover: #0E8264;
    --saas-blue: #3478D4;
    --saas-warning: #E9A23B;
    --saas-critical: #DC5656;
    --ai-bg: #F5F7FA;
    --ai-surface: #FFFFFF;
    --ai-surface-subtle: #F1F4F8;
    --ai-border: #E5EAF0;
    --ai-border-strong: #D1D9E2;
    --ai-navy: #202B38;
    --ai-text: #202B38;
    --ai-body: #374151;
    --ai-muted: #758294;
    --ai-green: #119B78;
    --ai-green-hover: #0E8264;
    --ai-green-soft: #E7F5EE;
    --ai-green-border: #A7DCC0;
    --text-color: #202B38;
    --background-color: #F5F7FA;
    --secondary-background-color: #FFFFFF;
    --primary-color: #119B78;
}

/* Base canvas and typography */
html, body, .stApp,
div[data-testid="stAppViewContainer"],
div[data-testid="stMain"] {
    background-color: var(--ai-bg) !important;
    color: var(--ai-text) !important;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
}

/* Prevent Streamlit top toolbar from overlapping the custom app header */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 2.25rem !important;
    pointer-events: none;
}

header[data-testid="stHeader"] * {
    pointer-events: auto;
}

header[data-testid="stHeader"] svg,
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] span {
    color: var(--ai-muted) !important;
}

.main .block-container,
div[data-testid="stMainBlockContainer"],
.stMainBlockContainer {
    max-width: 1440px !important;
    padding-top: 3.75rem !important;
    padding-bottom: 3rem !important;
    padding-left: 1.75rem !important;
    padding-right: 1.75rem !important;
}

/* Dark Navy Enterprise SaaS Sidebar */
section[data-testid="stSidebar"] {
    background-color: #172433 !important;
    border-right: 1px solid #223348 !important;
}

/* Eliminate the empty gap at the top of the sidebar */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

header[data-testid="stSidebarHeader"],
div[data-testid="stSidebarHeader"] {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    background-color: #172433 !important;
    height: 1.75rem !important;
    min-height: 1.75rem !important;
    padding: 0.2rem 0.65rem 0 0.65rem !important;
    margin: 0 !important;
}

section[data-testid="stSidebar"] > div:first-child,
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
    background-color: #172433 !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stSidebarCollapseButton"] button {
    color: #8C9BAE !important;
}

/* Sidebar branding header */
.saas-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.2rem 0.35rem 0.85rem 0.35rem;
    border-bottom: 1px solid #243548;
    margin-bottom: 0.75rem;
}

.saas-brand-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #119B78;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(17, 155, 120, 0.3);
    flex-shrink: 0;
}

.saas-brand-title {
    color: #FFFFFF;
    font-size: 0.92rem;
    font-weight: 750;
    line-height: 1.2;
    letter-spacing: -0.01em;
}

.saas-brand-subtitle {
    color: #8C9BAE;
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Nav group labels */
.saas-nav-group-label {
    color: #64748B;
    font-size: 0.66rem;
    font-weight: 750;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.75rem 0.5rem 0.25rem 0.5rem;
    margin-top: 0.15rem;
}

/* Sidebar navigation links */
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a {
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    padding: 0.42rem 0.75rem !important;
    min-height: 36px !important;
    color: #94A3B8 !important;
    text-decoration: none !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    transition: all 0.15s ease !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a p,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a span {
    color: #94A3B8 !important;
    font-weight: 550 !important;
    font-size: 0.83rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover {
    background-color: #1E2F42 !important;
    border-color: #273B52 !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover p,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover span {
    color: #FFFFFF !important;
}

/* Active page link in sidebar */
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] {
    background-color: #1E2F42 !important;
    border: 1px solid #2B3F56 !important;
    border-left: 3px solid #119B78 !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] p,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] span {
    color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* Bottom user profile */
.saas-sidebar-profile {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 0.65rem 0.6rem;
    background: #101B27;
    border: 1px solid #223348;
    border-radius: 10px;
    margin-top: 1.25rem;
}

.saas-profile-avatar {
    width: 32px;
    height: 32px;
    border-radius: 999px;
    background: #243548;
    color: #FFFFFF;
    font-size: 0.74rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.saas-profile-name {
    color: #FFFFFF;
    font-size: 0.78rem;
    font-weight: 650;
    line-height: 1.2;
}

.saas-profile-role {
    color: #758294;
    font-size: 0.68rem;
    line-height: 1.2;
}

.saas-profile-badge {
    font-size: 0.62rem;
    font-weight: 700;
    color: #119B78;
    background: rgba(17, 155, 120, 0.15);
    padding: 2px 6px;
    border-radius: 999px;
    text-transform: uppercase;
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
    font-size: 0.82em;
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
    font-size: 0.82rem !important;
}

/* Top header brand & profile avatar */
.ai-brand {
    display: flex;
    align-items: center;
    gap: 11px;
    min-height: 40px;
}

.ai-brand-mark {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: var(--ai-green);
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 700;
    flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(12, 107, 83, 0.22);
}

.ai-brand-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--ai-navy);
    line-height: 1.15;
    letter-spacing: -0.02em;
}

.ai-brand-subtitle {
    font-size: 0.74rem;
    font-weight: 500;
    color: var(--ai-muted);
    margin-top: 1px;
}

.ai-user-chip {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 9px;
    padding: 2px 4px;
    margin-left: auto;
    width: fit-content;
}

.ai-user-avatar {
    width: 34px;
    height: 34px;
    border-radius: 999px;
    background: var(--ai-navy);
    color: #ffffff;
    font-size: 0.76rem;
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
    text-align: right;
}

.ai-user-name {
    font-size: 0.78rem;
    font-weight: 650;
    color: var(--ai-navy);
}

.ai-user-role {
    font-size: 0.69rem;
    color: var(--ai-muted);
}

.ai-hairline {
    border-top: 1px solid var(--ai-border);
    margin: 0.5rem 0 0.6rem 0;
}

.ai-domain-inline-label {
    color: var(--ai-muted);
    font-size: 0.76rem;
    font-weight: 600;
    min-height: 36px;
    display: flex;
    align-items: center;
    white-space: nowrap;
}

/* Anchors for crisp baseline-aligned navigation rows */
.ai-nav-anchor {
    display: none;
}

div[data-testid="stPageLink"] {
    width: 100%;
}

/* Top workspace navigation: sleek minimalist borderless tabs */
div[data-testid="stVerticalBlock"]:has(#ai-topnav-anchor) div[data-testid="stHorizontalBlock"] div[data-testid="stPageLink"] a {
    width: 100% !important;
    min-height: 36px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0.32rem 0.7rem !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    text-decoration: none !important;
    transition: background-color 0.15s ease, color 0.15s ease;
}

div[data-testid="stVerticalBlock"]:has(#ai-topnav-anchor) div[data-testid="stHorizontalBlock"] div[data-testid="stPageLink"] a p,
div[data-testid="stVerticalBlock"]:has(#ai-topnav-anchor) div[data-testid="stHorizontalBlock"] div[data-testid="stPageLink"] a span {
    color: var(--ai-body) !important;
    font-weight: 550 !important;
    font-size: 0.86rem !important;
}

div[data-testid="stVerticalBlock"]:has(#ai-topnav-anchor) div[data-testid="stHorizontalBlock"] div[data-testid="stPageLink"] a:hover {
    background-color: #eceff4 !important;
    border-color: transparent !important;
}

/* Domain navigation & general page links: clean borderless pills with elevated active pill */
div[data-testid="stPageLink"] a {
    width: 100% !important;
    min-height: 34px;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px;
    padding: 0.3rem 0.72rem !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    color: var(--ai-body) !important;
    text-decoration: none !important;
    box-shadow: none !important;
    transition: all 0.15s ease;
}

div[data-testid="stPageLink"] a p,
div[data-testid="stPageLink"] a span,
div[data-testid="stPageLink"] a div {
    color: var(--ai-body) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    white-space: nowrap !important;
}

div[data-testid="stPageLink"] a:hover {
    background-color: #eceff4 !important;
    border-color: transparent !important;
}

div[data-testid="stPageLink"] a:hover p,
div[data-testid="stPageLink"] a:hover span {
    color: var(--ai-navy) !important;
}

div[data-testid="stPageLink"] a[aria-current="page"] {
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border) !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06) !important;
}

div[data-testid="stPageLink"] a[aria-current="page"] p,
div[data-testid="stPageLink"] a[aria-current="page"] span,
div[data-testid="stPageLink"] a[aria-current="page"] div {
    color: var(--ai-navy) !important;
    font-weight: 700 !important;
}

/* Planned navigation pills fallback */
.ai-nav-pill-planned {
    width: 100%;
    min-height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 0.32rem 0.7rem;
    background-color: #f8fafc;
    border: 1px dashed var(--ai-border-strong);
    border-radius: 9px;
    color: var(--ai-muted);
    font-size: 0.82rem;
    font-weight: 600;
}

.ai-nav-soon-tag {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: #e5e7eb;
    color: #374151;
    border-radius: 999px;
    padding: 1px 6px;
}

/* Consistent Page Header */
.ai-page-header {
    background: transparent;
    padding: 0.25rem 0 0.85rem 0;
    margin: 0.15rem 0 0.45rem 0;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
}

.ai-page-header-main {
    flex: 1 1 460px;
    min-width: 0;
}

.ai-page-eyebrow {
    font-size: 0.72rem;
    font-weight: 750;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--ai-green);
    margin-bottom: 0.2rem;
}

.ai-page-title {
    font-size: 1.75rem;
    font-weight: 750;
    color: var(--ai-navy);
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin: 0;
}

.ai-page-desc {
    font-size: 0.9rem;
    color: var(--ai-muted);
    margin: 0.32rem 0 0 0;
    line-height: 1.45;
}

.ai-page-meta {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
    justify-content: flex-end;
    padding-top: 0.2rem;
}

.ai-period-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    color: var(--ai-body);
    font-size: 0.75rem;
    font-weight: 600;
}

/* Status badges */
.ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0.22rem 0.58rem;
    border-radius: 999px;
    font-size: 0.73rem;
    font-weight: 650;
    line-height: 1.2;
    border: 1px solid transparent;
    white-space: nowrap;
}

.ai-badge-dot {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    flex-shrink: 0;
}

/* Section Headers */
.ai-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin: 1rem 0 0.6rem 0;
    flex-wrap: wrap;
}

.ai-section-header.compact {
    margin: 0 0 0.6rem 0;
}

.ai-section-title {
    font-size: 0.96rem;
    font-weight: 700;
    color: var(--ai-navy);
    letter-spacing: -0.01em;
    line-height: 1.25;
}

.ai-section-subtitle {
    font-size: 0.8rem;
    color: var(--ai-muted);
    margin-top: 2px;
    line-height: 1.38;
}

.ai-micro-label {
    font-size: 0.71rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ai-muted);
}

/* Reusable KPI Cards (AI Studio style) */
.ai-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(205px, 1fr));
    gap: 0.85rem;
    margin-bottom: 1.1rem;
}

.ai-kpi-card {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 14px;
    padding: 0.95rem 1.05rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 122px;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.ai-kpi-card:hover {
    border-color: var(--ai-border-strong);
    box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
}

.ai-kpi-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.45rem;
}

.ai-kpi-label {
    font-size: 0.79rem;
    font-weight: 600;
    color: var(--ai-body);
}

.ai-kpi-icon {
    font-size: 0.95rem;
    line-height: 1;
}

.ai-kpi-value {
    font-size: 1.68rem;
    font-weight: 750;
    color: var(--ai-navy);
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
    margin: 0.35rem 0 0.3rem 0;
    line-height: 1.12;
}

.ai-kpi-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
    flex-wrap: wrap;
}

.ai-kpi-caption {
    font-size: 0.74rem;
    color: var(--ai-muted);
    line-height: 1.3;
}

.ai-kpi-source {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.68rem;
    color: var(--ai-muted);
    margin-top: 0.35rem;
    padding-top: 0.3rem;
    border-top: 1px solid #f1f3f6;
}

/* Decision Queue & Sub-tiles */
.ai-stat-tile {
    background: var(--ai-surface-subtle);
    border: 1px solid var(--ai-border);
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
}

.ai-stat-tile.tone-warning {
    background: #fef6e5;
    border-color: #f4ce82;
}

.ai-stat-tile.tone-success {
    background: #e7f5ee;
    border-color: #a7dcc0;
}

.ai-stat-tile-label {
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--ai-muted);
    margin-bottom: 0.2rem;
}

.ai-stat-tile-value {
    font-size: 0.86rem;
    font-weight: 700;
    color: var(--ai-navy);
    line-height: 1.3;
}

/* Insight & Empty State Cards */
.ai-insight-card {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-left-width: 4px;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

.ai-insight-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
    flex-wrap: wrap;
}

.ai-insight-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--ai-navy);
}

.ai-insight-body {
    font-size: 0.83rem;
    color: var(--ai-body);
    line-height: 1.46;
}

.ai-empty-state {
    background: var(--ai-surface);
    border: 1px dashed var(--ai-border-strong);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    margin: 0.5rem 0;
}

.ai-empty-title {
    font-size: 0.94rem;
    font-weight: 700;
    color: var(--ai-navy);
    margin-bottom: 0.2rem;
}

.ai-empty-msg {
    font-size: 0.84rem;
    color: var(--ai-muted);
}

/* Native Streamlit Metric Cards */
div[data-testid="stMetric"] {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 14px;
    padding: 15px 17px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] label {
    color: var(--ai-muted) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
}

div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] div {
    color: var(--ai-navy) !important;
    font-weight: 750 !important;
    font-variant-numeric: tabular-nums;
}

/* Only round explicit bordered containers without forcing borders onto every column */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px;
}

/* Buttons: polished pill/rounded styling with crisp contrast */
.stButton > button,
button[data-testid="stBaseButton-secondary"],
div[data-testid="stDownloadButton"] > button {
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border-strong) !important;
    border-radius: 10px !important;
    color: var(--ai-navy) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    min-height: 38px !important;
    padding: 0.35rem 0.9rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    transition: all 0.15s ease;
}

.stButton > button p,
.stButton > button span,
button[data-testid="stBaseButton-secondary"] p,
button[data-testid="stBaseButton-secondary"] span,
div[data-testid="stDownloadButton"] > button p,
div[data-testid="stDownloadButton"] > button span {
    color: var(--ai-navy) !important;
}

.stButton > button:hover,
button[data-testid="stBaseButton-secondary"]:hover,
div[data-testid="stDownloadButton"] > button:hover {
    background-color: #f3f6f9 !important;
    border-color: #9ca3af !important;
    color: var(--ai-navy) !important;
}

.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: var(--ai-green) !important;
    border: 1px solid var(--ai-green) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-weight: 650 !important;
    min-height: 38px !important;
    box-shadow: 0 1px 3px rgba(12, 107, 83, 0.2);
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
button[data-testid="stBaseButton-primary"]:hover,
div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
    background-color: var(--ai-green-hover) !important;
    border-color: var(--ai-green-hover) !important;
}

/* Selectboxes, Inputs, Textareas, and Dropdown Popovers */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
    background-color: var(--ai-surface) !important;
    border-color: var(--ai-border-strong) !important;
    border-radius: 10px !important;
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
    color: #6b7280 !important;
    -webkit-text-fill-color: #6b7280 !important;
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
    font-size: 0.85rem !important;
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
    padding: 10px;
}

hr {
    border-color: var(--ai-border) !important;
    margin: 0.9rem 0 !important;
}

/* Responsive behavior */
@media (max-width: 992px) {
    .main .block-container,
    div[data-testid="stMainBlockContainer"],
    .stMainBlockContainer {
        padding-left: 1.15rem !important;
        padding-right: 1.15rem !important;
    }

    .ai-page-title {
        font-size: 1.45rem;
    }
}

@media (max-width: 640px) {
    .main .block-container,
    div[data-testid="stMainBlockContainer"],
    .stMainBlockContainer {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 2.3rem !important;
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
) -> None:
    """Render a baseline-aligned page link when available, or a planned pill otherwise."""
    if _page_exists(page_path):
        st.page_link(page_path, label=label)
        return

    _render_html(
        f'<div class="ai-nav-pill-planned" title="Scheduled in upcoming milestone">'
        f'<span>{_escape(label)}</span>'
        f'<span class="ai-nav-soon-tag">Planned</span>'
        f"</div>"
    )


def render_sidebar(active_page: str = "Executive Overview") -> None:
    """Render the IMMODESK/UnitStack-inspired dark navy sidebar navigation."""
    with st.sidebar:
        _render_html(
            '<div class="saas-sidebar-brand">'
            '<div class="saas-brand-icon">'
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>'
            '<polyline points="9 22 9 12 15 12 15 22"></polyline>'
            '</svg>'
            '</div>'
            '<div>'
            '<div class="saas-brand-title">Property Intelligence</div>'
            '<div class="saas-brand-subtitle">Enterprise SaaS · Databricks</div>'
            '</div>'
            '</div>'
        )

        for group in SIDEBAR_NAV_GROUPS:
            _render_html(f'<div class="saas-nav-group-label">{_escape(group["group"])}</div>')
            for label, path, icon in group["items"]:
                if _page_exists(path):
                    st.page_link(path, label=label, icon=icon)
                else:
                    _render_html(
                        f'<div class="ai-nav-pill-planned" style="background:#1a2838;border-color:#2a3b4e;color:#8c9bae;margin-bottom:4px;">'
                        f'<span>{_escape(label)}</span>'
                        f'<span class="ai-nav-soon-tag" style="background:#243548;color:#94a3b8;">Planned</span>'
                        f'</div>'
                    )

        _render_html(
            '<div class="saas-sidebar-profile">'
            '<div class="saas-profile-avatar">ES</div>'
            '<div style="flex:1;min-width:0;">'
            '<div class="saas-profile-name">Executive Studio</div>'
            '<div class="saas-profile-role">Portfolio Lead · Databricks</div>'
            '</div>'
            '<span class="saas-profile-badge">Live</span>'
            '</div>'
        )


def render_top_navigation(
    breadcrumbs: Optional[List[str]] = None,
    current_page: str = "Executive Overview",
    status_text: Optional[str] = "Gold Layer · Live Sync",
    status_tone: str = "success",
) -> None:
    """Render the crisp SaaS top navigation bar with breadcrumbs and utility controls."""
    crumbs = breadcrumbs or ["Residential Property Intelligence", current_page]
    crumbs_html = " <span style='color:#94A3B8;margin:0 6px;'>/</span> ".join(
        f"<span style='color:#202B38;font-weight:700;'>{_escape(c)}</span>" if i == len(crumbs) - 1
        else f"<span style='color:#758294;'>{_escape(c)}</span>"
        for i, c in enumerate(crumbs)
    )

    home_svg = (
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748B" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'style="margin-right:6px;vertical-align:-2px;">'
        '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>'
        '<polyline points="9 22 9 12 15 12 15 22"></polyline>'
        '</svg>'
    )

    with st.container():
        left_col, right_col = st.columns([2.5, 1.5])
        with left_col:
            _render_html(
                f'<div style="display:flex;align-items:center;min-height:36px;font-size:0.84rem;">'
                f'{home_svg} {crumbs_html}'
                f'</div>'
            )
        with right_col:
            r1, r2 = st.columns([1.5, 1.1])
            with r1:
                if status_text:
                    _render_html(
                        f'<div style="display:flex;align-items:center;justify-content:flex-end;min-height:36px;">'
                        f'{status_badge_html(status_text, tone=status_tone)}'
                        f'</div>'
                    )
            with r2:
                safe_key = "".join(ch if ch.isalnum() else "_" for ch in current_page)
                if st.button("Refresh", key=f"top_refresh_{safe_key}", icon=":material/refresh:", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

    _render_html('<div class="ai-hairline" style="margin:0.25rem 0 0.85rem 0;"></div>')


def render_alert_panel(
    alerts: List[Mapping[str, Any]],
    title: str = "Requires Attention",
    subtitle: str = "Operational and financial exceptions identified from Gold data",
) -> None:
    """Render IMMODESK-style actionable alert panel with severity tags and drill-downs."""
    with st.container(border=True):
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
            f'<div>'
            f'<strong style="font-size:0.95rem;color:#202B38;">{_escape(title)}</strong>'
            f'<div style="font-size:0.78rem;color:#758294;">{_escape(subtitle)}</div>'
            f'</div>'
            f'{status_badge_html(f"{len(alerts)} Active", tone="danger" if alerts else "success")}'
            f'</div>',
            unsafe_allow_html=True,
        )

        if not alerts:
            render_empty_state("All Systems Normal", "No portfolio thresholds or operational exceptions detected.", tone="success")
            return

        for alert in alerts:
            severity = str(alert.get("severity", "WARNING")).upper()
            tone = "danger" if severity == "CRITICAL" else ("warning" if severity == "WARNING" else "info")
            badge = status_badge_html(severity, tone=tone)
            page_target = str(alert.get("page_path", "app.py"))
            page_label = str(alert.get("page_label", "View Details"))

            st.markdown(
                f'<div style="background:#ffffff;border:1px solid #E5EAF0;border-left:4px solid {_get_tone(tone)["accent"]};'
                f'border-radius:8px;padding:0.75rem 0.9rem;margin-bottom:8px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                f'<strong style="font-size:0.86rem;color:#202B38;">{_escape(alert.get("title", ""))}</strong>'
                f'{badge}'
                f'</div>'
                f'<div style="font-size:0.78rem;color:#758294;margin-bottom:6px;">{_escape(alert.get("explanation", ""))}</div>'
                f'<div style="font-size:0.74rem;color:#202B38;font-weight:600;">{_escape(alert.get("metric_info", ""))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if _page_exists(page_target):
                st.page_link(page_target, label=page_label, icon=":material/arrow_forward:")


def render_quick_actions(actions: List[Mapping[str, Any]]) -> None:
    """Render IMMODESK/UnitStack-style quick action shortcuts."""
    with st.container(border=True):
        st.markdown(
            '<div style="margin-bottom:8px;">'
            '<strong style="font-size:0.92rem;color:#202B38;">Quick Actions</strong>'
            '<div style="font-size:0.76rem;color:#758294;">Direct navigation to key operational workflows</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(actions))
        for col, action in zip(cols, actions):
            with col:
                page_path = str(action.get("page_path", "app.py"))
                label = str(action.get("label", "Action"))
                icon = str(action.get("icon", ":material/arrow_forward:"))
                if _page_exists(page_path):
                    st.page_link(page_path, label=label, icon=icon)


def render_header(
    active_page: str = "Portfolio",
    active_section: str = "Today",
    user_name: str = "Executive Studio",
    user_role: str = "Portfolio Lead",
    user_initials: str = "ES",
) -> None:
    """Render the enterprise SaaS shell: Dark Navy Sidebar + Top Navigation."""
    render_sidebar(active_page=active_page)
    render_top_navigation(
        breadcrumbs=["Residential Property Intelligence", active_page],
        current_page=active_page,
    )


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
            f'<span class="ai-period-pill">{_escape(reporting_period)}</span>'
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
    source_table: Optional[str] = None,
) -> str:
    """Build HTML for a single enterprise KPI card styled after AI Studio."""
    delta_html = status_badge_html(delta, tone=delta_tone) if delta else ""
    icon_html = f'<span class="ai-kpi-icon">{_escape(icon)}</span>' if icon else ""
    top_right = delta_html or icon_html
    caption_html = (
        f'<div class="ai-kpi-caption">{_escape(caption)}</div>' if caption else ""
    )
    source_html = (
        f'<div class="ai-kpi-source">{_escape(source_table)}</div>'
        if source_table
        else ""
    )

    return (
        '<div class="ai-kpi-card">'
        '<div class="ai-kpi-top">'
        f'<span class="ai-kpi-label">{_escape(label)}</span>'
        f"{top_right}"
        "</div>"
        f'<div class="ai-kpi-value">{_escape(value)}</div>'
        f"{caption_html}"
        f"{source_html}"
        "</div>"
    )


def render_kpi_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_tone: str = "neutral",
    caption: Optional[str] = None,
    icon: Optional[str] = None,
    source_table: Optional[str] = None,
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
            source_table=source_table,
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
            source_table=card.get("source_table"),
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

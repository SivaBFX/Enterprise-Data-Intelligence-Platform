"""Shared AI Studio UI design system and reusable components."""

from contextlib import contextmanager
import html
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd
import streamlit as st

# Backward compatibility wrappers for older Streamlit runtimes (e.g., Databricks Apps)
# where st.button() does not accept the 'icon' keyword argument (added in Streamlit 1.38).
_orig_st_button = st.button


def _safe_st_button(label: str, *args: Any, **kwargs: Any) -> bool:
    try:
        return _orig_st_button(label, *args, **kwargs)
    except TypeError as err:
        if "icon" in kwargs and "unexpected keyword argument 'icon'" in str(err):
            kwargs.pop("icon", None)
            return _orig_st_button(label, *args, **kwargs)
        raise


st.button = _safe_st_button

_orig_st_page_link = getattr(st, "page_link", None)
if _orig_st_page_link is not None:

    def _safe_st_page_link(page: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return _orig_st_page_link(page, *args, **kwargs)
        except TypeError as err:
            if "icon" in kwargs and "unexpected keyword argument 'icon'" in str(err):
                kwargs.pop("icon", None)
                return _orig_st_page_link(page, *args, **kwargs)
            raise

    st.page_link = _safe_st_page_link

APP_ROOT = Path(__file__).resolve().parent.parent

# Centralized tone palette for status badges, KPI deltas, and insight cards.
TONE_STYLES = {
    "success": {
        "bg": "#EBF8F0",
        "border": "#B4E3C7",
        "text": "#15803D",
        "dot": "#15803D",
        "accent": "#15803D",
    },
    "warning": {
        "bg": "#FEF7EA",
        "border": "#F8D8A0",
        "text": "#B45309",
        "dot": "#D97706",
        "accent": "#D97706",
    },
    "danger": {
        "bg": "#FEF2F2",
        "border": "#FECACA",
        "text": "#DC2626",
        "dot": "#DC2626",
        "accent": "#DC2626",
    },
    "info": {
        "bg": "#EFF6FF",
        "border": "#BFDBFE",
        "text": "#1D4ED8",
        "dot": "#3478C8",
        "accent": "#3478C8",
    },
    "neutral": {
        "bg": "#F1F5F9",
        "border": "#E2E8F0",
        "text": "#475569",
        "dot": "#64748B",
        "accent": "#64748B",
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
    """Inject the Enterprise SaaS light theme stylesheet with zero header overlap."""
    _render_html(
        """
<style>
:root {
    --saas-sidebar: #172536;
    --saas-sidebar-border: #223348;
    --saas-sidebar-hover: #1E2F42;
    --saas-sidebar-active: #1E2F42;
    --saas-sidebar-text: #8C9BAE;
    --saas-sidebar-text-hover: #FFFFFF;
    --saas-bg: #F7F9FC;
    --saas-card: #FFFFFF;
    --saas-border: #E2E8F0;
    --saas-border-strong: #CBD5E1;
    --saas-text-primary: #172B4D;
    --saas-text-secondary: #64748B;
    --saas-text-muted: #94A3B8;
    --saas-green: #0F9D83;
    --saas-green-hover: #0C806A;
    --saas-green-soft: #E6F7F3;
    --saas-green-border: #A3E4D7;
    --saas-blue: #3478C8;
    --saas-warning: #D97706;
    --saas-critical: #DC2626;
    --ai-bg: #F7F9FC;
    --ai-surface: #FFFFFF;
    --ai-surface-subtle: #F8FAFC;
    --ai-border: #E2E8F0;
    --ai-border-strong: #CBD5E1;
    --ai-navy: #172B4D;
    --ai-text: #172B4D;
    --ai-body: #334155;
    --ai-muted: #64748B;
    --ai-green: #0F9D83;
    --ai-green-hover: #0C806A;
    --ai-green-soft: #E6F7F3;
    --ai-green-border: #A3E4D7;
    --text-color: #172B4D;
    --background-color: #F7F9FC;
    --secondary-background-color: #FFFFFF;
    --primary-color: #0F9D83;
}

/* Base canvas and typography */
html, body, .stApp,
div[data-testid="stAppViewContainer"],
div[data-testid="stMain"] {
    background-color: var(--ai-bg) !important;
    color: var(--ai-text) !important;
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
}

/* Prevent Streamlit / Databricks Apps top toolbar from overlapping the custom app header */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 3.25rem !important;
    pointer-events: none;
    z-index: 100 !important;
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
    padding-top: 4.5rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 1.75rem !important;
    padding-right: 1.75rem !important;
}

/* Minimal Light Enterprise SaaS Sidebar (~265px width) */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #EAECF0 !important;
}

section[data-testid="stSidebar"]:not([aria-expanded="false"]) {
    min-width: 250px !important;
    max-width: 280px !important;
    width: 268px !important;
}

/* Eliminate the empty gap at the top of the sidebar */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
    background-color: #FFFFFF !important;
}

header[data-testid="stSidebarHeader"],
div[data-testid="stSidebarHeader"] {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
    background-color: #FFFFFF !important;
    height: 1.75rem !important;
    min-height: 1.75rem !important;
    padding: 0.2rem 0.65rem 0 0.65rem !important;
    margin: 0 !important;
}

section[data-testid="stSidebar"] > div:first-child,
section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
    background-color: #FFFFFF !important;
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
}

section[data-testid="stSidebar"] div[data-testid="stSidebarCollapseButton"] button {
    color: #64748B !important;
}

/* Sidebar branding header */
.saas-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.75rem 0.45rem 0.85rem 0.45rem;
    border-bottom: 1px solid #EAECF0;
    margin-bottom: 0.65rem;
}

.saas-brand-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #0F9D83;
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 1px 3px rgba(15, 157, 131, 0.2);
    flex-shrink: 0;
}

.saas-brand-title {
    color: #0F172A;
    font-size: 0.90rem;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.01em;
}

.saas-brand-subtitle {
    color: #059669;
    font-size: 0.63rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 1px;
}

/* Nav group labels: strictly left-aligned */
.saas-nav-group-label {
    color: #94A3B8;
    font-size: 0.64rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.65rem 0.65rem 0.2rem 0.65rem;
    margin-top: 0.15rem;
    text-align: left !important;
}

/* Sidebar navigation links: strictly left-aligned */
section[data-testid="stSidebar"] div[data-testid="stPageLink"] {
    width: 100% !important;
    text-align: left !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a {
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 6px !important;
    padding: 0.32rem 0.65rem !important;
    min-height: 32px !important;
    height: 32px !important;
    color: #475569 !important;
    text-decoration: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    text-align: left !important;
    gap: 9px !important;
    width: 100% !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a * {
    text-align: left !important;
    justify-content: flex-start !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a p,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a span {
    color: #475569 !important;
    font-weight: 500 !important;
    font-size: 0.80rem !important;
    text-align: left !important;
    justify-content: flex-start !important;
    margin: 0 !important;
    white-space: nowrap !important;
}

/* Fixed icon alignment column */
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a span:first-child,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a svg {
    flex-shrink: 0 !important;
    width: 18px !important;
    min-width: 18px !important;
    text-align: center !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-right: 2px !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover {
    background-color: #F8FAFC !important;
    border-color: #F1F5F9 !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover p,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a:hover span {
    color: #0F172A !important;
}

/* Active page link in sidebar: soft mint capsule matching reference */
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] {
    background-color: #D1FAE5 !important;
    border: 1px solid #A7F3D0 !important;
    box-shadow: none !important;
    justify-content: flex-start !important;
}

section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] p,
section[data-testid="stSidebar"] div[data-testid="stPageLink"] a[aria-current="page"] span {
    color: #065F46 !important;
    font-weight: 650 !important;
    text-align: left !important;
}

/* Sidebar planned pills: left aligned */
section[data-testid="stSidebar"] .ai-nav-pill-planned {
    justify-content: flex-start !important;
    text-align: left !important;
    padding-left: 0.65rem !important;
    min-height: 32px !important;
    height: 32px !important;
    border-radius: 6px !important;
    font-size: 0.80rem !important;
}

/* Sidebar bottom graphic and tagline */
.saas-sidebar-footer {
    padding: 1rem 0.5rem 0.5rem 0.5rem;
    margin-top: 1.5rem;
    border-top: 1px solid #EAECF0;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.saas-sidebar-tagline {
    color: #475569;
    font-size: 0.78rem;
    font-weight: 600;
    line-height: 1.35;
    letter-spacing: -0.01em;
}

/* Top bar avatar badge and live sync button */
.top-nav-avatar {
    width: 26px;
    height: 26px;
    border-radius: 999px;
    background: #0F172A;
    color: #FFFFFF;
    font-size: 0.68rem;
    font-weight: 650;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #E2E8F0;
    cursor: default;
    gap: 2px;
}

.top-nav-avatar-chevron {
    font-size: 0.50rem;
    color: #94A3B8;
    margin-left: 2px;
}

div.stButton > button[key*="top_sync_"] {
    background-color: #FFFFFF !important;
    color: #059669 !important;
    border: 1px solid #EAECF0 !important;
    border-radius: 999px !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    height: 28px !important;
    min-height: 28px !important;
    padding: 0.15rem 0.65rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: none !important;
}

div.stButton > button[key*="top_sync_"]:hover {
    border-color: #A7F3D0 !important;
    background-color: #ECFDF5 !important;
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
div[data-testid="stMain"] div[data-testid="stPageLink"] a,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a {
    width: 100% !important;
    min-height: 30px;
    height: 30px;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px;
    padding: 0.18rem 0.65rem !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    border-radius: 6px !important;
    color: var(--ai-body) !important;
    text-decoration: none !important;
    box-shadow: none !important;
    transition: all 0.15s ease;
}

div[data-testid="stMain"] div[data-testid="stPageLink"] a p,
div[data-testid="stMain"] div[data-testid="stPageLink"] a span,
div[data-testid="stMain"] div[data-testid="stPageLink"] a div,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a p,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a span,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a div {
    color: var(--ai-body) !important;
    font-weight: 550 !important;
    font-size: 0.78rem !important;
    white-space: nowrap !important;
}

div[data-testid="stMain"] div[data-testid="stPageLink"] a:hover,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a:hover {
    background-color: #eceff4 !important;
    border-color: transparent !important;
}

div[data-testid="stMain"] div[data-testid="stPageLink"] a:hover p,
div[data-testid="stMain"] div[data-testid="stPageLink"] a:hover span,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a:hover p,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a:hover span {
    color: var(--ai-navy) !important;
}

div[data-testid="stMain"] div[data-testid="stPageLink"] a[aria-current="page"],
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a[aria-current="page"] {
    background-color: var(--ai-surface) !important;
    border: 1px solid var(--ai-border) !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
}

div[data-testid="stMain"] div[data-testid="stPageLink"] a[aria-current="page"] p,
div[data-testid="stMain"] div[data-testid="stPageLink"] a[aria-current="page"] span,
div[data-testid="stMain"] div[data-testid="stPageLink"] a[aria-current="page"] div,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a[aria-current="page"] p,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a[aria-current="page"] span,
div[data-testid="stMainBlockContainer"] div[data-testid="stPageLink"] a[aria-current="page"] div {
    color: var(--ai-navy) !important;
    font-weight: 650 !important;
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
    font-size: 1.35rem;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: -0.02em;
    line-height: 1.25;
    margin: 0;
}

.ai-page-desc {
    font-size: 0.82rem;
    color: #64748B;
    margin: 0.25rem 0 0 0;
    line-height: 1.4;
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
    padding: 0.22rem 0.6rem;
    border-radius: 999px;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    color: #475569;
    font-size: 0.73rem;
    font-weight: 550;
}

/* Status badges */
.ai-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
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
    margin: 1.35rem 0 0.65rem 0 !important;
    clear: both !important;
    flex-wrap: wrap;
}

.ai-section-header.compact {
    margin: 0.35rem 0 0.45rem 0 !important;
}

.ai-section-title {
    font-size: 0.92rem !important;
    font-weight: 650 !important;
    color: #0F172A !important;
    letter-spacing: -0.01em;
    line-height: 1.25;
}

.ai-section-subtitle {
    font-size: 0.75rem !important;
    color: #64748B !important;
    margin-top: 3px;
    line-height: 1.35;
}

.ai-micro-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #94A3B8;
    padding-left: 2px;
}

/* Reusable Minimal Pastel KPI Cards (Equal height, no clipping, restrained font) */
.ai-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 0.85rem;
    margin-top: 0.45rem !important;
    margin-bottom: 1.25rem !important;
    align-items: stretch;
}

.ai-kpi-card {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 8px;
    padding: 0.75rem 0.85rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
    min-height: 114px !important;
    height: 100% !important;
    box-sizing: border-box !important;
    transition: all 0.15s ease;
}

.ai-kpi-card:hover {
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
}

/* 4 Pastel Tints matching reference */
.ai-kpi-grid > .ai-kpi-card:nth-child(4n+1) {
    background-color: #FAF5FF !important;
    border-color: #E9D5FF !important;
}
.ai-kpi-grid > .ai-kpi-card:nth-child(4n+1) .ai-kpi-circle-icon {
    background-color: #F3E8FF !important;
    color: #7C3AED !important;
}

.ai-kpi-grid > .ai-kpi-card:nth-child(4n+2) {
    background-color: #ECFDF5 !important;
    border-color: #A7F3D0 !important;
}
.ai-kpi-grid > .ai-kpi-card:nth-child(4n+2) .ai-kpi-circle-icon {
    background-color: #D1FAE5 !important;
    color: #059669 !important;
}

.ai-kpi-grid > .ai-kpi-card:nth-child(4n+3) {
    background-color: #EFF6FF !important;
    border-color: #BFDBFE !important;
}
.ai-kpi-grid > .ai-kpi-card:nth-child(4n+3) .ai-kpi-circle-icon {
    background-color: #DBEAFE !important;
    color: #2563EB !important;
}

.ai-kpi-grid > .ai-kpi-card:nth-child(4n+4) {
    background-color: #FFF1F2 !important;
    border-color: #FECDD3 !important;
}
.ai-kpi-grid > .ai-kpi-card:nth-child(4n+4) .ai-kpi-circle-icon {
    background-color: #FFE4E6 !important;
    color: #E11D48 !important;
}

.ai-kpi-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    min-height: 32px;
    width: 100%;
}

.ai-kpi-label {
    font-size: 0.74rem;
    font-weight: 600;
    color: #475569;
    line-height: 1.25;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: normal !important;
    overflow-wrap: break-word !important;
    flex: 1 1 auto;
    min-width: 0;
}

.ai-kpi-card .ai-badge {
    font-size: 0.68rem !important;
    padding: 0.15rem 0.45rem !important;
    max-width: 58% !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    flex-shrink: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
}

.ai-kpi-value {
    font-size: 1.22rem !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
    margin: 4px 0 6px 0 !important;
    line-height: 1.25;
    white-space: nowrap;
    overflow: visible;
}

.ai-kpi-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    margin-top: auto;
}

.ai-kpi-caption {
    font-size: 0.68rem;
    color: #94A3B8;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex: 1;
}

.ai-kpi-circle-icon {
    width: 24px;
    height: 24px;
    min-width: 24px;
    border-radius: 999px;
    background: #E6F7F5;
    color: #0E7C66;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.76rem;
    flex-shrink: 0;
    margin-left: auto;
}

.ai-kpi-source {
    display: none;
}

/* Three-column Decision Brief cards */
.ai-decision-card {
    background: #FFFFFF;
    border: 1px solid #EAECF0;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 110px;
    height: 100%;
    position: relative;
    border-left-width: 4px !important;
}

.ai-decision-card.tone-emerald {
    border-left-color: #10B981 !important;
}

.ai-decision-card.tone-orange {
    border-left-color: #F59E0B !important;
}

.ai-decision-card.tone-blue {
    border-left-color: #3B82F6 !important;
}

.ai-decision-header {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 4px;
}

.ai-decision-title {
    font-size: 0.88rem;
    font-weight: 650;
    color: #0F172A;
}

.ai-decision-desc {
    font-size: 0.78rem;
    color: #64748B;
    margin-bottom: 10px;
    line-height: 1.38;
}

.ai-decision-pill {
    background-color: #ECFDF5;
    color: #065F46 !important;
    border: 1px solid #A7F3D0;
    border-radius: 999px;
    padding: 0.25rem 0.75rem;
    font-size: 0.74rem;
    font-weight: 600;
    text-decoration: none !important;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    width: fit-content;
    transition: all 0.15s ease;
}

.ai-decision-pill:hover {
    background-color: #D1FAE5;
    color: #064E3B !important;
    border-color: #6EE7B7;
}

/* Decision Queue & Sub-tiles */
.ai-stat-tile {
    background: var(--ai-surface-subtle);
    border: 1px solid var(--ai-border);
    border-radius: 10px;
    padding: 0.65rem 0.8rem;
    min-height: 68px;
    display: flex;
    flex-direction: column;
    justify-content: center;
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
    border-radius: 10px;
    padding: 0.65rem 0.85rem;
    margin-bottom: 0.45rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
}

.ai-insight-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
    flex-wrap: wrap;
}

.ai-insight-title {
    font-size: 0.87rem;
    font-weight: 700;
    color: var(--ai-navy);
}

.ai-insight-body {
    font-size: 0.82rem;
    color: var(--ai-body);
    line-height: 1.44;
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

/* Native Streamlit Metric Cards - Full visibility with zero truncation */
div[data-testid="stMetric"] {
    background: var(--ai-surface);
    border: 1px solid var(--ai-border);
    border-radius: 12px;
    padding: 10px 14px !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
}

div[data-testid="stMetricLabel"],
div[data-testid="stMetricLabel"] p,
div[data-testid="stMetricLabel"] label {
    color: var(--ai-muted) !important;
    font-size: 0.77rem !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

div[data-testid="stMetricValue"],
div[data-testid="stMetricValue"] > div,
div[data-testid="stMetricValue"] span {
    color: var(--ai-navy) !important;
    font-size: clamp(1.1rem, 1.6vw, 1.35rem) !important;
    font-weight: 750 !important;
    font-variant-numeric: tabular-nums !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.25 !important;
}

/* Equal-height column cards across horizontal grid blocks */
div[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    display: flex !important;
    flex-direction: column !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
}

div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
}

/* Style action page links inside columns to look like cohesive minimal secondary buttons */
div[data-testid="stColumn"] > div[data-testid="stPageLink"] a {
    background-color: #FFFFFF !important;
    border: 1px solid #EAECF0 !important;
    border-radius: 6px !important;
    min-height: 30px !important;
    height: 30px !important;
    padding: 0.15rem 0.65rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: #1E293B !important;
    font-weight: 550 !important;
    font-size: 0.76rem !important;
    box-shadow: none !important;
    text-decoration: none !important;
    transition: all 0.15s ease;
}

div[data-testid="stColumn"] > div[data-testid="stPageLink"] a:hover {
    background-color: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
}

/* Crisp minimal bordered containers */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 10px !important;
    border-color: #EAECF0 !important;
}

/* Buttons: compact, minimal, professional styling */
.stButton > button,
button[data-testid="stBaseButton-secondary"],
div[data-testid="stDownloadButton"] > button {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 6px !important;
    color: #1E293B !important;
    font-weight: 550 !important;
    font-size: 0.76rem !important;
    min-height: 30px !important;
    height: 30px !important;
    padding: 0.15rem 0.65rem !important;
    box-shadow: none !important;
    transition: all 0.15s ease;
}

.stButton > button p,
.stButton > button span,
button[data-testid="stBaseButton-secondary"] p,
button[data-testid="stBaseButton-secondary"] span,
div[data-testid="stDownloadButton"] > button p,
div[data-testid="stDownloadButton"] > button span {
    color: #1E293B !important;
    font-size: 0.76rem !important;
    font-weight: 550 !important;
}

.stButton > button:hover,
button[data-testid="stBaseButton-secondary"]:hover,
div[data-testid="stDownloadButton"] > button:hover {
    background-color: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
}

.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"],
div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background-color: #0F9D83 !important;
    border: 1px solid #0F9D83 !important;
    border-radius: 6px !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 0.76rem !important;
    min-height: 30px !important;
    height: 30px !important;
    padding: 0.15rem 0.75rem !important;
    box-shadow: none !important;
}

.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span,
button[data-testid="stBaseButton-primary"] p,
button[data-testid="stBaseButton-primary"] span,
div[data-testid="stFormSubmitButton"] button[kind="primary"] p,
div[data-testid="stFormSubmitButton"] button[kind="primary"] span {
    color: #ffffff !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
}

.stButton > button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
    background-color: #0C806A !important;
    border-color: #0C806A !important;
}

/* Suggested question buttons: ultra-compact subtle mint pills */
div.stButton > button[key*="suggest"],
div.stButton > button[key*="genie_suggest"],
div.stButton > button[key*="genie_btn_"],
div.stButton > button[key*="followup_"] {
    background-color: #F0FDF4 !important;
    color: #065F46 !important;
    border: 1px solid #DCFCE7 !important;
    border-radius: 999px !important;
    min-height: 25px !important;
    height: 25px !important;
    font-size: 0.70rem !important;
    font-weight: 550 !important;
    line-height: 1.15 !important;
    text-align: center !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0.1rem 0.55rem !important;
    white-space: nowrap !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
}

div.stButton > button[key*="suggest"] p,
div.stButton > button[key*="genie_suggest"] p,
div.stButton > button[key*="genie_btn_"] p,
div.stButton > button[key*="followup_"] p,
div.stButton > button[key*="suggest"] span,
div.stButton > button[key*="genie_suggest"] span,
div.stButton > button[key*="genie_btn_"] span,
div.stButton > button[key*="followup_"] span {
    color: #065F46 !important;
    font-size: 0.70rem !important;
    font-weight: 550 !important;
}

div.stButton > button[key*="suggest"]:hover,
div.stButton > button[key*="genie_suggest"]:hover,
div.stButton > button[key*="genie_btn_"]:hover,
div.stButton > button[key*="followup_"]:hover {
    background-color: #DCFCE7 !important;
    border-color: #BBF7D0 !important;
    color: #047857 !important;
}

/* Perspective toggle buttons on Executive Overview: sleek executive segmented pills */
div[class*="st-key-persona_btn_"] button,
div.stButton > button[key*="persona_btn_"] {
    min-height: 36px !important;
    height: 36px !important;
    border-radius: 8px !important;
    padding: 0 0.55rem !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    line-height: normal !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 6px !important;
    white-space: nowrap !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}

div[class*="st-key-persona_btn_"] button p,
div[class*="st-key-persona_btn_"] button span,
div[class*="st-key-persona_btn_"] button div,
div.stButton > button[key*="persona_btn_"] p,
div.stButton > button[key*="persona_btn_"] span,
div.stButton > button[key*="persona_btn_"] div {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: normal !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[class*="st-key-persona_btn_"] button[kind="secondary"],
div[class*="st-key-persona_btn_"] button:not([kind="primary"]),
div.stButton > button[key*="persona_btn_"][kind="secondary"],
div.stButton > button[key*="persona_btn_"]:not([kind="primary"]) {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    color: #475569 !important;
    box-shadow: none !important;
}

div[class*="st-key-persona_btn_"] button[kind="secondary"] p,
div[class*="st-key-persona_btn_"] button[kind="secondary"] span,
div[class*="st-key-persona_btn_"] button:not([kind="primary"]) p,
div[class*="st-key-persona_btn_"] button:not([kind="primary"]) span,
div.stButton > button[key*="persona_btn_"][kind="secondary"] p,
div.stButton > button[key*="persona_btn_"][kind="secondary"] span,
div.stButton > button[key*="persona_btn_"]:not([kind="primary"]) p,
div.stButton > button[key*="persona_btn_"]:not([kind="primary"]) span {
    color: #475569 !important;
    font-size: 0.74rem !important;
    font-weight: 550 !important;
}

div[class*="st-key-persona_btn_"] button[kind="secondary"]:hover,
div[class*="st-key-persona_btn_"] button:not([kind="primary"]):hover,
div.stButton > button[key*="persona_btn_"][kind="secondary"]:hover,
div.stButton > button[key*="persona_btn_"]:not([kind="primary"]):hover {
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
    background-color: #F8FAFC !important;
}

div[class*="st-key-persona_btn_"] button[kind="primary"],
div.stButton > button[key*="persona_btn_"][kind="primary"] {
    background-color: #0F9D83 !important;
    border: 1px solid #0F9D83 !important;
    color: #FFFFFF !important;
    font-weight: 650 !important;
    box-shadow: 0 1px 3px rgba(15, 157, 131, 0.25) !important;
}

div[class*="st-key-persona_btn_"] button[kind="primary"] p,
div[class*="st-key-persona_btn_"] button[kind="primary"] span,
div[class*="st-key-persona_btn_"] button[kind="primary"] div,
div.stButton > button[key*="persona_btn_"][kind="primary"] p,
div.stButton > button[key*="persona_btn_"][kind="primary"] span,
div.stButton > button[key*="persona_btn_"][kind="primary"] div {
    color: #FFFFFF !important;
    font-size: 0.74rem !important;
    font-weight: 650 !important;
}

/* Soft mint active capsule token compatibility */
.ai-persona-mint-token {
    background-color: #D1FAE5 !important;
    border: 1px solid #A7F3D0 !important;
    color: #065F46 !important;
}

/* Selectboxes, Dropdown Buttons, Inputs, Textareas, and Popovers */
div[data-testid="stSelectbox"] > div:nth-child(2),
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    min-height: 38px !important;
    height: 38px !important;
    box-sizing: border-box !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    transition: all 0.15s ease !important;
    padding: 0 !important;
    overflow: hidden !important;
}

div[data-testid="stSelectbox"] > div:nth-child(2):hover,
div[data-baseweb="select"] > div:hover {
    border-color: #CBD5E1 !important;
}

div[data-testid="stSelectbox"] > div:nth-child(2):focus-within,
div[data-baseweb="select"] > div:focus-within {
    border-color: #0F9D83 !important;
    box-shadow: 0 0 0 1px #0F9D83 !important;
}

/* Ensure inner select input & value text are vertically centered */
div[data-testid="stSelectbox"] input,
div[data-testid="stSelectbox"] [data-testid="stSelectboxValue"],
div[data-baseweb="select"] input,
div[data-baseweb="select"] span,
div[data-baseweb="select"] div[role="combobox"] {
    display: flex !important;
    align-items: center !important;
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;
    line-height: 36px !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    padding: 0 10px !important;
    margin: 0 !important;
    border: none !important;
    outline: none !important;
    background: transparent !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
    white-space: nowrap !important;
    text-overflow: ellipsis !important;
}

/* Dropdown arrow icon styling and centering */
div[data-testid="stSelectbox"] svg,
div[data-baseweb="select"] svg {
    fill: #64748B !important;
    color: #64748B !important;
    width: 16px !important;
    height: 16px !important;
    margin-right: 8px !important;
    flex-shrink: 0 !important;
}

/* Single-line text and search inputs: match 38px height and vertical alignment */
div[data-testid="stTextInput"] > div:nth-child(2),
div[data-testid="stTextInputRootElement"],
div[data-baseweb="input"],
div[data-baseweb="input"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    min-height: 38px !important;
    height: 38px !important;
    box-sizing: border-box !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    transition: all 0.15s ease !important;
    padding: 0 !important;
    overflow: hidden !important;
}

div[data-testid="stTextInputRootElement"]:hover,
div[data-baseweb="input"]:hover {
    border-color: #CBD5E1 !important;
}

div[data-testid="stTextInputRootElement"]:focus-within,
div[data-baseweb="input"]:focus-within {
    border-color: #0F9D83 !important;
    box-shadow: 0 0 0 1px #0F9D83 !important;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextInputField"],
div[data-baseweb="input"] input {
    height: 36px !important;
    min-height: 36px !important;
    max-height: 36px !important;
    line-height: 36px !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    padding: 0 10px !important;
    margin: 0 !important;
    border: none !important;
    outline: none !important;
    background: transparent !important;
    box-sizing: border-box !important;
}

div[data-testid="stTextInput"] input::placeholder,
div[data-baseweb="input"] input::placeholder {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    font-size: 0.8125rem !important;
    line-height: 36px !important;
}

/* Multiline text areas */
div[data-baseweb="textarea"],
div[data-baseweb="textarea"] > div,
div[data-testid="stTextArea"] > div:nth-child(2) {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    color: #0F172A !important;
    min-height: 72px !important;
    padding: 8px 10px !important;
    box-sizing: border-box !important;
}

div[data-baseweb="textarea"] textarea,
div[data-testid="stTextArea"] textarea {
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    font-size: 0.8125rem !important;
    line-height: 1.4 !important;
}

div[data-baseweb="textarea"] textarea::placeholder,
div[data-testid="stTextArea"] textarea::placeholder {
    color: #94A3B8 !important;
    -webkit-text-fill-color: #94A3B8 !important;
    font-size: 0.8125rem !important;
}

/* Form submit buttons aligned with 38px inputs and dropdowns */
div[data-testid="stFormSubmitButton"] button {
    min-height: 38px !important;
    height: 38px !important;
    border-radius: 8px !important;
    font-size: 0.8125rem !important;
    font-weight: 600 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 1rem !important;
    background-color: #0F9D83 !important;
    border: 1px solid #0F9D83 !important;
    color: #FFFFFF !important;
}

/* Dropdown popover list container */
div[data-testid="stSelectboxVirtualDropdown"],
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[data-testid="stSelectboxVirtualDropdown"],
ul[role="listbox"] {
    background-color: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08) !important;
    color: #0F172A !important;
    padding: 4px !important;
}

/* Dropdown list option items */
div[data-testid="stSelectboxVirtualDropdown"] li,
div[data-testid="stSelectboxVirtualDropdown"] div[role="option"],
ul[role="listbox"] li,
li[role="option"] {
    color: #1E293B !important;
    background-color: #FFFFFF !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
    padding: 0.4rem 0.75rem !important;
    border-radius: 6px !important;
    display: flex !important;
    align-items: center !important;
    cursor: pointer !important;
    transition: background-color 0.1s ease !important;
}

div[data-testid="stSelectboxVirtualDropdown"] li span,
div[data-testid="stSelectboxVirtualDropdown"] div[role="option"] span,
ul[role="listbox"] li span,
li[role="option"] span {
    color: #1E293B !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
}

div[data-testid="stSelectboxVirtualDropdown"] li:hover,
div[data-testid="stSelectboxVirtualDropdown"] div[role="option"]:hover,
ul[role="listbox"] li:hover,
li[role="option"]:hover {
    background-color: #F8FAFC !important;
    color: #0F172A !important;
}

div[data-testid="stSelectboxVirtualDropdown"] li[aria-selected="true"],
div[data-testid="stSelectboxVirtualDropdown"] div[role="option"][aria-selected="true"],
ul[role="listbox"] li[aria-selected="true"],
li[role="option"][aria-selected="true"] {
    background-color: #ECFDF5 !important;
    color: #065F46 !important;
    font-weight: 600 !important;
}

div[data-testid="stSelectboxVirtualDropdown"] li[aria-selected="true"] span,
div[data-testid="stSelectboxVirtualDropdown"] div[role="option"][aria-selected="true"] span,
ul[role="listbox"] li[aria-selected="true"] span,
li[role="option"][aria-selected="true"] span {
    color: #065F46 !important;
    font-weight: 600 !important;
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
    """Render the minimal light enterprise sidebar navigation."""
    with st.sidebar:
        _render_html(
            '<div class="saas-sidebar-brand">'
            '<div class="saas-brand-icon">'
            '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
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
                        f'<div class="ai-nav-pill-planned" style="background:#F8FAFC;border-color:#EAECF0;color:#64748B;margin-bottom:4px;">'
                        f'<span>{_escape(label)}</span>'
                        f'<span class="ai-nav-soon-tag" style="background:#E2E8F0;color:#475569;">Planned</span>'
                        f'</div>'
                    )

        _render_html(
            '<div class="saas-sidebar-footer">'
            '<svg width="100%" height="40" viewBox="0 0 200 40" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="8" y="18" width="14" height="22" rx="1" fill="#ECFDF5" stroke="#10B981" stroke-opacity="0.5" stroke-width="1"/>'
            '<rect x="26" y="9" width="20" height="31" rx="1" fill="#ECFDF5" stroke="#10B981" stroke-opacity="0.6" stroke-width="1"/>'
            '<rect x="50" y="14" width="16" height="26" rx="1" fill="#ECFDF5" stroke="#10B981" stroke-opacity="0.45" stroke-width="1"/>'
            '<rect x="70" y="5" width="24" height="35" rx="1.5" fill="#D1FAE5" stroke="#059669" stroke-opacity="0.7" stroke-width="1"/>'
            '<path d="M82 2 L82 5" stroke="#059669" stroke-width="1.5"/>'
            '<rect x="98" y="13" width="18" height="27" rx="1" fill="#ECFDF5" stroke="#10B981" stroke-opacity="0.5" stroke-width="1"/>'
            '<rect x="120" y="8" width="22" height="32" rx="1" fill="#ECFDF5" stroke="#10B981" stroke-opacity="0.6" stroke-width="1"/>'
            '<rect x="146" y="16" width="16" height="24" rx="1" fill="#ECFDF5" stroke="#10B981" stroke-opacity="0.45" stroke-width="1"/>'
            '<circle cx="36" cy="15" r="1.1" fill="#059669" fill-opacity="0.75"/>'
            '<circle cx="36" cy="21" r="1.1" fill="#059669" fill-opacity="0.75"/>'
            '<circle cx="36" cy="27" r="1.1" fill="#059669" fill-opacity="0.75"/>'
            '<circle cx="78" cy="12" r="1.1" fill="#059669" fill-opacity="0.85"/>'
            '<circle cx="86" cy="12" r="1.1" fill="#059669" fill-opacity="0.85"/>'
            '<circle cx="78" cy="18" r="1.1" fill="#059669" fill-opacity="0.85"/>'
            '<circle cx="86" cy="18" r="1.1" fill="#059669" fill-opacity="0.85"/>'
            '<circle cx="78" cy="24" r="1.1" fill="#059669" fill-opacity="0.85"/>'
            '<circle cx="86" cy="24" r="1.1" fill="#059669" fill-opacity="0.85"/>'
            '<circle cx="127" cy="14" r="1.1" fill="#059669" fill-opacity="0.8"/>'
            '<circle cx="135" cy="14" r="1.1" fill="#059669" fill-opacity="0.8"/>'
            '<circle cx="127" cy="20" r="1.1" fill="#059669" fill-opacity="0.8"/>'
            '<circle cx="135" cy="20" r="1.1" fill="#059669" fill-opacity="0.8"/>'
            '</svg>'
            '<div class="saas-sidebar-tagline">'
            '<div>Smarter Insights.</div>'
            '<div>Greater Impact.</div>'
            '</div>'
            '</div>'
        )


def render_top_navigation(
    breadcrumbs: Optional[List[str]] = None,
    current_page: str = "Executive Overview",
    status_text: Optional[str] = "Gold Layer · Live Sync",
    status_tone: str = "success",
) -> None:
    """Render the crisp minimal SaaS top navigation bar with breadcrumbs and utility controls."""
    crumbs = breadcrumbs or ["Residential Property Intelligence", current_page]
    crumbs_html = " <span style='color:#CBD5E1;margin:0 6px;font-size:0.80rem;'>/</span> ".join(
        f"<span style='color:#0F172A;font-weight:650;'>{_escape(c)}</span>" if i == len(crumbs) - 1
        else f"<span style='color:#64748B;font-weight:450;'>{_escape(c)}</span>"
        for i, c in enumerate(crumbs)
    )

    home_svg = (
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#64748B" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'style="margin-right:6px;vertical-align:-2px;">'
        '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>'
        '<polyline points="9 22 9 12 15 12 15 22"></polyline>'
        '</svg>'
    )

    with st.container():
        left_col, right_col = st.columns([2.55, 1.45])
        with left_col:
            _render_html(
                f'<div style="display:flex;align-items:center;min-height:32px;font-size:0.80rem;">'
                f'{home_svg} {crumbs_html}'
                f'</div>'
            )
        with right_col:
            r1, r2 = st.columns([2.3, 0.7])
            with r1:
                safe_key = "".join(ch if ch.isalnum() else "_" for ch in current_page)
                sync_label = f"● {status_text} 🔄" if status_text else "● Live Sync 🔄"
                if st.button(sync_label, key=f"top_sync_{safe_key}", use_container_width=True):
                    if hasattr(st, "cache_data") and hasattr(st.cache_data, "clear"):
                        st.cache_data.clear()
                    st.rerun()
            with r2:
                _render_html(
                    '<div style="display:flex;align-items:center;justify-content:flex-end;height:32px;">'
                    '<div class="top-nav-avatar">SM <span class="top-nav-avatar-chevron">▼</span></div>'
                    '</div>'
                )

    _render_html('<div style="height:4px;"></div>')


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
    """Build HTML for a single enterprise KPI card styled after the minimal light reference."""
    delta_html = status_badge_html(delta, tone=delta_tone) if delta else ""
    icon_chip = (
        f'<span class="ai-kpi-circle-icon">{_escape(icon)}</span>'
        if icon
        else ""
    )
    caption_text = f'<span class="ai-kpi-caption">{_escape(caption)}</span>' if caption else ""
    footer_content = f'<div class="ai-kpi-footer">{caption_text}{icon_chip}</div>'

    return (
        '<div class="ai-kpi-card">'
        '<div class="ai-kpi-top">'
        f'<div class="ai-kpi-label">{_escape(label)}</div>'
        f"{delta_html}"
        "</div>"
        f'<div class="ai-kpi-value">{_escape(value)}</div>'
        f"{footer_content}"
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

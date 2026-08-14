import os
import sys

import pandas as pd
import streamlit as st

# Add project root to path for absolute imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.share_insights_v1.dashboard.pages.thesis_generation_full import (
    load_llm_config,
    get_provider_models,
    analyze_watchlist_batch,
    analyze_single_stock,
    display_analyzer_tab,
    generate_investment_thesis,
)
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation
from src.share_insights_v1.implementations.llm_providers.llm_manager import LLMManager
from src.share_insights_v1.utils.prompt_loader import ThesisPromptLoader
from src.share_insights_v1.services.storage.thesis_storage_service import ThesisStorageService
from src.share_insights_v1.utils.formatters import format_currency, get_scale_and_label
from src.share_insights_v1.utils.logging import log_page_view

AVAILABLE_ANALYZERS = [
    "dcf", "technical", "comparable", "startup",
    "ai_insights", "news_sentiment", "business_model",
    "financial_health", "analyst_consensus", "industry_analysis",
    "competitive_position", "management_quality"
]

ANALYZER_LABELS = {
    'dcf': 'DCF Analysis',
    'technical': 'Technical Analysis',
    'comparable': 'Comparable Analysis',
    'startup': 'Startup Analysis',
    'ai_insights': 'AI Insights',
    'analyst_consensus': 'Analyst Consensus',
    'news_sentiment': 'News Sentiment',
    'business_model': 'Business Model',
    'financial_health': 'Financial Health',
    'industry_analysis': 'Industry Analysis',
    'competitive_position': 'Competitive Position',
    'management_quality': 'Management Quality',
}

TAB_GROUPS = {
    "Overview": ["overview"],
    "Valuation": ["dcf", "comparable", "financial_health"],
    "Market Signals": ["technical", "analyst_consensus"],
    "Qualitative": ["business_model", "competitive_position", "management_quality",
                     "industry_analysis", "ai_insights", "startup"],
    "News": ["news_sentiment"],
    "Thesis": [],
}

# Token palette ported from the approved watchlist-redesign mockup, reskinning
# Streamlit's default chrome via its stable data-testid hooks (Streamlit 1.50)
# rather than the mockup's hand-authored HTML, since every widget here still
# needs to be a real interactive Streamlit component.
_THEME_CSS = """
<style>
:root {
    --la-ink: #151b1e; --la-ink-muted: #55636a; --la-ink-faint: #8a9599;
    --la-surface-raised: #ffffff; --la-surface-sunken: #eceeed;
    --la-border: #dde2e1; --la-border-strong: #c7cecd;
    --la-accent: #1e4a5c; --la-accent-strong: #163949; --la-accent-soft: #e4eef0; --la-accent-ink: #ffffff;
    --la-good: #1f7a4d; --la-good-soft: #e4f3ea;
    --la-warn: #9a6b14; --la-warn-soft: #fbf1dd;
    --la-bad: #b23a3a; --la-bad-soft: #fbe9e9;
    --la-font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --la-font-mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
    :root {
        --la-ink: #e9edee; --la-ink-muted: #a3b0b4; --la-ink-faint: #6c7a7f;
        --la-surface-raised: #171e22; --la-surface-sunken: #11161a;
        --la-border: #2a3338; --la-border-strong: #3a454b;
        --la-accent: #72b8ce; --la-accent-strong: #94cbdd; --la-accent-soft: #1c333c; --la-accent-ink: #0d1114;
        --la-good: #4fbe85; --la-good-soft: #163123;
        --la-warn: #d7a53f; --la-warn-soft: #332a10;
        --la-bad: #e17575; --la-bad-soft: #362020;
    }
}

[data-testid="stAppViewContainer"] { font-family: var(--la-font-ui); }
[data-testid="stAppViewContainer"] h1, [data-testid="stAppViewContainer"] h2, [data-testid="stAppViewContainer"] h3 {
    letter-spacing: -0.01em;
}

/* Metric labels/values (st.metric still used by the shared display_analyzer_tab
   header for dcf/technical/etc - can't be touched, so this is a plain,
   box-free style rather than the card look, plus a wrap fallback so long
   labels/values can't clip the way they did in the boxed version). */
[data-testid="stMetricLabel"] { color: var(--la-ink-faint) !important; text-transform: uppercase; letter-spacing: 0.04em; font-size: 0.7rem !important; white-space: normal !important; }
[data-testid="stMetricValue"] {
    font-family: var(--la-font-mono) !important; font-variant-numeric: tabular-nums;
    white-space: normal !important; overflow-wrap: break-word; line-height: 1.25 !important;
    font-size: 1.1rem !important;
}

/* Finviz-style key:value table (Option C) - label/value are separate cells so
   long content grows the row instead of clipping, unlike st.metric. */
table.la-kv { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 2px 0; }
table.la-kv td { padding: 6px 8px; border-bottom: 1px solid var(--la-border); vertical-align: baseline; }
table.la-kv tr:last-child td { border-bottom: none; }
table.la-kv td.la-kv-k {
    color: var(--la-ink-faint); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.03em;
    width: 1%; white-space: nowrap; padding-right: 12px;
}
table.la-kv td.la-kv-v { font-family: var(--la-font-mono); font-weight: 700; font-variant-numeric: tabular-nums; }

/* Density: shrink default heading/divider spacing so tabs need less scrolling */
[data-testid="stAppViewContainer"] h3 { margin: 0.5rem 0 0.35rem !important; font-size: 1.05rem !important; }
[data-testid="stAppViewContainer"] hr { margin: 0.5rem 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0.35rem !important; }

/* Expanders as cards */
[data-testid="stExpander"] {
    border: 1px solid var(--la-border) !important;
    border-radius: 8px !important;
    background: var(--la-surface-raised);
}

/* Stylized expander treatment (Option D: top accent stripe) - trialled on
   Configure first via a keyed wrapper before rolling out to every expander
   on the page. */
.st-key-la_configure_wrap [data-testid="stExpander"],
.st-key-la_configure_wrap [data-testid="stExpander"] > div,
.st-key-la_configure_wrap [data-testid="stExpander"] details {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    border-top: 3px solid var(--la-accent) !important;
    border-radius: 6px 6px 0 0 !important;
    overflow: hidden;
}
.st-key-la_configure_wrap [data-testid="stExpander"] summary {
    padding: 13px 16px !important;
    font-weight: 700 !important;
    color: var(--la-ink) !important;
    border: none !important;
    border-bottom: 1px solid var(--la-border) !important;
    box-shadow: none !important;
    transition: color 0.12s ease;
}
.st-key-la_configure_wrap [data-testid="stExpander"] summary:hover {
    color: var(--la-accent) !important;
}
.st-key-la_configure_wrap [data-testid="stExpander"] summary svg { color: var(--la-ink-faint); transition: color 0.12s ease; }
.st-key-la_configure_wrap [data-testid="stExpander"] summary:hover svg { color: var(--la-accent) !important; }
.st-key-la_configure_wrap [data-testid="stExpanderDetails"] {
    border: none !important;
    box-shadow: none !important;
    padding: 16px !important;
}

/* Buttons */
[data-testid^="stBaseButton-"] {
    border-radius: 6px !important;
    font-weight: 600 !important;
}
[data-testid="stBaseButton-primary"] {
    background: var(--la-accent) !important;
    border-color: var(--la-accent) !important;
    color: var(--la-accent-ink) !important;
}
[data-testid="stBaseButton-primary"]:hover {
    background: var(--la-accent-strong) !important;
    border-color: var(--la-accent-strong) !important;
}

/* Pill-style tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--la-border); }
[data-testid="stTab"] {
    border-radius: 999px !important;
    padding: 6px 14px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    background: transparent;
}
[data-testid="stTab"][aria-selected="true"] {
    background: var(--la-accent) !important;
    color: var(--la-accent-ink) !important;
}
[data-testid="stTab"][aria-selected="true"] p { color: var(--la-accent-ink) !important; }

/* Interactive table */
[data-testid="stDataFrame"] {
    border: 1px solid var(--la-border);
    border-radius: 8px;
    overflow: hidden;
}

/* Plain HTML tables (methods summary) - lighter than st.dataframe's canvas grid */
table.la-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 2px 0; }
table.la-table th {
    text-align: left; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.03em;
    color: var(--la-ink-faint); font-weight: 600; padding: 6px 10px; border-bottom: 1px solid var(--la-border-strong);
}
table.la-table td { padding: 6px 10px; border-bottom: 1px solid var(--la-border); }
table.la-table tr:last-child td { border-bottom: none; }

/* Sleek "read more" popover trigger - plain text-link look, not a full button */
.st-key-la_summary_popover_wrap button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    color: var(--la-accent) !important; padding: 2px 0 !important; font-size: 0.8rem !important;
}
.st-key-la_summary_popover_wrap button:hover { text-decoration: underline; }
.st-key-la_summary_popover_wrap button p { color: var(--la-accent) !important; font-size: 0.8rem !important; }

/* Section labels - one consistent style for every sub-section header across
   every tab, instead of ad hoc st.markdown("###"/"####") of varying levels. */
.la-section-label {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
    color: var(--la-ink-faint); margin: 20px 0 8px; padding-bottom: 5px;
    border-bottom: 1px solid var(--la-border);
}

/* Inputs */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    border-radius: 6px !important;
    border-color: var(--la-border-strong) !important;
}

.la-mode-pill {
    display: inline-flex; align-items: center; gap: 7px;
    background: var(--la-accent-soft); color: var(--la-accent);
    font-size: 0.8rem; font-weight: 600;
    padding: 5px 12px; border-radius: 6px; margin-bottom: 8px;
}
.la-rec-pill {
    display: inline-block; font-size: 0.75rem; font-weight: 700;
    padding: 3px 10px; border-radius: 4px; letter-spacing: 0.01em; white-space: nowrap;
}
.la-rec-strongbuy, .la-rec-buy { background: var(--la-good-soft); color: var(--la-good); }
.la-rec-hold { background: var(--la-warn-soft); color: var(--la-warn); }
.la-rec-sell, .la-rec-strongsell { background: var(--la-bad-soft); color: var(--la-bad); }
.la-ticker-mono { font-family: var(--la-font-mono); font-weight: 700; }
.la-upside-pos { color: var(--la-good); font-family: var(--la-font-mono); font-weight: 700; }
.la-upside-neg { color: var(--la-bad); font-family: var(--la-font-mono); font-weight: 700; }
</style>
"""


def _inject_theme_css():
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


def _rec_pill_class(rec: str) -> str:
    return "la-rec-" + rec.lower().replace(" ", "").replace("-", "")


def _rec_pill_html(rec: str) -> str:
    return f'<span class="la-rec-pill {_rec_pill_class(rec)}">{rec}</span>'


def _section_label(text: str):
    """One consistent sub-section header style, used across every tab instead
    of ad hoc st.markdown("###"/"####") calls at varying heading levels."""
    st.markdown(f'<div class="la-section-label">{text}</div>', unsafe_allow_html=True)


def _render_kv_table(pairs, cols=2):
    """Finviz-style label:value table (chosen over boxed st.metric cards after
    comparing options) - each label/value is its own table cell, so a long
    label ("Revenue Growth") or long value ("Consumer Electronics") just grows
    that row instead of getting clipped the way a fixed-width metric box does."""
    rows_html = []
    for i in range(0, len(pairs), cols):
        chunk = pairs[i:i + cols]
        cells = ''.join(
            f'<td class="la-kv-k">{label}</td><td class="la-kv-v">{value}</td>'
            for label, value in chunk
        )
        rows_html.append(f'<tr>{cells}</tr>')
    st.markdown(f'<table class="la-kv">{"".join(rows_html)}</table>', unsafe_allow_html=True)


# Analyzers with no dedicated renderer in the shared page - display_analyzer_tab
# falls back to a raw st.json() dump for these, which is hard to scan. Rendered
# locally instead (see _render_readable_dict) without touching the shared file.
_JSON_FALLBACK_ANALYZERS = {'financial_health', 'competitive_position', 'management_quality'}

_READABLE_DICT_HIDDEN_KEYS = {
    'method', 'applicable', 'recommendation', 'predicted_price', 'confidence',
    'error', 'upside_downside_pct', 'current_price', 'total_equity_value',
}


def _humanize_key(key: str) -> str:
    return key.replace('_', ' ').title()


def _render_value_readable(value, depth=0):
    """Render a single value at increasing scan-friendliness: scalars as plain
    text, flat lists as bullets, one level of nested dict as labeled sub-blocks -
    anything deeper falls back to st.json rather than reimplementing a full
    tree view, which is still far more scannable than dumping the whole thing."""
    if isinstance(value, bool):
        st.write("Yes" if value else "No")
    elif isinstance(value, (int, float)):
        st.write(f"{value:,.2f}" if isinstance(value, float) else f"{value:,}")
    elif isinstance(value, str):
        st.write(value)
    elif isinstance(value, list):
        if all(isinstance(v, (str, int, float)) for v in value):
            for v in value:
                st.markdown(f"- {v}")
        else:
            st.json(value)
    elif isinstance(value, dict):
        if depth >= 1:
            st.json(value)
        else:
            for k, v in value.items():
                if v in (None, '', [], {}):
                    continue
                st.markdown(f"**{_humanize_key(k)}**")
                _render_value_readable(v, depth=depth + 1)
    else:
        st.write(str(value))


def _render_readable_dict(data: dict, hidden_keys=_READABLE_DICT_HIDDEN_KEYS):
    """Formats an analyzer's raw result dict as scannable label/value pairs and
    bullet lists instead of raw JSON - short scalar fields in a 2-column grid,
    longer/nested fields as their own labeled section below."""
    scalar_rows = [(k, v) for k, v in data.items()
                   if k not in hidden_keys and v not in (None, '', [], {})
                   and isinstance(v, (str, int, float, bool))]
    complex_items = [(k, v) for k, v in data.items()
                      if k not in hidden_keys and v not in (None, '', [], {})
                      and not isinstance(v, (str, int, float, bool))]

    if scalar_rows:
        _render_kv_table([(_humanize_key(k), v) for k, v in scalar_rows], cols=2)

    for key, value in complex_items:
        _section_label(_humanize_key(key))
        _render_value_readable(value)


def _render_analyzer_tab(ticker, analyses, key, fm):
    """Drop-in replacement for display_analyzer_tab for the three analyzers
    that have no dedicated renderer upstream (mirrors its Recommendation/Target/
    Confidence header for visual consistency with the other tabs, then formats
    the body readably instead of falling back to st.json)."""
    if key not in _JSON_FALLBACK_ANALYZERS:
        display_analyzer_tab(ticker, analyses, key, ANALYZER_LABELS[key], financial_metrics=fm)
        return

    analysis_data = analyses.get(key)
    if not analysis_data or 'error' in analysis_data:
        st.info(f"{ANALYZER_LABELS[key]} was not run for this stock" if not analysis_data
                else f"{ANALYZER_LABELS[key]} failed: {analysis_data.get('error', 'Unknown error')}")
        return

    target = analysis_data.get('predicted_price', 0) or 0
    _render_kv_table([
        ("Recommendation", _rec_pill_html(analysis_data.get('recommendation', 'N/A'))),
        ("Target Price", f"${target:.2f}" if target else "N/A"),
        ("Confidence", analysis_data.get('confidence', 'N/A')),
    ], cols=3)
    _section_label("Details")
    _render_readable_dict(analysis_data)


def _render_financial_charts(revenue_data_statements):
    """Local reimplementation of the shared display_financial_charts_modal's
    chart-data prep (not called here to avoid its own st.expander wrapper) -
    same 3 bar charts, rendered inside a popover instead of a permanently
    expandable block."""
    revenue_data, gross_income_data, net_income_data = [], [], []
    operating_cf_data, free_cf_data, years = [], [], []

    annual_revenue = revenue_data_statements.get('annual_revenue', {})
    annual_income = revenue_data_statements.get('annual_income_stmt', {})
    cashflow_data = revenue_data_statements.get('cashflow', {})

    if annual_revenue:
        for date_str in reversed(sorted(annual_revenue.keys())):
            years.append(date_str[:4])
            revenue_data.append(annual_revenue.get(date_str, 0))
            if annual_income and date_str in annual_income:
                income_data = annual_income[date_str]
                gross_income_data.append(income_data.get('Gross Profit', 0) or 0)
                net_income_data.append(income_data.get('Net Income', 0) or 0)
            else:
                gross_income_data.append(0)
                net_income_data.append(0)
            if cashflow_data and date_str in cashflow_data:
                cf_data = cashflow_data[date_str]
                op_cf = (cf_data.get('Operating Cash Flow', 0) or cf_data.get('Total Cash From Operating Activities', 0) or
                         cf_data.get('Cash Flowsfromusedin Operating Activities Direct', 0) or cf_data.get('OperatingCashFlow', 0) or 0)
                free_cf = cf_data.get('Free Cash Flow', 0) or cf_data.get('FreeCashFlow', 0) or 0
                operating_cf_data.append(op_cf)
                free_cf_data.append(free_cf)
            else:
                operating_cf_data.append(0)
                free_cf_data.append(0)

    if not years:
        st.caption("No historical data available for charts.")
        return

    rev_max = max([abs(v) for v in revenue_data]) if revenue_data else 0
    rev_scale, rev_label = get_scale_and_label(rev_max)
    income_max = max([abs(v) for v in gross_income_data + net_income_data]) if (gross_income_data or net_income_data) else 0
    income_scale, income_label = get_scale_and_label(income_max)
    cf_max = max([abs(v) for v in operating_cf_data + free_cf_data]) if (operating_cf_data or free_cf_data) else 0
    cf_scale, cf_label = get_scale_and_label(cf_max)

    chart_col1, chart_col2, chart_col3 = st.columns(3)
    with chart_col1:
        st.markdown(f"**Revenue ({rev_label})**")
        st.bar_chart(pd.DataFrame({'Year': years, 'Revenue': [r / rev_scale for r in revenue_data]}).set_index('Year'),
                     height=200)
    with chart_col2:
        st.markdown(f"**Income ({income_label})**")
        st.bar_chart(pd.DataFrame({
            'Year': years,
            'Gross': [g / income_scale for g in gross_income_data],
            'Net': [n / income_scale for n in net_income_data],
        }).set_index('Year'), height=200)
    with chart_col3:
        st.markdown(f"**Cash Flow ({cf_label})**")
        st.bar_chart(pd.DataFrame({
            'Year': years,
            'Operating': [o / cf_scale for o in operating_cf_data],
            'Free': [f / cf_scale for f in free_cf_data],
        }).set_index('Year'), height=200)


def _financial_figures_pairs(fm):
    """Revenue/Gross Income/Net Income/Op CF/Free CF as kv-table pairs (not
    rendered directly) so they can be prepended as the first row of the main
    metrics table instead of living in their own separately-aligned table -
    two kv-tables with different column counts never line up column-for-column."""
    revenue_data_statements = fm.get('revenue_data_statements') or {}
    annual_income = revenue_data_statements.get('annual_income_stmt', {})
    cashflow_data = revenue_data_statements.get('cashflow', {})

    latest_revenue = latest_gross_income = latest_net_income = 0
    if annual_income:
        latest_year = list(annual_income.keys())[0]
        annual_data = annual_income[latest_year]
        latest_revenue = annual_data.get('Total Revenue', 0) or 0
        latest_gross_income = annual_data.get('Gross Profit', 0) or 0
        latest_net_income = annual_data.get('Net Income', 0) or 0

    latest_op_cf = latest_free_cf = 0
    if cashflow_data:
        latest_cf_date = list(cashflow_data.keys())[0]
        cf_data = cashflow_data[latest_cf_date]
        latest_op_cf = (cf_data.get('Operating Cash Flow', 0) or cf_data.get('Total Cash From Operating Activities', 0) or
                         cf_data.get('Cash Flowsfromusedin Operating Activities Direct', 0) or cf_data.get('OperatingCashFlow', 0) or 0)
        latest_free_cf = cf_data.get('Free Cash Flow', 0) or cf_data.get('FreeCashFlow', 0) or 0

    return [
        ("Revenue", format_currency(latest_revenue)),
        ("Gross Income", format_currency(latest_gross_income)),
        ("Net Income", format_currency(latest_net_income)),
        ("Op Cash Flow", format_currency(latest_op_cf)),
        ("Free Cash Flow", format_currency(latest_free_cf)),
    ]


def _render_methods_table(analyses):
    """Sleeker replacement for the plain st.dataframe methods summary - a real
    HTML table (like the kv tables elsewhere on this page) instead of
    Streamlit's canvas-rendered grid, so it matches the page's density/style
    rather than bringing its own toolbar/scrollbar chrome."""
    rows = [
        (k.replace('_', ' ').title(), _rec_pill_html(v.get('recommendation', 'N/A')),
         f"${v.get('predicted_price', 0) or 0:.2f}", v.get('confidence', 'N/A'))
        for k, v in analyses.items() if isinstance(v, dict)
    ]
    if not rows:
        return
    header = ''.join(f'<th>{h}</th>' for h in ("Method", "Recommendation", "Target Price", "Confidence"))
    body = ''.join(
        '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
        for row in rows
    )
    st.markdown(f'<table class="la-table"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>',
                unsafe_allow_html=True)


def _render_overview_compact(ticker, data, analyses):
    """Local replacement for display_overview_tab (not called here) - denser
    layout in a fixed order: company info, summary (with a lightweight
    "read more" popover), charts up front, then the metrics tables and the
    per-analyzer methods summary."""
    fm = data.get('financial_metrics') or {}

    st.markdown(
        f"**Company Type:** {data.get('company_type', 'N/A')}  ·  "
        f"**Sector:** {fm.get('sector', 'N/A')}  ·  **Industry:** {fm.get('industry', 'N/A')}"
    )

    summary = fm.get('business_summary') or ''
    if summary:
        preview = summary if len(summary) <= 280 else summary[:280].rsplit(' ', 1)[0] + '…'
        st.markdown(f"**Summary:** {preview}")
        if len(summary) > 280:
            with st.container(key="la_summary_popover_wrap"):
                with st.popover("Read full summary ›"):
                    st.write(summary)

    revenue_data_statements = fm.get('revenue_data_statements') or {}
    if revenue_data_statements:
        _section_label("Charts")
        _render_financial_charts(revenue_data_statements)

    market_cap = fm.get('market_cap') or 0
    roe = fm.get('roe')
    revenue_growth = fm.get('revenue_growth')
    div_yield = (fm.get('dividend_info') or {}).get('dividend_yield') or 0

    dividend_info = fm.get('dividend_info') or {}
    forward_pe = fm.get('forward_pe') or 0
    forward_eps = fm.get('forward_eps') or 0
    current_eps = fm.get('current_year_eps') or 0
    payout_ratio = dividend_info.get('payout_ratio') or 0
    div_rate = dividend_info.get('dividend_rate') or 0
    earnings_date = fm.get('earnings_date', 'N/A')
    target_median = (analyses.get('analyst_consensus') or {}).get('target_median_price') or 0

    _section_label("Metrics")
    _render_kv_table(_financial_figures_pairs(fm) + [
        ("Market Cap", format_currency(market_cap) if market_cap else "N/A"),
        ("P/E Ratio", fm.get('pe_ratio', 'N/A')),
        ("Forward P/E", f"{forward_pe:.2f}" if forward_pe else "N/A"),
        ("ROE", f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else "N/A"),
        ("Revenue Growth", f"{revenue_growth*100:.1f}%" if isinstance(revenue_growth, (int, float)) else "N/A"),
        ("Forward EPS", f"${forward_eps:.2f}" if forward_eps else "N/A"),
        ("Current EPS", f"${current_eps:.2f}" if current_eps else "N/A"),
        ("Dividend Yield", f"{div_yield:.2f}%" if div_yield else "N/A"),
        ("Annual Div Rate", f"${div_rate:.2f}" if div_rate else "N/A"),
        ("Payout Ratio", f"{payout_ratio:.1f}%" if payout_ratio else "N/A"),
        ("Debt/Equity", fm.get('debt_to_equity', 'N/A')),
        ("Current Ratio", fm.get('current_ratio', 'N/A')),
        ("Target Median", f"${target_median:.2f}" if target_median else "N/A"),
        ("Next Earnings", earnings_date if earnings_date and earnings_date != 'N/A' else "N/A"),
    ], cols=3)

    _section_label("Analysis Summary")
    _render_methods_table(analyses)


def render_llm_selector(providers_config):
    """Persistent LLM provider/model row - writes into the exact session_state
    keys the reused business logic (analyze_*, generate_investment_thesis)
    already reads: thesis_llm_manager / thesis_llm_provider / thesis_llm_model."""
    st.subheader("🤖 LLM Provider")
    col1, col2 = st.columns(2)

    with col1:
        provider_options = [(p['name'], f"{p['display_name']} {p['icon']}")
                             for p in providers_config if os.getenv(p['api_key_env'])]
        if provider_options:
            selected_provider_name = st.selectbox(
                "Provider:",
                options=[p[0] for p in provider_options],
                format_func=lambda x: next(p[1] for p in provider_options if p[0] == x),
                key="la_provider_selector"
            )
        else:
            st.error("No LLM providers available (missing API keys)")
            selected_provider_name = None

    with col2:
        if selected_provider_name:
            models = get_provider_models(providers_config, selected_provider_name)
            if models:
                selected_model = st.selectbox(
                    "Model:",
                    options=[m['name'] for m in models],
                    format_func=lambda x: next(f"{m['display_name']} ({m['name']})" for m in models if m['name'] == x),
                    key="la_model_selector"
                )
            else:
                st.error(f"No models available for {selected_provider_name}")
                selected_model = None
        else:
            selected_model = None

    if selected_provider_name and selected_model:
        try:
            shared_llm_manager = LLMManager(use_plugin_system=True)
            shared_llm_manager.set_primary_provider(selected_provider_name, selected_model)
            st.session_state.thesis_llm_manager = shared_llm_manager
            st.session_state.thesis_llm_provider = selected_provider_name
            st.session_state.thesis_llm_model = selected_model
            st.caption(f"✅ Using {selected_provider_name} / {selected_model}")
        except Exception as e:
            st.error(f"Failed to initialize LLM provider: {e}")
            st.session_state.thesis_llm_manager = LLMManager()
            st.session_state.thesis_llm_provider = None
            st.session_state.thesis_llm_model = None
    else:
        st.session_state.thesis_llm_manager = LLMManager()
        st.session_state.thesis_llm_provider = None
        st.session_state.thesis_llm_model = None


def render_configure_section():
    """Collapsible configure/run section. Collapses automatically once results
    exist, since expanded=not has_results is re-evaluated on every rerun."""
    from watchlist_component import get_watchlist

    watchlist = get_watchlist()
    has_results = bool(st.session_state.get('batch_results') or st.session_state.get('thesis_analysis_data'))

    if st.session_state.get('la_mode') == "Single Stock" and st.session_state.get('thesis_ticker'):
        st.markdown(f'<span class="la-mode-pill">📍 Single Stock · {st.session_state.thesis_ticker}</span>', unsafe_allow_html=True)
    elif watchlist:
        st.markdown(f'<span class="la-mode-pill">📋 Watchlist · {len(watchlist)} stocks</span>', unsafe_allow_html=True)

    with st.container(key="la_configure_wrap"), st.expander("⚙️ Configure", expanded=not has_results):
        mode = st.radio("Analysis Mode:", ["Watchlist Batch", "Single Stock"], horizontal=True, key="la_mode")

        if mode == "Single Stock":
            ticker = st.text_input("Enter Stock Ticker:", value="AAPL").upper()

            st.markdown("**News Sentiment Options**")
            col1, col2, col3 = st.columns(3)
            with col1:
                enable_web_scraping = st.checkbox("Enable Web Scraping", value=True, key="la_single_scrape")
            with col2:
                enable_llm_sentiment = st.checkbox("Enable LLM Sentiment", value=True, key="la_single_llm_sent")
            with col3:
                max_news_articles = st.number_input("Max News Articles", min_value=1, max_value=20, value=5, key="la_single_news_n")

            selected_analyzers = st.multiselect(
                "Analyzers to run:", AVAILABLE_ANALYZERS, default=AVAILABLE_ANALYZERS, key="la_single_analyzers"
            )

            if st.button("🔍 Analyze Stock", key="la_analyze_single"):
                if not st.session_state.get('thesis_llm_provider') or not st.session_state.get('thesis_llm_model'):
                    st.error("Please select LLM provider and model first")
                elif not selected_analyzers:
                    st.error("Please select at least one analyzer")
                elif not ticker:
                    st.error("Please enter a ticker")
                else:
                    st.session_state.news_options = {
                        'enable_web_scraping': enable_web_scraping,
                        'enable_llm_sentiment': enable_llm_sentiment,
                        'max_news_articles': max_news_articles
                    }
                    analyze_single_stock(ticker, selected_analyzers, st.session_state.thesis_llm_manager, max_news_articles)
                    st.rerun()

        else:  # Watchlist Batch
            if not watchlist:
                st.info("No stocks in watchlist. Add stocks using the sidebar.")
            else:
                st.write(f"**Watchlist ({len(watchlist)} stocks):** {', '.join(watchlist)}")

                st.markdown("**News Sentiment Options**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    batch_web_scraping = st.checkbox("Enable Web Scraping (Batch)", value=False, key="la_batch_scrape")
                with col2:
                    batch_llm_sentiment = st.checkbox("Enable LLM Sentiment (Batch)", value=False, key="la_batch_llm_sent")
                with col3:
                    batch_max_news_articles = st.number_input("Max News Articles (Batch)", min_value=1, max_value=20, value=7, key="la_batch_news_n")

                batch_analyzers = st.multiselect(
                    "Analyzers to run:", AVAILABLE_ANALYZERS, default=AVAILABLE_ANALYZERS, key="la_batch_analyzers"
                )

                if st.button("Analyze All Watchlist Stocks", key="la_analyze_batch"):
                    if not st.session_state.get('thesis_llm_provider') or not st.session_state.get('thesis_llm_model'):
                        st.error("Please select LLM provider and model first")
                    elif not batch_analyzers:
                        st.error("Please select at least one analyzer")
                    else:
                        st.session_state.batch_news_options = {
                            'enable_web_scraping': batch_web_scraping,
                            'enable_llm_sentiment': batch_llm_sentiment,
                            'max_news_articles': batch_max_news_articles
                        }
                        analyze_watchlist_batch(watchlist, batch_analyzers, st.session_state.thesis_llm_manager, batch_max_news_articles)
                        st.rerun()

    return mode


def render_summary_table(successful_results):
    """Native interactive summary table replacing the old button-column selector."""
    rows = []
    for ticker, data in successful_results.items():
        fm = data.get('financial_metrics') or {}
        rec = data.get('final_recommendation') or {}
        current_price = fm.get('current_price') or 0
        target_price = rec.get('target_price') or 0
        upside = ((target_price - current_price) / current_price * 100) if current_price and target_price else None
        rows.append({
            "Ticker": ticker,
            "Price": current_price,
            "Target": target_price,
            "Upside %": upside,
            "Recommendation": rec.get('recommendation', 'N/A'),
            "Confidence": rec.get('confidence', 'N/A'),
        })

    df = pd.DataFrame(rows)
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn(format="$%.2f"),
            "Target": st.column_config.NumberColumn(format="$%.2f"),
            "Upside %": st.column_config.NumberColumn(format="%+.1f%%"),
        },
        on_select="rerun",
        selection_mode="single-row",
        key="la_summary_table",
    )

    if event.selection.rows:
        st.session_state.la_selected_ticker = df.iloc[event.selection.rows[0]]["Ticker"]
    elif st.session_state.get('la_selected_ticker') not in successful_results:
        st.session_state.la_selected_ticker = df.iloc[0]["Ticker"] if not df.empty else None

    return st.session_state.get('la_selected_ticker')


def render_stock_detail(ticker, data):
    """Header metrics + 5 grouped category tabs (replaces the old 13 flat tabs)."""
    fm = data.get('financial_metrics') or {}
    rec = data.get('final_recommendation') or {}
    analyses = data.get('analyses') or {}
    company_name = fm.get('long_name') or ''

    current_price = fm.get('current_price') or 0
    target_price = rec.get('target_price') or 0
    upside = ((target_price - current_price) / current_price * 100) if current_price and target_price else None
    upside_html = (
        f'<span class="{"la-upside-pos" if upside >= 0 else "la-upside-neg"}">{upside:+.1f}%</span>'
        if upside is not None else 'N/A'
    )

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(
            f'<span class="la-ticker-mono" style="font-size:1.3rem;">{ticker}</span>'
            f'<br><span style="color:var(--la-ink-muted); font-size:0.85rem;">{company_name}</span>',
            unsafe_allow_html=True
        )
    with col2:
        _render_kv_table([
            ("Current Price", f"${current_price:.2f}" if current_price else "N/A"),
            ("Target Price", f"${target_price:.2f}" if target_price else "N/A"),
            ("Upside", upside_html),
            ("Recommendation", _rec_pill_html(rec.get("recommendation", "N/A"))),
        ], cols=2)

    st.caption(f"Confidence: {rec.get('confidence', 'N/A')}")

    tabs = st.tabs(list(TAB_GROUPS.keys()))
    for tab, group_name in zip(tabs, TAB_GROUPS.keys()):
        with tab:
            if group_name == "Overview":
                _render_overview_compact(ticker, data, analyses)
                continue

            if group_name == "Thesis":
                render_generate_thesis_section(ticker, data)
                continue

            present = [k for k in TAB_GROUPS[group_name] if k in analyses]
            if not present:
                st.caption("No analyzers from this group were run.")
            elif len(present) == 1:
                _render_analyzer_tab(ticker, analyses, present[0], fm)
            else:
                for k in present:
                    with st.expander(ANALYZER_LABELS[k]):
                        _render_analyzer_tab(ticker, analyses, k, fm)


def render_generate_thesis_section(ticker, data):
    """Thesis generation as its own tab (next to News) rather than a button
    that reveals a panel - always visible, no extra click needed. Thesis-type
    dropdown is file-driven (ThesisPromptLoader), same source of truth as the
    old page. save_thesis_to_database resolves batch_analysis_id straight from
    session_state (batch_results / thesis_analysis_data), so as long as those
    keys stay populated by the reused analyze_* functions, saving here links
    correctly without needing to pass anything extra through."""
    prompt_loader = ThesisPromptLoader()
    available_prompts = prompt_loader.list_available_prompts()
    if not available_prompts:
        st.warning("No thesis prompt templates found.")
        return
    display_names = {p: p.replace('_', ' ').title() for p in available_prompts}

    col1, col2 = st.columns([3, 1])
    with col1:
        prompt_key = st.selectbox(
            "Thesis Style:", available_prompts,
            format_func=lambda k: display_names[k],
            key=f"la_thesis_type_{ticker}"
        )
    with col2:
        generate_clicked = st.button("Generate", key=f"la_generate_{ticker}")

    if generate_clicked:
        if not st.session_state.get('thesis_llm_provider') or not st.session_state.get('thesis_llm_model'):
            st.error("Please select LLM provider and model first")
        else:
            generate_investment_thesis(ticker, data, display_names[prompt_key], st.session_state.thesis_llm_manager, show_prompt=True)

    history = ThesisStorageService().get_thesis_history(ticker, limit=5)
    if history:
        _section_label("Recent Theses")
        for h in history:
            created = h['created_at']
            label = f"{h['thesis_type'].replace('_', ' ').title()} — {created:%Y-%m-%d %H:%M}" if created else h['thesis_type']
            with st.expander(label):
                st.caption(f"LLM: {h.get('llm_provider', 'N/A')} / {h.get('llm_model', 'N/A')}")
                content = h.get('content', '')
                st.write(content[:500] + ("…" if len(content) > 500 else ""))


def show_live_analysis_page():
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return

    render_navigation()
    _inject_theme_css()

    st.title("📈 Live Analysis")
    show_disclaimer()
    st.markdown("*Run real-time analysis - single ticker or watchlist batch*")

    log_page_view('live_analysis', metadata={'mode': 'initial_load'})

    from watchlist_component import show_watchlist_sidebar
    show_watchlist_sidebar()

    providers_config = load_llm_config()
    render_llm_selector(providers_config)

    st.markdown("---")
    mode = render_configure_section()

    st.markdown("---")

    if mode == "Watchlist Batch" and st.session_state.get('batch_results'):
        successful_results = {t: d for t, d in st.session_state.batch_results.items() if 'error' not in d}
        failed_tickers = [t for t, d in st.session_state.batch_results.items() if 'error' in d]

        if not successful_results:
            st.warning("All stocks in the last batch run failed.")
        else:
            st.subheader(f"📊 Results ({len(successful_results)} stocks)")
            selected_ticker = render_summary_table(successful_results)
            if failed_tickers:
                st.caption(f"Failed: {', '.join(failed_tickers)}")

            if selected_ticker:
                st.markdown("---")
                render_stock_detail(selected_ticker, successful_results[selected_ticker])

    elif mode == "Single Stock" and st.session_state.get('thesis_analysis_data') and st.session_state.get('thesis_ticker'):
        ticker = st.session_state.thesis_ticker
        data = st.session_state.thesis_analysis_data
        render_stock_detail(ticker, data)


if __name__ == "__main__":
    show_live_analysis_page()

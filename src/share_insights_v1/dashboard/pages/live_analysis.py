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
    display_dcf_details,
    display_ai_insights_details,
    display_news_details,
    display_business_model_details,
    display_analyst_consensus_details,
    display_industry_analysis_details,
    display_startup_details,
    generate_investment_thesis,
)
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.components.theme import (
    inject_theme_css,
    rec_pill_html,
    rec_pill_class,
    section_label,
    render_kv_table,
)
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

# financial_health/competitive_position/management_quality have no dedicated
# renderer upstream (display_analyzer_tab falls back to a raw st.json() dump
# for these, which is hard to scan) - they're the analyzer keys absent from
# _LOCAL_DETAIL_RENDERERS below, so _render_analyzer_tab's dispatch falls
# through to _render_readable_dict for them instead.
_READABLE_DICT_HIDDEN_KEYS = {
    'method', 'applicable', 'recommendation', 'predicted_price', 'confidence',
    'error', 'upside_downside_pct', 'current_price', 'total_equity_value',
}


def _humanize_key(key: str) -> str:
    return key.replace('_', ' ').title()


def _fmt_num(value, decimals=2, suffix=""):
    """Round a raw numeric indicator (e.g. RSI 51.559723317858584) to a
    readable precision; passes non-numeric values through as-is."""
    if isinstance(value, (int, float)):
        return f"{value:.{decimals}f}{suffix}"
    return value if value is not None else "N/A"


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
        render_kv_table([(_humanize_key(k), v) for k, v in scalar_rows], cols=2)

    for key, value in complex_items:
        section_label(_humanize_key(key))
        _render_value_readable(value)


def _render_comparable_details(data: dict):
    """Local, denser replacement for the shared display_comparable_details
    (thesis_generation_full.py) - that function renders one st.write() call
    per field (each its own paragraph-spaced block, only 2 per row), which
    reads as a long vertical list. Same fields, as kv-tables instead."""
    multiples = data.get('target_multiples') or {}
    sources = data.get('multiple_sources') or {}

    def _tagged(key, label):
        val = multiples.get(key)
        tag = " 🔗" if sources.get(key) == 'config+peer_blend' else ""
        return (label, f"{val:.2f}x{tag}" if isinstance(val, (int, float)) else "N/A")

    if multiples:
        section_label("Valuation Multiples")
        render_kv_table([_tagged('pe', 'P/E'), _tagged('ps', 'P/S'),
                          _tagged('pb', 'P/B'), _tagged('ev_ebitda', 'EV/EBITDA')], cols=4)
        if sources:
            st.caption("🔗 = blended with live peer data; otherwise a config-based default")

    peers = data.get('peer_tickers') or []
    if peers:
        section_label("Peer Companies")
        st.write(", ".join(peers[:10]))

    peer_averages = data.get('peer_averages') or {}
    if peer_averages:
        section_label("Peer Averages")
        multiple_fields = {'pe_ratio': 'P/E', 'price_to_sales': 'P/S', 'price_to_book': 'P/B', 'ev_ebitda': 'EV/EBITDA'}
        pct_fields = {'roe': 'ROE', 'revenue_growth': 'Revenue Growth', 'profit_margin': 'Profit Margin'}
        pairs = [(label, f"{peer_averages[key]:.2f}x") for key, label in multiple_fields.items() if key in peer_averages]
        pairs += [(label, f"{peer_averages[key] * 100:.1f}%") for key, label in pct_fields.items() if key in peer_averages]
        render_kv_table(pairs, cols=4)

    relative_position = data.get('relative_position') or {}
    if relative_position:
        section_label("Relative Position vs Peers")
        badge = {'Discount': '🟢', 'Premium': '🔴', 'Inline': '⚪', 'Superior': '🟢', 'Below': '🔴'}
        label_map = {'pe_ratio': 'P/E', 'price_to_sales': 'P/S', 'price_to_book': 'P/B',
                     'roe': 'ROE', 'profit_margin': 'Profit Margin'}
        pairs = [(label_map.get(k, k), f"{badge.get(v, '')} {v}") for k, v in relative_position.items()]
        render_kv_table(pairs, cols=3)

    peer_insights = data.get('peer_insights') or []
    if peer_insights:
        section_label("Peer Insights")
        for insight in peer_insights:
            st.markdown(f"- {insight}")


def _render_technical_details(data: dict, ticker: str, fm: dict):
    """Local, denser replacement for the shared display_technical_details -
    same indicator/range/support-resistance fields as kv-tables instead of
    one st.write() per field across several 3-4 column st.columns() grids,
    same price chart (height trimmed from 900 to 650), and the raw
    st.json(technical_signals) dump replaced with a bullish/bearish count
    summary plus a clean bullet list. Note: signal_details strings aren't
    individually tagged bullish/bearish in the underlying data, so they can't
    be reliably split into two separate lists - only the aggregate counts can."""
    fm = fm or {}
    float_shares = fm.get('float_shares', 0) or 0
    shares_outstanding = fm.get('shares_outstanding', 0) or 0
    float_pct = min((float_shares / shares_outstanding * 100), 100.0) if shares_outstanding > 0 else 0

    section_label("Technical Indicators")
    render_kv_table([
        ("RSI (14)", _fmt_num(data.get('rsi_14'))),
        ("MACD", _fmt_num(data.get('macd_line'))),
        ("MA 20", _fmt_num(data.get('ma_20'))),
        ("MA 50", _fmt_num(data.get('ma_50'))),
        ("MA 200", _fmt_num(data.get('ma_200'))),
        ("ADX", _fmt_num(data.get('adx'))),
        ("ATR %", _fmt_num(data.get('atr_percent'), suffix="%")),
        ("Trend", data.get('trend', 'N/A')),
        ("Volume Trend", data.get('volume_trend', 'N/A')),
        ("BB Upper", f"${data.get('bb_upper', 0) or 0:.2f}"),
        ("BB Middle", f"${data.get('bb_middle', 0) or 0:.2f}"),
        ("BB Lower", f"${data.get('bb_lower', 0) or 0:.2f}"),
    ], cols=4)

    section_label("Range & Float")
    render_kv_table([
        ("30d High", f"${(data.get('price_30d_high', 0) or 0):.2f}"),
        ("30d Low", f"${(data.get('price_30d_low', 0) or 0):.2f}"),
        ("30d Fluctuation", f"{(data.get('price_30d_fluctuation', 0) or 0):.1f}%"),
        ("52w High", f"${(data.get('high_52w', 0) or 0):.2f}"),
        ("52w Low", f"${(data.get('low_52w', 0) or 0):.2f}"),
        ("Volatility (Ann)", f"{(data.get('volatility_annual', 0) or 0) * 100:.1f}%"),
        ("Float Shares", f"{float_shares / 1e6:.0f}M"),
        ("Float %", f"{float_pct:.1f}%"),
        ("Shares Outstanding", f"{shares_outstanding / 1e6:.0f}M"),
    ], cols=3)

    support_resistance = data.get('support_resistance') or {}
    if support_resistance:
        section_label("Support & Resistance")
        support_levels = support_resistance.get('support_levels') or []
        resistance_levels = support_resistance.get('resistance_levels') or []
        level_pairs = [(f"Support S{i}", f"${lvl:.2f}") for i, lvl in enumerate(support_levels, 1)]
        level_pairs += [(f"Resistance R{i}", f"${lvl:.2f}") for i, lvl in enumerate(resistance_levels, 1)]
        if level_pairs:
            render_kv_table(level_pairs, cols=4)
        else:
            st.caption("No support/resistance levels calculated")

        fibonacci = support_resistance.get('fibonacci') or {}
        if fibonacci:
            st.markdown("**Fibonacci Retracement**")
            render_kv_table([(level.replace('level_', ''), f"${value:.2f}") for level, value in fibonacci.items()], cols=4)

        pivots = support_resistance.get('pivot_points') or {}
        if pivots:
            st.markdown("**Pivot Points**")
            render_kv_table([
                ("Pivot", f"${pivots.get('pivot', 0):.2f}"),
                ("R1", f"${pivots.get('r1', 0):.2f}"),
                ("R2", f"${pivots.get('r2', 0):.2f}"),
                ("S1", f"${pivots.get('s1', 0):.2f}"),
                ("S2", f"${pivots.get('s2', 0):.2f}"),
            ], cols=5)

    if ticker:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2y")

            if not hist.empty:
                section_label("Price Chart with Indicators")
                st.caption("Click legend items to show/hide indicators")

                sma_20 = hist['Close'].rolling(window=20).mean()
                std_20 = hist['Close'].rolling(window=20).std()
                bb_upper = sma_20 + (std_20 * 2)
                bb_lower = sma_20 - (std_20 * 2)
                ma_50 = hist['Close'].rolling(window=50).mean()
                ma_200 = hist['Close'].rolling(window=200).mean()

                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))

                exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
                exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()

                import plotly.graph_objects as go
                from plotly.subplots import make_subplots

                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                                     row_heights=[0.4, 0.15, 0.225, 0.225],
                                     subplot_titles=('Price with Indicators', 'Volume', 'RSI (14)', 'MACD'))

                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='Price', line=dict(color='blue', width=2)), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=bb_upper, name='BB Upper', line=dict(color='gray', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=sma_20, name='BB Middle (MA20)', line=dict(color='orange', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=bb_lower, name='BB Lower', line=dict(color='gray', width=1, dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=ma_50, name='MA50', line=dict(color='green', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=ma_200, name='MA200', line=dict(color='red', width=1.5)), row=1, col=1)

                colors = ['red' if hist['Close'].iloc[i] < hist['Open'].iloc[i] else 'green' for i in range(len(hist))]
                fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volume', marker_color=colors), row=2, col=1)

                fig.add_trace(go.Scatter(x=hist.index, y=rsi, name='RSI', line=dict(color='purple', width=1.5)), row=3, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)

                fig.add_trace(go.Scatter(x=hist.index, y=macd, name='MACD', line=dict(color='blue', width=1.5)), row=4, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=signal, name='Signal', line=dict(color='red', width=1.5)), row=4, col=1)

                fig.update_layout(
                    height=650,
                    hovermode='x unified',
                    showlegend=True,
                    legend=dict(yanchor="top", y=1, xanchor="left", x=-0.5, bgcolor="rgba(255,255,255,0.9)", bordercolor="#ddd", borderwidth=1)
                )
                fig.update_yaxes(title_text="Price ($)", row=1, col=1)
                fig.update_yaxes(title_text="Volume", row=2, col=1)
                fig.update_yaxes(title_text="RSI", row=3, col=1)
                fig.update_yaxes(title_text="MACD", row=4, col=1)

                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not load price chart: {str(e)}")

    signals = data.get('technical_signals') or {}
    if signals:
        section_label("Signals")
        net = signals.get('net_signal', 0)
        render_kv_table([
            # bullish_signals/bearish_signals are weighted point totals, not item
            # counts - e.g. a single "Strong MA uptrend" is worth 3 points alone -
            # labeled "Score" rather than "Signals" so that isn't misread as a count.
            ("Bullish Score", f"🟢 {signals.get('bullish_signals', 0)}"),
            ("Bearish Score", f"🔴 {signals.get('bearish_signals', 0)}"),
            ("Net Score", f"{net:+d}" if isinstance(net, int) else net),
        ], cols=3)

        details = signals.get('signal_details') or []
        categories = signals.get('signal_categories') or []
        if details and len(categories) == len(details):
            # signal_categories (technical_analyzer.py) tags each detail string
            # bullish/bearish/neutral - grouped into columns so it's clear which
            # is which, rather than one flat list that reads as if everything's
            # under "bullish" since nothing visually distinguishes them.
            grouped = {'bullish': [], 'bearish': [], 'neutral': []}
            for text, cat in zip(details, categories):
                grouped.setdefault(cat, grouped['neutral']).append(text)
            sig_col1, sig_col2, sig_col3 = st.columns(3)
            for col, cat, icon in ((sig_col1, 'bullish', '🟢'), (sig_col2, 'bearish', '🔴'), (sig_col3, 'neutral', '⚪')):
                with col:
                    st.markdown(f"**{icon} {cat.title()}**")
                    if grouped[cat]:
                        for text in grouped[cat]:
                            st.markdown(f"- {text}")
                    else:
                        st.caption("None")
        elif details:
            # Older/cached result predating signal_categories - fall back to
            # an unclassified flat list rather than erroring.
            for item in details:
                st.markdown(f"- {item}")


# Analyzers with a local, denser renderer replacing the shared page's version -
# same underlying analysis data and (for dcf/analyst_consensus/business_model/
# industry_analysis/ai_insights/news_sentiment/startup) the exact same body
# content via the shared page's own inner display_*_details functions, just
# under OUR header instead of display_analyzer_tab's own st.metric one - that
# function bundles its header and body together, so getting a consistent
# Recommendation-pill/Target/Confidence header across every tab means calling
# the inner functions directly rather than the dispatch wrapper (which would
# render its own header a second time). All take (analysis_data, ticker,
# financial_metrics) for a uniform dispatch signature even where an argument
# goes unused.
_LOCAL_DETAIL_RENDERERS = {
    'comparable': lambda data, ticker, fm: _render_comparable_details(data),
    'technical': _render_technical_details,
    'dcf': lambda data, ticker, fm: display_dcf_details(data, ticker),
    'analyst_consensus': lambda data, ticker, fm: display_analyst_consensus_details(data),
    'business_model': lambda data, ticker, fm: display_business_model_details(data),
    'industry_analysis': lambda data, ticker, fm: display_industry_analysis_details(data),
    'ai_insights': lambda data, ticker, fm: display_ai_insights_details(data),
    'news_sentiment': lambda data, ticker, fm: display_news_details(data),
    'startup': lambda data, ticker, fm: display_startup_details(data),
}


# st.expander labels are plain text only (no markdown/HTML rendering), so the
# colored rec-pill badge used everywhere else on this page can't appear in a
# title - a colored emoji is the closest equivalent that's still plain text.
# Keyed off the same la-rec-* classes rec_pill_html uses, so an expander title
# always agrees with what the pill badge inside its own body would show.
_REC_CLASS_EMOJI = {
    'la-rec-strongbuy': '🟢', 'la-rec-buy': '🟢',
    'la-rec-hold': '🟡',
    'la-rec-sell': '🔴', 'la-rec-strongsell': '🔴',
}


def _analyzer_expander_label(analyses, key):
    """Recommendation/Target/Confidence summary for an expander's title
    itself, so it's visible collapsed without needing to open every analyzer
    to compare them."""
    label = ANALYZER_LABELS[key]
    analysis_data = analyses.get(key)
    if not analysis_data or 'error' in analysis_data:
        return label
    target = analysis_data.get('predicted_price', 0) or 0
    rec = analysis_data.get('recommendation', 'N/A')
    conf = analysis_data.get('confidence', 'N/A')
    target_str = f"${target:.2f}" if target else "N/A"
    emoji = _REC_CLASS_EMOJI.get(rec_pill_class(rec), '⚪')
    return f"{label}  —  {emoji} {rec} · {target_str} · {conf}"


def _render_analyzer_tab(ticker, analyses, key, fm, show_header=True):
    """Consistent Recommendation-pill/Target/Confidence header for every
    analyzer tab (previously only the JSON-fallback and locally-rewritten
    tabs got this; dcf/analyst_consensus/business_model/industry_analysis/
    ai_insights/news_sentiment/startup used display_analyzer_tab's own
    st.metric-based header, which looked different) - then dispatches to
    either a local renderer or the shared inner body-content function.
    show_header=False when the same Recommendation/Target/Confidence is
    already shown in the caller's expander title, to avoid repeating it."""
    analysis_data = analyses.get(key)
    if not analysis_data or 'error' in analysis_data:
        st.info(f"{ANALYZER_LABELS[key]} was not run for this stock" if not analysis_data
                else f"{ANALYZER_LABELS[key]} failed: {analysis_data.get('error', 'Unknown error')}")
        return

    if show_header:
        target = analysis_data.get('predicted_price', 0) or 0
        render_kv_table([
            ("Recommendation", rec_pill_html(analysis_data.get('recommendation', 'N/A'))),
            ("Target Price", f"${target:.2f}" if target else "N/A"),
            ("Confidence", analysis_data.get('confidence', 'N/A')),
        ], cols=3)

    if key in _LOCAL_DETAIL_RENDERERS:
        _LOCAL_DETAIL_RENDERERS[key](analysis_data, ticker, fm)
    else:
        section_label("Details")
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
        (k.replace('_', ' ').title(), rec_pill_html(v.get('recommendation', 'N/A')),
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
        section_label("Charts")
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

    section_label("Metrics")
    render_kv_table(_financial_figures_pairs(fm) + [
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

    section_label("Analysis Summary")
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

    with st.container(key="la_expander_configure"), st.expander("⚙️ Configure", expanded=not has_results):
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
        render_kv_table([
            ("Current Price", f"${current_price:.2f}" if current_price else "N/A"),
            ("Target Price", f"${target_price:.2f}" if target_price else "N/A"),
            ("Upside", upside_html),
            ("Recommendation", rec_pill_html(rec.get("recommendation", "N/A"))),
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
                    with st.container(key=f"la_expander_{k}"), st.expander(_analyzer_expander_label(analyses, k)):
                        _render_analyzer_tab(ticker, analyses, k, fm, show_header=False)


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
        section_label("Recent Theses")
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
    inject_theme_css()

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
            batch_timing = st.session_state.get('batch_timing')
            if batch_timing:
                render_kv_table([
                    ("Total Batch Time", f"{batch_timing['total_batch_time']}s"),
                    ("Avg Time/Stock", f"{batch_timing['avg_time_per_stock']}s"),
                    ("Parallel Workers", batch_timing.get('parallel_workers', 'N/A')),
                ], cols=3)
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

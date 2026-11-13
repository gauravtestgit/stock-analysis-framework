"""Centralized dashboard styling - a CSS token palette (light/dark via
prefers-color-scheme) plus small presentation helpers (kv-tables, section
labels, recommendation pills) shared across dashboard pages, instead of each
page hand-rolling its own inline CSS the way thesis_generation_full.py and
others historically have.

Originated on the Live Analysis page (hence the "la-" CSS prefix, kept as-is
rather than renamed since it's just a namespacing convention, not something
page-specific) and pulled out here so other pages can adopt the same design
language. Reskins Streamlit's default chrome via its data-testid hooks
(Streamlit 1.50) rather than replacing widgets outright, since every element
still needs to be a real interactive Streamlit component.
"""

from typing import Dict

import streamlit as st

THEME_CSS = """
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

/* Metric labels/values (st.metric is still used by some shared render
   functions that can't be touched, so this is a plain, box-free style
   rather than the card look, plus a wrap fallback so long labels/values
   can't clip the way a fixed-width metric box otherwise would). */
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

/* Stylized expander treatment (top accent stripe) - applied to any expander
   wrapped in a keyed container whose key starts with "la_expander_", e.g.
   st.container(key="la_expander_configure"). */
[class*="st-key-la_expander_"] [data-testid="stExpander"],
[class*="st-key-la_expander_"] [data-testid="stExpander"] > div,
[class*="st-key-la_expander_"] [data-testid="stExpander"] details {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    border-top: 3px solid var(--la-accent) !important;
    border-radius: 6px 6px 0 0 !important;
    overflow: hidden;
}
[class*="st-key-la_expander_"] [data-testid="stExpander"] summary {
    padding: 13px 16px !important;
    font-weight: 700 !important;
    color: var(--la-ink) !important;
    border: none !important;
    border-bottom: 1px solid var(--la-border) !important;
    box-shadow: none !important;
    transition: color 0.12s ease;
}
[class*="st-key-la_expander_"] [data-testid="stExpander"] summary:hover {
    color: var(--la-accent) !important;
}
[class*="st-key-la_expander_"] [data-testid="stExpander"] summary svg { color: var(--la-ink-faint); transition: color 0.12s ease; }
[class*="st-key-la_expander_"] [data-testid="stExpander"] summary:hover svg { color: var(--la-accent) !important; }
[class*="st-key-la_expander_"] [data-testid="stExpanderDetails"] {
    border: none !important;
    box-shadow: none !important;
    padding: 16px !important;
}

/* Density inside expander bodies - the shared display_*_details render
   functions (dcf/comparable/technical/analyst_consensus, in
   thesis_generation_full.py) use default-sized headers/dividers throughout;
   this tightens just those specifically inside an expander without touching
   that shared file. Scoped narrowly (headers/dividers only, not the vertical
   gap or a blanket <p> rule) after an earlier, broader version broke the DCF
   scenario table and caused text overlap - canvas-rendered elements like
   st.dataframe and Streamlit's own internal <p>-based component markup don't
   tolerate aggressive ancestor gap/margin overrides well. */
[class*="st-key-la_expander_"] [data-testid="stExpanderDetails"] h3,
[class*="st-key-la_expander_"] [data-testid="stExpanderDetails"] h4 {
    margin: 10px 0 6px !important;
    font-size: 0.95rem !important;
}
[class*="st-key-la_expander_"] [data-testid="stExpanderDetails"] hr {
    margin: 8px 0 !important;
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

/* Plain HTML tables (e.g. a methods summary) - lighter than st.dataframe's canvas grid */
table.la-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 2px 0; }
table.la-table th {
    text-align: left; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.03em;
    color: var(--la-ink-faint); font-weight: 600; padding: 6px 10px; border-bottom: 1px solid var(--la-border-strong);
}
table.la-table td { padding: 6px 10px; border-bottom: 1px solid var(--la-border); }
table.la-table tr:last-child td { border-bottom: none; }

/* Sleek "read more" popover trigger - plain text-link look, not a full button.
   Apply by wrapping the st.popover(...) call in st.container(key="la_summary_popover_wrap"). */
.st-key-la_summary_popover_wrap button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    color: var(--la-accent) !important; padding: 2px 0 !important; font-size: 0.8rem !important;
}
.st-key-la_summary_popover_wrap button:hover { text-decoration: underline; }
.st-key-la_summary_popover_wrap button p { color: var(--la-accent) !important; font-size: 0.8rem !important; }

/* Ticker link buttons in a summary table (opens the stock's full detail in a
   modal instead of an inline panel) - plain text-link look, monospace to
   match the ticker styling used elsewhere. Apply by wrapping the st.button(
   ticker, ...) call in st.container(key=f"la_ticker_link_{ticker}"). */
[class*="st-key-la_ticker_link_"] { border-bottom: 1px solid var(--la-border); }
[class*="st-key-la_ticker_link_"] button {
    background: transparent !important; border: none !important; box-shadow: none !important;
    color: var(--la-accent) !important; font-weight: 700 !important; font-family: var(--la-font-mono);
    padding: 4px 0 !important; justify-content: flex-start !important;
}
[class*="st-key-la_ticker_link_"] button:hover { text-decoration: underline; }
[class*="st-key-la_ticker_link_"] button p { color: var(--la-accent) !important; font-family: var(--la-font-mono); font-weight: 700 !important; }

/* Header/cell styling for the custom link-based summary table (replaces
   st.dataframe there, since its canvas cells can't hold a clickable element
   that calls back into Python). */
.la-linktable-h {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.03em;
    color: var(--la-ink-faint); font-weight: 600; padding: 4px 0 8px;
    border-bottom: 1px solid var(--la-border-strong);
}
.la-linktable-c {
    padding: 8px 0; font-family: var(--la-font-mono); font-variant-numeric: tabular-nums;
    border-bottom: 1px solid var(--la-border);
}

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

/* Support/Resistance number line - points spaced proportionally to their
   actual price gap (not evenly), so an unusually tight or wide gap between
   e.g. price and R1 is visually obvious, unlike a flat kv-table of the same
   numbers. Current price is always rendered ABOVE the track on its own stem
   line rather than inline with support/resistance labels, so it can never
   collide with one of them even when price sits right on top of a level. */
.la-ladder { position: relative; height: 96px; margin: 10px 0 6px; }
.la-ladder-track {
    position: absolute; top: 53px; left: 0; right: 0; height: 3px;
    border-radius: 2px;
    background: linear-gradient(to right, var(--la-bad) 0%, var(--la-border-strong) 45%, var(--la-border-strong) 55%, var(--la-good) 100%);
    opacity: 0.55;
}
.la-ladder-current-wrap {
    position: absolute; top: 0; transform: translateX(-50%);
    display: flex; flex-direction: column; align-items: center; width: max-content;
}
.la-ladder-current-label {
    font-size: 0.68rem; color: var(--la-accent); font-weight: 700; white-space: nowrap;
    font-family: var(--la-font-mono); font-variant-numeric: tabular-nums; text-align: center;
    margin-bottom: 2px;
}
.la-ladder-current-stem { width: 2px; height: 26px; background: var(--la-accent); opacity: 0.6; }
.la-ladder-current-dot {
    width: 13px; height: 13px; border-radius: 50%; margin-top: -6px;
    background: var(--la-accent); box-shadow: 0 0 0 4px var(--la-accent-soft);
    border: 2px solid var(--la-surface-raised);
}
.la-ladder-point { position: absolute; top: 53px; transform: translateX(-50%); text-align: center; }
.la-ladder-dot {
    width: 9px; height: 9px; border-radius: 50%; margin: -4.5px auto 6px;
    background: var(--la-ink-faint); border: 2px solid var(--la-surface-raised);
}
.la-ladder-point.la-ladder-support .la-ladder-dot { background: var(--la-bad); }
.la-ladder-point.la-ladder-resistance .la-ladder-dot { background: var(--la-good); }
.la-ladder-label {
    font-size: 0.68rem; color: var(--la-ink-faint); white-space: nowrap;
    font-family: var(--la-font-mono); font-variant-numeric: tabular-nums;
}
.la-ladder-label-name {
    display: block; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.03em; font-size: 0.62rem; font-family: var(--la-font-ui);
}
/* When two support (or two resistance) levels sit close together in price,
   their centered labels below the track would overlap - stack the label
   into a lower row instead, while the dot stays exactly on its true
   proportional position on the track. */
.la-ladder-point.la-ladder-row1 .la-ladder-label { margin-top: 17px; }
.la-ladder-point.la-ladder-row2 .la-ladder-label { margin-top: 34px; }
</style>
"""


def inject_theme_css():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def rec_pill_class(rec: str) -> str:
    return "la-rec-" + rec.lower().replace(" ", "").replace("-", "")


def rec_pill_html(rec: str) -> str:
    return f'<span class="la-rec-pill {rec_pill_class(rec)}">{rec}</span>'


def section_label(text: str):
    """One consistent sub-section header style, used across every tab instead
    of ad hoc st.markdown("###"/"####") calls at varying heading levels."""
    st.markdown(f'<div class="la-section-label">{text}</div>', unsafe_allow_html=True)


def _render_ladder(current_price, points):
    """Shared number-line renderer: current price always drawn ABOVE the
    track on its own connector stem (so it can never collide with another
    label no matter how close it sits to one), while every other `points`
    entry - (label, value, 'support'|'resistance') - sits on the track at
    its true proportional position, falling back to row-stacking if two of
    them land close enough together to collide with each other."""
    if current_price is None or not points:
        return

    values = [current_price] + [p[1] for p in points]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0

    def pos(v):
        return 6 + ((v - lo) / span) * 88  # 6-94% so end labels aren't clipped

    # points is already in ascending value order, so raw positions are
    # monotonic - walk left to right and drop any point whose label would sit
    # too close to the previous one in the same row into the next row down
    # instead (dot position is untouched; only the label is restacked).
    MIN_GAP_PCT = 11.0
    last_left_in_row: Dict[int, float] = {}
    rows = []
    for _, value, _ in points:
        left = pos(value)
        row = 0
        while row in last_left_in_row and left - last_left_in_row[row] < MIN_GAP_PCT:
            row += 1
        last_left_in_row[row] = left
        rows.append(row)
    max_row = max(rows) if rows else 0

    html_points = ''.join(
        f'<div class="la-ladder-point la-ladder-{kind} la-ladder-row{row}" style="left:{pos(value):.1f}%;">'
        f'<div class="la-ladder-dot"></div>'
        f'<div class="la-ladder-label"><span class="la-ladder-label-name">{label}</span>${value:,.2f}</div>'
        f'</div>'
        for (label, value, kind), row in zip(points, rows)
    )
    current_html = (
        f'<div class="la-ladder-current-wrap" style="left:{pos(current_price):.1f}%;">'
        f'<div class="la-ladder-current-label"><span class="la-ladder-label-name">Current Price</span>${current_price:,.2f}</div>'
        f'<div class="la-ladder-current-stem"></div>'
        f'<div class="la-ladder-current-dot"></div>'
        f'</div>'
    )
    container_style = f'height:{96 + max_row * 17}px;' if max_row else ''
    st.markdown(
        f'<div class="la-ladder" style="{container_style}"><div class="la-ladder-track"></div>{current_html}{html_points}</div>',
        unsafe_allow_html=True,
    )


def render_price_ladder(current_price, support_levels, resistance_levels):
    """Horizontal number-line: S2--S1--(price on a stem above)--R1--R2."""
    supports = [lvl for lvl in (support_levels or []) if lvl]
    resistances = [lvl for lvl in (resistance_levels or []) if lvl]
    if not supports and not resistances:
        return

    # support_levels[0] is S1 (closest below price), support_levels[1] is S2
    # (further below), etc. - reverse so the furthest support renders
    # leftmost: S2, S1, ..., R1, R2.
    points = [(f"S{len(supports) - i}", lvl, 'support') for i, lvl in enumerate(reversed(supports))]
    points += [(f"R{i + 1}", lvl, 'resistance') for i, lvl in enumerate(resistances)]
    _render_ladder(current_price, points)


def render_rsi_target_ladder(current_price, price_low, price_high, rsi_low, rsi_high):
    """Horizontal number-line showing the price range a target RSI band maps
    to (see project_rsi_target_price_range) - reuses the same track/stem
    visual as render_price_ladder, with the band's low/high price in place
    of support/resistance."""
    if price_low is None or price_high is None:
        return
    points = [
        (f"RSI {rsi_low:.0f}", price_low, 'support'),
        (f"RSI {rsi_high:.0f}", price_high, 'resistance'),
    ]
    _render_ladder(current_price, points)


def render_kv_table(pairs, cols=2):
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

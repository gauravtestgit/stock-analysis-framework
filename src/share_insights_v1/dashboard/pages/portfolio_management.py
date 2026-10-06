"""Current Portfolio page: create multiple named portfolios of stock/ETF
holdings (ticker + shares), see live market value per holding, and push a
portfolio's tickers into the existing (shared, session-state) watchlist so
they can be run through Live Analysis - see
src/share_insights_v1/api/portfolios.py for the backing API.

Not admin-gated (unlike Stock Management) - any logged-in user manages their
own portfolios, scoped server-side by owner_username = st.session_state.username.
"""

import os
import sys

import requests
import streamlit as st

# Add project root to path for absolute imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.watchlist_component import render_watchlist_header, get_watchlist

API_BASE = "http://localhost:8000/api/portfolios"


def _fmt_money(value) -> str:
    """Plain 2-decimal comma-formatted currency - utils.formatters.format_currency
    scales to B/M/K (built for company-level metrics like market cap), which loses
    precision for a personal portfolio's per-holding/total values (e.g. a $5,200
    holding would show as "$5.2K")."""
    return f"${value:,.2f}"


def _error_detail(exc: Exception) -> str:
    """requests.HTTPError carries the FastAPI error body (e.g. "Portfolio 'X'
    already exists") in exc.response - surface that instead of the generic
    "400 Client Error" message when available."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
            if detail:
                return detail
        except Exception:
            pass
    return str(exc)


def _api_get(path, **params):
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API request failed: {_error_detail(e)}")
        return None


def _api_post(path, json=None):
    try:
        resp = requests.post(f"{API_BASE}{path}", json=json, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API request failed: {_error_detail(e)}")
        return None


def _api_delete(path):
    try:
        resp = requests.delete(f"{API_BASE}{path}", timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API request failed: {_error_detail(e)}")
        return None


def _render_create_portfolio_form(username: str, key_suffix: str = ""):
    with st.form(f"create_portfolio_form{key_suffix}", clear_on_submit=True):
        name = st.text_input("Portfolio name", placeholder="e.g. Long-Term Growth")
        submitted = st.form_submit_button("Create Portfolio")
        if submitted:
            if not name.strip():
                st.error("Portfolio name cannot be empty")
            else:
                result = _api_post("/", json={"name": name.strip(), "owner_username": username})
                if result:
                    # Seed the selectbox's own widget-state key directly (not just an
                    # index= passed to it) - "portfolio_selector" is a persistent key,
                    # so once it holds a value from any prior render, Streamlit ignores
                    # index= on every later render and keeps showing the old selection.
                    # Writing the key itself is the only thing that actually overrides it.
                    st.session_state["portfolio_selector"] = result["name"]
                    st.toast(f"Created portfolio '{result['name']}'")
                    st.rerun()


def _render_holdings(portfolio: dict):
    portfolio_id = portfolio["id"]
    priced = _api_get(f"/{portfolio_id}/holdings/priced")
    holdings = priced.get("holdings", []) if priced else []

    if holdings:
        total_value = priced.get("total_market_value", 0.0)
        st.metric("Total Market Value", _fmt_money(total_value))

        header = st.columns([2, 2, 2, 2, 2, 1])
        for col, label in zip(header, ["Ticker", "Shares", "Current Price", "Market Value", "% of Portfolio", ""]):
            col.markdown(f"**{label}**")

        for h in holdings:
            cols = st.columns([2, 2, 2, 2, 2, 1])
            cols[0].write(h["ticker"] + (" ⚠️" if h.get("price_stale") else ""))
            cols[1].write(f"{h['shares']:,.4g}")
            cols[2].write(_fmt_money(h["current_price"]) if h["current_price"] is not None else "N/A")
            cols[3].write(_fmt_money(h["market_value"]) if h["market_value"] is not None else "N/A")
            pct = (h["market_value"] / total_value * 100) if h.get("market_value") and total_value else 0
            cols[4].write(f"{pct:.1f}%")
            if cols[5].button("×", key=f"remove_holding_{h['id']}", help=f"Remove {h['ticker']}"):
                _api_delete(f"/{portfolio_id}/holdings/{h['id']}")
                st.rerun()
    else:
        st.info("No holdings yet - add one below.")

    st.markdown("---")
    st.markdown("**Add / Update Holding**")
    with st.form(f"add_holding_form_{portfolio_id}", clear_on_submit=True):
        add_col1, add_col2, add_col3 = st.columns([2, 2, 1])
        ticker = add_col1.text_input("Ticker", placeholder="e.g. AAPL")
        shares = add_col2.number_input("Shares", min_value=0.0, step=1.0, format="%.4f")
        add_col3.markdown("<br>", unsafe_allow_html=True)
        submitted = add_col3.form_submit_button("Add")
        if submitted:
            if not ticker.strip():
                st.error("Ticker cannot be empty")
            elif shares <= 0:
                st.error("Shares must be greater than 0")
            else:
                result = _api_post(f"/{portfolio_id}/holdings", json={"ticker": ticker.strip(), "shares": shares})
                if result:
                    st.toast(f"{result['ticker']}: now {result['shares']:,.4g} shares")
                    st.rerun()

    st.markdown("---")
    if st.button("➕ Add All Holdings to Watchlist", disabled=not holdings, use_container_width=True):
        watchlist = get_watchlist()
        tickers = [h["ticker"] for h in holdings]
        added = [t for t in tickers if t not in watchlist]
        watchlist.extend(added)
        if added:
            st.toast(f"Added {len(added)} stock(s) to watchlist")
        else:
            st.info("All holdings already in watchlist")
        st.rerun()


def _render_portfolio_management(username: str):
    st.subheader("💼 My Portfolios")

    data = _api_get("/", owner_username=username)
    portfolios = data.get("portfolios", []) if data else []

    if not portfolios:
        st.info("You don't have any portfolios yet. Create your first one below.")
        _render_create_portfolio_form(username)
        return

    portfolio_names = [p["name"] for p in portfolios]

    # If the previously-selected portfolio no longer exists (just deleted, or a stale
    # value from before this session's portfolios changed), drop it so the widget falls
    # back to its default instead of erroring - Streamlit rejects a stored key value
    # that isn't among the current options.
    if st.session_state.get("portfolio_selector") not in portfolio_names:
        st.session_state.pop("portfolio_selector", None)

    select_col, new_col = st.columns([3, 1])
    with select_col:
        selected_name = st.selectbox("Portfolio", options=portfolio_names, key="portfolio_selector")
    selected_portfolio = next(p for p in portfolios if p["name"] == selected_name)

    with new_col:
        with st.popover("+ New Portfolio", use_container_width=True):
            _render_create_portfolio_form(username, key_suffix="_popover")

    delete_col1, delete_col2 = st.columns([3, 1])
    with delete_col2:
        confirm = st.checkbox("Confirm delete", key=f"confirm_delete_{selected_portfolio['id']}")
        if st.button("🗑️ Delete Portfolio", disabled=not confirm, use_container_width=True):
            _api_delete(f"/{selected_portfolio['id']}")
            st.session_state.pop("portfolio_selector", None)
            st.toast(f"Deleted portfolio '{selected_portfolio['name']}'")
            st.rerun()

    st.markdown(f"### {selected_portfolio['name']}")
    _render_holdings(selected_portfolio)


def main():
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return

    render_navigation()
    st.title("💼 Current Portfolio")
    show_disclaimer()
    render_watchlist_header()

    if st.button("← Back to Main Dashboard"):
        st.switch_page("main_dashboard.py")

    _render_portfolio_management(st.session_state.username)


if __name__ == "__main__":
    main()

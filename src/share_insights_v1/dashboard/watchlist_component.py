import streamlit as st

def init_watchlist():
    """Initialize watchlist in session state"""
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []

def show_watchlist_sidebar():
    """Show watchlist component in sidebar"""
    init_watchlist()
    
    st.sidebar.header("📋 Stock Watchlist")
    
    # Add stock input
    new_stock = st.sidebar.text_input("Add Stock(s):", placeholder="Enter tickers separated by spaces (e.g., AAPL MSFT GOOGL)")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Add", key="add_stock"):
            if new_stock:
                tickers = [ticker.strip().upper() for ticker in new_stock.split() if ticker.strip()]
                added_count = 0
                for ticker in tickers:
                    if ticker not in st.session_state.watchlist:
                        st.session_state.watchlist.append(ticker)
                        added_count += 1
                if added_count > 0:
                    st.sidebar.success(f"Added {added_count} stock(s)")
                else:
                    st.sidebar.info("All stocks already in watchlist")
    
    with col2:
        if st.button("Clear All", key="clear_watchlist"):
            st.session_state.watchlist = []
            st.sidebar.success("Watchlist cleared")
    
    # Show current watchlist
    if st.session_state.watchlist:
        st.sidebar.write(f"**Watchlist ({len(st.session_state.watchlist)} stocks):**")
        
        for i, stock in enumerate(st.session_state.watchlist):
            col1, col2 = st.sidebar.columns([3, 1])
            with col1:
                st.write(f"• {stock}")
            with col2:
                if st.button("×", key=f"remove_{i}", help=f"Remove {stock}"):
                    st.session_state.watchlist.remove(stock)
        
        # Add analyze watchlist button
        st.sidebar.markdown("---")
        if st.sidebar.button("🔍 Analyze Watchlist", key="analyze_watchlist_btn", help="Navigate to detailed analysis page"):
            # Set page to detailed analysis
            st.session_state.current_page = "Detailed Stock Analysis"
            st.rerun()
    else:
        st.sidebar.info("No stocks in watchlist")

def render_watchlist_header():
    """Common watchlist widget shown in the main content area (a shared
    header) instead of the sidebar, so it's visible consistently across
    pages. Uses Streamlit's native bordered container rather than custom CSS
    so it renders the same regardless of whether a page has adopted the Live
    Analysis theme (components/theme.py)."""
    init_watchlist()
    watchlist = st.session_state.watchlist

    with st.container(border=True):
        header_col, add_col, add_btn_col, clear_col, analyze_col = st.columns([1.3, 3, 0.8, 0.8, 1.4])

        with header_col:
            st.markdown(f"**📋 Watchlist ({len(watchlist)})**")

        with add_col:
            new_stock = st.text_input(
                "Add Stock(s)",
                placeholder="Add tickers, e.g. AAPL MSFT GOOGL",
                key="watchlist_header_add_input",
                label_visibility="collapsed",
            )

        with add_btn_col:
            if st.button("Add", key="watchlist_header_add_btn", use_container_width=True):
                if new_stock:
                    tickers = [t.strip().upper() for t in new_stock.split() if t.strip()]
                    added = [t for t in tickers if t not in watchlist]
                    watchlist.extend(added)
                    if added:
                        st.toast(f"Added {len(added)} stock(s)")
                    st.rerun()

        with clear_col:
            if st.button("Clear", key="watchlist_header_clear_btn", use_container_width=True, disabled=not watchlist):
                st.session_state.watchlist = []
                st.rerun()

        with analyze_col:
            if st.button(
                "🔍 Analyze", key="watchlist_header_analyze_btn", use_container_width=True,
                disabled=not watchlist, help="Go to Live Analysis to run analysis on the watchlist",
            ):
                st.switch_page("pages/live_analysis.py")

        if watchlist:
            per_row = 8
            for i in range(0, len(watchlist), per_row):
                chunk = watchlist[i:i + per_row]
                cols = st.columns(per_row)
                for col, ticker in zip(cols, chunk):
                    with col:
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"`{ticker}`")
                        if c2.button("×", key=f"watchlist_header_remove_{ticker}", help=f"Remove {ticker}"):
                            watchlist.remove(ticker)
                            st.rerun()
        else:
            st.caption("No stocks in watchlist")


def add_stock_to_watchlist_button(ticker):
    """Add a button to add specific stock to watchlist"""
    init_watchlist()
    
    if ticker and ticker not in st.session_state.watchlist:
        if st.button(f"➕ Add {ticker} to Watchlist", key=f"add_{ticker}"):
            st.session_state.watchlist.append(ticker)
            st.success(f"Added {ticker} to watchlist")
    elif ticker in st.session_state.watchlist:
        st.info(f"{ticker} already in watchlist")

def get_watchlist():
    """Get current watchlist"""
    init_watchlist()
    return st.session_state.watchlist
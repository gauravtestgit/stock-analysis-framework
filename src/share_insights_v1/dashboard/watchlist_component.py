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
    new_stock = st.sidebar.text_input("Add Stock:", placeholder="Enter ticker (e.g., AAPL)")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Add", key="add_stock"):
            if new_stock and new_stock.upper() not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_stock.upper())
                st.sidebar.success(f"Added {new_stock.upper()}")
    
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
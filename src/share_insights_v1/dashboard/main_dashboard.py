import streamlit as st
from app import main as batch_dashboard
from detailed_analysis import show_detailed_analysis

# Page config
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main dashboard with navigation"""
    
    # Initialize page selection in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Batch Results Dashboard"
    
    # Import watchlist component
    from watchlist_component import show_watchlist_sidebar
    
    # Show watchlist in sidebar
    show_watchlist_sidebar()
    
    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    page_options = ["Batch Results Dashboard", "Detailed Stock Analysis", "Analyst Alignment Analysis", "Bullish Convergence Analysis"]
    
    # Get current page index
    try:
        current_index = page_options.index(st.session_state.current_page)
    except ValueError:
        current_index = 0
    
    page = st.sidebar.selectbox(
        "Choose Analysis Type:",
        page_options,
        index=current_index,
        key="page_selector"
    )
    
    # Update session state
    st.session_state.current_page = page
    
    if st.session_state.current_page == "Batch Results Dashboard":
        batch_dashboard()
    elif st.session_state.current_page == "Detailed Stock Analysis":
        show_detailed_analysis()
    elif st.session_state.current_page == "Analyst Alignment Analysis":
        from analyst_alignment import show_analyst_alignment
        show_analyst_alignment()
    elif st.session_state.current_page == "Bullish Convergence Analysis":
        from bullish_convergence_view import show_bullish_convergence
        show_bullish_convergence()

if __name__ == "__main__":
    main()
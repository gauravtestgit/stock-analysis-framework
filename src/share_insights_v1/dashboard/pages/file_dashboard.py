import streamlit as st
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import authentication
from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.app import main as batch_dashboard
from src.share_insights_v1.dashboard.detailed_analysis import show_detailed_analysis
from src.share_insights_v1.dashboard.analyst_alignment import show_analyst_alignment
from src.share_insights_v1.dashboard.bullish_convergence_view import show_bullish_convergence

def main():
    """Main dashboard with navigation"""
    # Check authentication
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return
    
    # Navigation bar
    render_navigation()
    
    # Show disclaimer
    show_disclaimer()
    
    # Initialize page selection in session state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Batch Results Dashboard"
    
    # Import and show watchlist component
    from src.share_insights_v1.dashboard.watchlist_component import show_watchlist_sidebar
    show_watchlist_sidebar()
    
    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    page_options = ["Batch Results Dashboard", "Detailed Stock Analysis", "Analyst Alignment Analysis", "Bullish Convergence Analysis"]
    
    page = st.sidebar.selectbox(
        "Choose Analysis Type:",
        page_options,
        index=page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0
    )
    
    # Update session state
    st.session_state.current_page = page
    
    if st.session_state.current_page == "Batch Results Dashboard":
        batch_dashboard()
    elif st.session_state.current_page == "Detailed Stock Analysis":
        show_detailed_analysis()
    elif st.session_state.current_page == "Analyst Alignment Analysis":
        show_analyst_alignment()
    elif st.session_state.current_page == "Bullish Convergence Analysis":
        show_bullish_convergence()

if __name__ == "__main__":
    main()
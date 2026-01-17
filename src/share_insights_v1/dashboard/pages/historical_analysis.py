import streamlit as st
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import authentication
from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.historical_analysis_functions import show_historical_analysis, show_bulk_analysis

def main():
    """Historical Analysis page"""
    # Check authentication
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return
    
    # Navigation bar
    render_navigation()
    
    # Show disclaimer
    show_disclaimer()
    
    # Back to main dashboard
    if st.button("← Back to Main Dashboard"):
        st.switch_page("main_dashboard.py")
    
    # Create tabs for different analysis views
    tab1, tab2 = st.tabs(["📊 Individual Analysis", "📈 Bulk Analysis"])
    
    with tab1:
        show_historical_analysis()
    
    with tab2:
        show_bulk_analysis()

if __name__ == "__main__":
    main()
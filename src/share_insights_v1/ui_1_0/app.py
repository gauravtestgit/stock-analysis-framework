import streamlit as st
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

from views.exchange_analysis_view import ExchangeAnalysisView

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="Stock Analysis UI 1.0",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Navigation
    st.sidebar.title("🚀 Stock Analysis UI 1.0")
    
    # View selection
    view_options = {
        "📊 Exchange Analysis": "exchange_analysis",
        "📈 Analyst Alignment": "analyst_alignment",  # Future implementation
        "📋 Watchlist Manager": "watchlist",  # Future implementation
        "💼 Portfolio Analyzer": "portfolio"  # Future implementation
    }
    
    selected_view = st.sidebar.selectbox(
        "Select View:",
        list(view_options.keys()),
        index=0
    )
    
    # Render selected view
    if view_options[selected_view] == "exchange_analysis":
        view = ExchangeAnalysisView()
        view.render()
    
    elif view_options[selected_view] == "analyst_alignment":
        st.title("📈 Analyst Alignment Dashboard")
        st.info("🚧 Coming Soon - Analyst alignment analysis view")
        st.markdown("""
        **Planned Features:**
        - Method performance comparison (DCF vs Technical vs Comparable)
        - Alignment categories visualization  
        - Divergence analysis with charts
        - Method-specific success rates
        """)
    
    elif view_options[selected_view] == "watchlist":
        st.title("📋 Watchlist Manager")
        st.info("🚧 Coming Soon - Watchlist management view")
        st.markdown("""
        **Planned Features:**
        - Create custom stock lists from analysis results
        - Track performance over time
        - Set price alerts and target notifications
        - Bulk re-analysis of watchlist stocks
        """)
    
    elif view_options[selected_view] == "portfolio":
        st.title("💼 Portfolio Analyzer")
        st.info("🚧 Coming Soon - Portfolio analysis view")
        st.markdown("""
        **Planned Features:**
        - Import existing portfolio positions
        - Analyze current holdings against framework recommendations
        - Risk assessment and diversification analysis
        - Rebalancing suggestions based on analysis scores
        """)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**UI 1.0** - Next Generation Dashboard")
    st.sidebar.markdown("Built with Streamlit & Component Architecture")

if __name__ == "__main__":
    main()
import streamlit as st
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.share_insights_v1.dashboard.login_page import check_authentication, logout, render_navigation
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.dashboard.watchlist_component import render_watchlist_header

def render_main_dashboard():
    """Render the main dashboard content (registered as the default page via
    st.Page in main() below - st.set_page_config lives there instead, since it
    must run once, first, before st.navigation() is constructed)."""
    # Check authentication
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return
    
    # Navigation bar
    render_navigation()
    
    st.title("📊 Stock Analysis Framework")
    
    # Show disclaimer
    show_disclaimer()
    st.markdown("*Comprehensive stock analysis with multiple valuation methods and database management*")

    render_watchlist_header()

    # Main dashboard content
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔍 Analysis Tools")
        
        # Database Dashboard
        if st.button("📊 Database Dashboard", use_container_width=True, help="View analysis results from PostgreSQL database"):
            st.switch_page("pages/database_dashboard.py")
        
        # Stock Management (Admin only)
        if st.session_state.user_role == "admin":
            if st.button("🗃️ Stock Management", use_container_width=True, help="Manage stock information database"):
                st.switch_page("pages/stock_management.py")
        else:
            st.button("🗃️ Stock Management", use_container_width=True, disabled=True, help="Admin access required")
        
        # Original Dashboard
        if st.button("📈 File-based Dashboard", use_container_width=True, help="Original file-based analysis dashboard"):
            st.switch_page("pages/file_dashboard.py")
        
        # Thesis Generation
        if st.button("📝 Thesis Generation", use_container_width=True, help="Generate professional investment theses"):
            st.switch_page("pages/thesis_generation_full.py")

        # Live Analysis
        if st.button("📈 Live Analysis", use_container_width=True, help="Analyze stocks now - single ticker or watchlist batch"):
            st.switch_page("pages/live_analysis.py")

        # Historical Analysis
        if st.button("📊 Historical Analysis", use_container_width=True, help="Track analysis evolution and performance over time"):
            st.switch_page("pages/historical_analysis.py")
    
    with col2:
        st.subheader("⚙️ System Information")
        
        # User info
        st.info(f"""
        **Current User:** {st.session_state.username}
        **Role:** {st.session_state.user_role}
        **Access Level:** {'Full Access' if st.session_state.user_role == 'admin' else 'Analyst Access'}
        """)
        
        # System features
        st.markdown("### 🚀 Available Features")
        
        features = [
            "📊 **Database Dashboard** - Real-time PostgreSQL analysis results",
            "📈 **File Dashboard** - CSV-based analysis viewing",
            "📝 **Thesis Generation** - AI-powered investment thesis creation",
            "📊 **Historical Analysis** - Track analysis evolution over time",
        ]
        
        if st.session_state.user_role == "admin":
            features.append("🗃️ **Stock Management** - Database administration")
        
        for feature in features:
            st.markdown(f"- {feature}")
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("🎯 Analysis Methods", "8+")
    
    with col2:
        st.metric("📊 Exchanges", "4")
    
    with col3:
        st.metric("🔄 Real-time Data", "✅")

def main():
    st.set_page_config(
        page_title="Stock Analysis Dashboard",
        page_icon="📊",
        layout="wide"
    )

    # Grouped sidebar nav - only the actively-used pages (Main Dashboard,
    # Login, Live Analysis, Historical Analysis) show up front; everything
    # else lives collapsed under "Under Work Pages" instead of Streamlit's
    # default flat, ungrouped listing of every file in pages/.
    pg = st.navigation({
        "Main": [
            st.Page(render_main_dashboard, title="Main Dashboard", icon="📊", default=True),
            st.Page("pages/login_page.py", title="Login", icon="🔐"),
            st.Page("pages/live_analysis.py", title="Live Analysis", icon="📈"),
            st.Page("pages/historical_analysis.py", title="Historical Analysis", icon="📊"),
        ],
        "Under Work Pages": [
            st.Page("pages/database_dashboard.py", title="Database Dashboard", icon="🗄️"),
            st.Page("pages/stock_management.py", title="Stock Management", icon="🗃️"),
            st.Page("pages/file_dashboard.py", title="File Dashboard", icon="📁"),
            st.Page("pages/prompt_management.py", title="Prompt Management", icon="🔧"),
            st.Page("pages/thesis_generation_full.py", title="Thesis Generation Full", icon="📝"),
        ],
    })
    pg.run()

if __name__ == "__main__":
    main()
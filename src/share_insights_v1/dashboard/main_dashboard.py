import streamlit as st
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.share_insights_v1.dashboard.login_page import check_authentication, logout, render_navigation

def render_main_dashboard():
    """Render the main dashboard with navigation"""
    st.set_page_config(
        page_title="Stock Analysis Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    # Check authentication
    if not check_authentication():
        st.switch_page("pages/login_page.py")
        return
    
    # Navigation bar
    render_navigation()
    
    st.title("📊 Stock Analysis Framework")
    st.markdown("*Comprehensive stock analysis with multiple valuation methods and database management*")
    
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
    render_main_dashboard()

if __name__ == "__main__":
    main()
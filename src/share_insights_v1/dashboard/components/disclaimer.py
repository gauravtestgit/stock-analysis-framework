import streamlit as st

def show_disclaimer():
    """Display prominent legal disclaimer on every page"""
    st.markdown("""
    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; margin-bottom: 20px; border-radius: 5px;">
        <h4 style="color: #856404; margin-top: 0;">⚠️ Important Disclaimer</h4>
        <p style="color: #856404; margin-bottom: 0; font-size: 14px;">
        <strong>NOT FINANCIAL ADVICE:</strong> This tool is for educational and research purposes only. 
        It is not certified financial advice and should not be used as the sole basis for investment decisions. 
        Always consult with a qualified financial advisor before making investment decisions. 
        Past performance does not guarantee future results. Use at your own risk.
        </p>
    </div>
    """, unsafe_allow_html=True)

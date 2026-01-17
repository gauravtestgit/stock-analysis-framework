import streamlit as st
import os
from pathlib import Path
from src.share_insights_v1.utils.prompt_loader import ThesisPromptLoader
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer

def show_prompt_management():
    """Show prompt management interface for thesis generation"""
    
    st.title("🔧 Prompt Management")
    show_disclaimer()
    st.markdown("*Manage and edit thesis generation prompt templates*")
    
    # Initialize prompt loader
    prompt_loader = ThesisPromptLoader()
    
    # Get available prompts
    available_prompts = prompt_loader.list_available_prompts()
    
    # Add refresh button to clear cache
    if st.sidebar.button("🔄 Refresh Prompts"):
        prompt_loader._prompt_cache.clear()
        available_prompts = prompt_loader.list_available_prompts()
        st.rerun()
    
    # Sidebar for prompt selection
    st.sidebar.subheader("📝 Prompt Templates")
    selected_prompt = st.sidebar.selectbox(
        "Select Prompt Template:",
        available_prompts,
        format_func=lambda x: {
            'bull_case': '🚀 Bull Case',
            'bear_case': '🐻 Bear Case', 
            'objective': '⚖️ Objective',
            'base': '📋 Base Template'
        }.get(x, x.replace('_', ' ').title())
    )
    
    # Show prompt info
    prompt_info = prompt_loader.get_prompt_info(selected_prompt)
    if prompt_info:
        st.sidebar.markdown(f"**File:** {Path(prompt_info['file_path']).name}")
        st.sidebar.markdown(f"**Size:** {prompt_info['file_size']:,} bytes")
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.subheader("🎛️ Actions")
        
        if st.button("📥 Load Template", use_container_width=True):
            st.session_state.current_prompt = prompt_loader.load_prompt(selected_prompt)
            st.session_state.selected_prompt_type = selected_prompt
            st.success(f"Loaded {selected_prompt} template")
        
        if st.button("💾 Save Changes", use_container_width=True):
            if 'edited_prompt' in st.session_state and 'selected_prompt_type' in st.session_state:
                save_prompt_template(st.session_state.selected_prompt_type, st.session_state.edited_prompt)
                st.success("Template saved successfully!")
            else:
                st.error("No changes to save")
        
        if st.button("🔄 Reset to Default", use_container_width=True):
            if 'selected_prompt_type' in st.session_state:
                # Clear cache and reload
                prompt_loader._prompt_cache.clear()
                st.session_state.current_prompt = prompt_loader.load_prompt(st.session_state.selected_prompt_type)
                st.success("Reset to default template")
        
        st.markdown("---")
        
        # Template variables reference
        st.subheader("📋 Template Variables")
        with st.expander("Available Variables", expanded=False):
            variables = [
                "{ticker}", "{company_type}", "{target_price}", "{current_price_str}",
                "{market_cap}", "{pe_ratio}", "{revenue_growth}", "{strengths}",
                "{risks}", "{industry_outlook}", "{news_count}", "{segment_info}"
            ]
            for var in variables:
                st.code(var, language="text")
    
    with col1:
        st.subheader(f"✏️ Edit {selected_prompt.replace('_', ' ').title()} Template")
        
        # Load current prompt if not already loaded
        if 'current_prompt' not in st.session_state:
            st.session_state.current_prompt = prompt_loader.load_prompt(selected_prompt)
            st.session_state.selected_prompt_type = selected_prompt
        
        # Check if we switched prompt types
        if st.session_state.get('selected_prompt_type') != selected_prompt:
            st.session_state.current_prompt = prompt_loader.load_prompt(selected_prompt)
            st.session_state.selected_prompt_type = selected_prompt
        
        # Text editor for prompt
        edited_prompt = st.text_area(
            "Prompt Template:",
            value=st.session_state.current_prompt,
            height=600,
            help="Edit the prompt template. Use {variable_name} for dynamic content.",
            key="prompt_editor"
        )
        
        # Store edited prompt in session state
        st.session_state.edited_prompt = edited_prompt
        
        # Show character count
        char_count = len(edited_prompt)
        word_count = len(edited_prompt.split())
        st.caption(f"📊 {word_count:,} words, {char_count:,} characters")
        
        # Preview section
        if st.button("👁️ Preview with Sample Data"):
            show_prompt_preview(edited_prompt, selected_prompt)

def save_prompt_template(prompt_type: str, content: str):
    """Save edited prompt template to file"""
    
    prompt_file_map = {
        'bull_case': 'bull_case_prompt.txt',
        'bear_case': 'bear_case_prompt.txt',
        'objective': 'objective_case_prompt.txt',
        'base': 'base_thesis_prompt.txt'
    }
    
    if prompt_type not in prompt_file_map:
        st.error(f"Unknown prompt type: {prompt_type}")
        return
    
    # Get prompts directory
    prompts_dir = Path(__file__).parent.parent / "prompts" / "thesis_generation"
    prompt_file = prompts_dir / prompt_file_map[prompt_type]
    
    try:
        # Create backup
        backup_file = prompt_file.with_suffix('.txt.backup')
        if prompt_file.exists():
            backup_file.write_text(prompt_file.read_text(encoding='utf-8'), encoding='utf-8')
        
        # Save new content
        prompt_file.write_text(content, encoding='utf-8')
        
        # Clear cache so changes take effect
        prompt_loader = ThesisPromptLoader()
        prompt_loader._prompt_cache.clear()
        
    except Exception as e:
        st.error(f"Failed to save template: {str(e)}")

def show_prompt_preview(prompt_content: str, prompt_type: str):
    """Show preview of prompt with sample data"""
    
    st.subheader("🔍 Prompt Preview")
    
    # Sample data for preview
    sample_data = {
        'ticker': 'AAPL',
        'company_type': 'Large Cap Technology',
        'target_price': 185.50,
        'current_price_str': '$175.25',
        'market_cap': 2800000000000,
        'enterprise_value': 2750000000000,
        'beta': 1.25,
        'pe_ratio': 28.5,
        'ps_ratio': 7.2,
        'pb_ratio': 12.8,
        'ev_ebitda_multiple': 22.1,
        'gross_margin': 0.43,
        'operating_margin': 0.28,
        'net_margin': 0.24,
        'roe': 0.15,
        'roa': 0.12,
        'revenue_growth': 0.08,
        'earnings_growth': 0.12,
        'debt_to_equity': 1.73,
        'current_ratio': 1.05,
        'quick_ratio': 0.95,
        'free_cash_flow': 95000000000,
        'cash_per_share': 15.25,
        'book_value_per_share': 4.85,
        'dividend_yield': 0.0045,
        'payout_ratio': 0.15,
        'total_revenue': 394000000000,
        'latest_net_income': 97000000000,
        'latest_operating_income': 114000000000,
        'latest_gross_profit': 170000000000,
        'latest_operating_cf': 104000000000,
        'latest_capital_expenditures': 11000000000,
        'industry': 'Consumer Electronics',
        'sector': 'Technology',
        'segment_info': '\n- iPhone: 52.4% of revenue\n- Services: 22.3% of revenue\n- Mac: 10.1% of revenue',
        'net_income_growth': 5.8,
        'operating_cf_growth': 7.2,
        'dcf_calculation_details': '\n\n**DCF CALCULATION VALIDATION:**\n- WACC: 8.5%\n- FCF CAGR: 6.2%\n- Terminal Growth: 2.5%',
        'startup_calculation_details': '',
        'average_target': 182.75,
        'consensus_strength': 'High',
        'method_agreement': '8/10 methods bullish',
        'strengths': 'Strong brand loyalty, Ecosystem lock-in, Premium pricing power, Innovation pipeline, Cash generation',
        'risks': 'China dependency, Regulatory scrutiny, Market saturation, Competition, Supply chain risks',
        'key_developments': 'iPhone 15 launch success, Services growth acceleration, Vision Pro announcement',
        'sentiment_rating': 'Positive',
        'news_count': 15,
        'news_sources_with_urls': 'Reuters: Apple reports strong Q4... (https://reuters.com/apple), Bloomberg: iPhone demand... (https://bloomberg.com/iphone)',
        'industry_outlook': 'Positive',
        'competitive_position': 'Strong',
        'regulatory_risk': 'Medium',
        'esg_score': 7.5,
        'business_segments': 'iPhone, Services, Mac, iPad, Wearables',
        'revenue_breakdown': 'iPhone (52.4%), Services (22.3%), Mac (10.1%), iPad (8.7%), Wearables (6.5%)',
        'data_source': 'SEC 10-K Filing',
        'revenue_diversification': 'Moderate',
        'thesis_type_lower': prompt_type.replace('_', ' ').lower()
    }
    
    try:
        # Format prompt with sample data
        formatted_prompt = prompt_content.format(**sample_data)
        
        # Display in expandable section
        with st.expander("📄 Formatted Prompt Preview", expanded=True):
            st.markdown(
                f"""
                <div style="
                    background-color: #f8f9fa;
                    padding: 15px;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                    max-height: 400px;
                    overflow-y: auto;
                    white-space: pre-wrap;
                ">
                    {formatted_prompt}
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # Show statistics
        preview_word_count = len(formatted_prompt.split())
        preview_char_count = len(formatted_prompt)
        st.caption(f"📊 Preview: {preview_word_count:,} words, {preview_char_count:,} characters")
        
    except KeyError as e:
        st.error(f"Missing template variable: {e}")
        st.info("Make sure all variables in the template are defined in the sample data.")
    except Exception as e:
        st.error(f"Error formatting prompt: {str(e)}")

def main():
    """Main function for prompt management page"""
    show_prompt_management()

if __name__ == "__main__":
    main()

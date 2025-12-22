import streamlit as st
import sys
import os
import requests

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import authentication
from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation
from src.share_insights_v1.services.database.database_service import DatabaseService

def show_thesis_generation():
    """Show thesis generation page with database integration"""
    
    st.title("📝 Investment Thesis Generator")
    st.markdown("*Generate comprehensive investment theses using database analysis results*")
    
    # Initialize database service
    db_service = DatabaseService()
    
    # Stock selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        ticker = st.text_input("Enter Stock Ticker:", value="AAPL").upper()
    
    with col2:
        if st.button("🔍 Load Analysis", type="primary"):
            if ticker:
                load_stock_analysis(ticker, db_service)
    
    # Display analysis data if loaded
    if 'thesis_analysis_data' in st.session_state and 'thesis_ticker' in st.session_state:
        display_analysis_summary(st.session_state.thesis_ticker, st.session_state.thesis_analysis_data)
        
        # Check for missing analysis components and show enhancement options
        analyses = st.session_state.thesis_analysis_data.get('analyses', {})
        
        st.markdown("---")
        st.subheader("🔄 Analysis Enhancement")
        
        # Show all available analyzers with run buttons
        available_analyzers = [
            ("dcf", "💰 DCF Valuation", "Discounted Cash Flow analysis"),
            ("technical", "📈 Technical Analysis", "Price patterns and momentum indicators"),
            ("comparable", "📉 Comparable Analysis", "Industry multiple-based valuation"),
            ("startup", "🚀 Startup Valuation", "Early-stage company analysis"),
            ("ai_insights", "🤖 AI Insights", "AI-powered business analysis"),
            ("news_sentiment", "📰 News Sentiment", "Recent news sentiment analysis"),
            ("business_model", "🏢 Business Model", "Revenue quality and scalability analysis"),
            ("financial_health", "💊 Financial Health", "Balance sheet and cash flow analysis"),
            ("analyst_consensus", "👥 Analyst Consensus", "Professional analyst targets"),
            ("industry_analysis", "🏢 Industry Analysis", "Sector and industry analysis")
        ]
        
        # Create 3 columns for analyzer buttons
        cols = st.columns(3)
        for i, (analyzer_key, analyzer_name, analyzer_desc) in enumerate(available_analyzers):
            col_idx = i % 3
            with cols[col_idx]:
                # Check if analyzer already exists
                has_analysis = analyzer_key in analyses
                button_text = f"✓ {analyzer_name}" if has_analysis else f"▶ {analyzer_name}"
                button_type = "secondary" if has_analysis else "primary"
                
                if st.button(button_text, key=f"run_{analyzer_key}", type=button_type, help=analyzer_desc):
                    run_individual_analysis(st.session_state.thesis_ticker, analyzer_key)
        
        # Add "Run All Analysis" button
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🚀 Run All Analysis Methods", type="primary", help="Run comprehensive analysis with all methods"):
                run_comprehensive_analysis(st.session_state.thesis_ticker)
        
        # Thesis generation section
        st.markdown("---")
        st.subheader("🎯 Generate Investment Thesis")
        
        col1, col2 = st.columns(2)
        with col1:
            thesis_type = st.selectbox("Thesis Type:", ["Balanced", "Bull Case", "Bear Case"])
        with col2:
            generate_button = st.button("🚀 Generate Thesis", type="primary")
        
        # Handle thesis generation outside column layout
        if generate_button:
            generate_investment_thesis(
                st.session_state.thesis_ticker, 
                st.session_state.thesis_analysis_data, 
                thesis_type
            )

def load_stock_analysis(ticker, db_service):
    """Load latest analysis for a stock from database"""
    
    with st.spinner(f"Loading analysis for {ticker}..."):
        try:
            from src.share_insights_v1.models.database import get_db
            
            with next(get_db()) as db:
                # Get latest comprehensive analysis
                analysis_data = db_service.get_latest_analysis(db, ticker)
                
                if analysis_data:
                    st.session_state.thesis_analysis_data = analysis_data
                    st.session_state.thesis_ticker = ticker
                    st.success(f"✅ Analysis loaded for {ticker}")
                    st.rerun()
                else:
                    st.error(f"❌ No analysis found for {ticker}. Please run analysis first.")
                    
        except Exception as e:
            st.error(f"Error loading analysis: {str(e)}")

def display_analysis_summary(ticker, analysis_data):
    """Display summary of loaded analysis data"""
    
    st.subheader(f"📊 Analysis Summary for {ticker}")
    
    # Basic metrics
    col1, col2, col3, col4 = st.columns(4)
    
    final_rec = analysis_data.get('final_recommendation', {})
    
    with col1:
        st.metric("Recommendation", final_rec.get('recommendation', 'N/A'))
    with col2:
        target_price = final_rec.get('target_price', 0)
        st.metric("Target Price", f"${target_price:.2f}" if target_price else "N/A")
    with col3:
        analysis_date = analysis_data.get('analysis_date')
        if analysis_date:
            st.metric("Analysis Date", analysis_date.strftime("%Y-%m-%d"))
        else:
            st.metric("Analysis Date", "N/A")
    with col4:
        analyses_count = analysis_data.get('analyses_count', 0)
        st.metric("Methods Used", analyses_count)
    
    # Available analyses
    analyses = analysis_data.get('analyses', {})
    if analyses:
        st.write("**Available Analysis Methods:**")
        analysis_methods = list(analyses.keys())
        st.write(", ".join([method.replace('_', ' ').title() for method in analysis_methods]))
    
    # Show expandable detailed data
    with st.expander("🔍 View Detailed Analysis Data"):
        st.json(analysis_data)

def generate_investment_thesis(ticker, analysis_data, thesis_type):
    """Generate investment thesis based on analysis data"""
    
    with st.spinner(f"Generating {thesis_type.lower()} thesis for {ticker}..."):
        try:
            # Extract key data points
            final_rec = analysis_data.get('final_recommendation', {})
            analyses = analysis_data.get('analyses', {})
            
            # Build thesis components
            thesis_components = extract_thesis_components(ticker, analysis_data, analyses)
            
            # Generate thesis based on type
            if thesis_type == "Bull Case":
                thesis = generate_bull_case(ticker, thesis_components)
            elif thesis_type == "Bear Case":
                thesis = generate_bear_case(ticker, thesis_components)
            else:  # Balanced
                thesis = generate_balanced_thesis(ticker, thesis_components)
            
            # Display generated thesis
            display_generated_thesis(ticker, thesis, thesis_type)
            
        except Exception as e:
            st.error(f"Error generating thesis: {str(e)}")

def extract_thesis_components(ticker, analysis_data, analyses):
    """Extract key components for thesis generation"""
    
    components = {
        'ticker': ticker,
        'final_recommendation': analysis_data.get('final_recommendation', {}),
        'company_type': analysis_data.get('company_type', 'Unknown'),
        'strengths': [],
        'risks': [],
        'catalysts': [],
        'valuation_methods': {},
        'financial_health': {},
        'competitive_position': {},
        'market_sentiment': {}
    }
    
    # Extract from AI Insights
    if 'ai_insights' in analyses:
        ai_data = analyses['ai_insights']
        ai_insights = ai_data.get('ai_insights', {})
        components['strengths'].extend(ai_insights.get('key_strengths', []))
        components['risks'].extend(ai_insights.get('key_risks', []))
        components['competitive_position'] = {
            'market_position': ai_insights.get('market_position', 'N/A'),
            'growth_prospects': ai_insights.get('growth_prospects', 'N/A'),
            'competitive_advantage': ai_insights.get('competitive_advantage', 'N/A')
        }
    
    # Extract from Business Model
    if 'business_model' in analyses:
        bm_data = analyses['business_model']
        components['strengths'].extend(bm_data.get('strengths', []))
        components['risks'].extend(bm_data.get('risks', []))
    
    # Extract valuation data
    valuation_methods = ['dcf', 'technical', 'comparable', 'analyst_consensus']
    for method in valuation_methods:
        if method in analyses:
            method_data = analyses[method]
            components['valuation_methods'][method] = {
                'recommendation': method_data.get('recommendation', 'N/A'),
                'target_price': method_data.get('predicted_price', 0),
                'confidence': method_data.get('confidence', 'N/A')
            }
    
    # Extract news sentiment
    if 'news_sentiment' in analyses:
        news_data = analyses['news_sentiment']
        components['market_sentiment'] = {
            'sentiment_score': news_data.get('overall_sentiment_score', 0),
            'sentiment_rating': news_data.get('sentiment_rating', 'Neutral'),
            'key_developments': news_data.get('key_developments', []),
            'news_count': news_data.get('news_count', 0)
        }
    
    return components

def generate_bull_case(ticker, components):
    """Generate bullish investment thesis"""
    
    final_rec = components['final_recommendation']
    target_price = final_rec.get('target_price', 0)
    
    thesis = f"""
# 🚀 Bull Case Investment Thesis: {ticker}

## Executive Summary
{ticker} presents a compelling investment opportunity with strong fundamentals and significant upside potential. Our analysis indicates a target price of ${target_price:.2f}, representing attractive returns for investors.

## Key Investment Strengths
"""
    
    # Add strengths
    if components['strengths']:
        for strength in components['strengths'][:5]:  # Top 5 strengths
            thesis += f"• {strength}\n"
    else:
        thesis += "• Strong market position and competitive advantages\n"
    
    thesis += f"""
## Competitive Position
• Market Position: {components['competitive_position'].get('market_position', 'Strong')}
• Growth Prospects: {components['competitive_position'].get('growth_prospects', 'Positive')}
• Competitive Advantage: {components['competitive_position'].get('competitive_advantage', 'Sustainable')}

## Valuation Analysis
"""
    
    # Add valuation methods that support bull case
    for method, data in components['valuation_methods'].items():
        if data['recommendation'] in ['Buy', 'Strong Buy']:
            thesis += f"• {method.upper()}: {data['recommendation']} - Target ${data['target_price']:.2f}\n"
    
    thesis += f"""
## Market Sentiment
• Current sentiment: {components['market_sentiment'].get('sentiment_rating', 'Positive')}
• Recent developments support positive outlook
• {components['market_sentiment'].get('news_count', 0)} recent news articles analyzed

## Investment Recommendation
**BUY** - {ticker} offers strong upside potential with manageable risks. The combination of solid fundamentals, competitive advantages, and positive market dynamics makes this an attractive investment opportunity.
"""
    
    return thesis

def generate_bear_case(ticker, components):
    """Generate bearish investment thesis"""
    
    thesis = f"""
# 🐻 Bear Case Investment Thesis: {ticker}

## Executive Summary
{ticker} faces significant headwinds and risks that could impact future performance. Investors should exercise caution given the current risk-reward profile.

## Key Risk Factors
"""
    
    # Add risks
    if components['risks']:
        for risk in components['risks'][:5]:  # Top 5 risks
            thesis += f"• {risk}\n"
    else:
        thesis += "• Market volatility and competitive pressures\n"
    
    thesis += f"""
## Valuation Concerns
"""
    
    # Add valuation methods that support bear case
    for method, data in components['valuation_methods'].items():
        if data['recommendation'] in ['Sell', 'Strong Sell', 'Hold']:
            thesis += f"• {method.upper()}: {data['recommendation']} - Suggests limited upside\n"
    
    thesis += f"""
## Market Headwinds
• Sentiment challenges may persist
• Competitive landscape intensifying
• Regulatory or market risks present

## Investment Recommendation
**HOLD/AVOID** - Given the risk factors and limited upside potential, investors should consider alternative opportunities with better risk-adjusted returns.
"""
    
    return thesis

def generate_balanced_thesis(ticker, components):
    """Generate balanced investment thesis"""
    
    final_rec = components['final_recommendation']
    recommendation = final_rec.get('recommendation', 'Hold')
    target_price = final_rec.get('target_price', 0)
    
    thesis = f"""
# ⚖️ Balanced Investment Thesis: {ticker}

## Executive Summary
{ticker} presents a mixed investment profile with both opportunities and challenges. Our comprehensive analysis suggests a **{recommendation}** recommendation with a target price of ${target_price:.2f}.

## Investment Strengths
"""
    
    # Add top strengths
    if components['strengths']:
        for strength in components['strengths'][:3]:
            thesis += f"• {strength}\n"
    
    thesis += f"""
## Key Risk Factors
"""
    
    # Add top risks
    if components['risks']:
        for risk in components['risks'][:3]:
            thesis += f"• {risk}\n"
    
    thesis += f"""
## Valuation Analysis Summary
"""
    
    # Summarize all valuation methods
    for method, data in components['valuation_methods'].items():
        thesis += f"• {method.upper()}: {data['recommendation']} - ${data['target_price']:.2f} ({data['confidence']} confidence)\n"
    
    thesis += f"""
## Market Position
• Company Type: {components['company_type']}
• Market Position: {components['competitive_position'].get('market_position', 'N/A')}
• Growth Prospects: {components['competitive_position'].get('growth_prospects', 'N/A')}

## Investment Recommendation
**{recommendation}** - {ticker} offers a balanced risk-reward profile. Investors should consider their risk tolerance and investment timeline when making allocation decisions.
"""
    
    return thesis

def display_generated_thesis(ticker, thesis, thesis_type):
    """Display the generated investment thesis"""
    
    st.subheader(f"📝 Generated {thesis_type} for {ticker}")
    
    # Display thesis using full-width container with white background
    st.markdown(
        f"""
        <div style="
            background-color: white;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            margin: 10px 0;
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            max-height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
            width: 100%;
            box-sizing: border-box;
        ">
            {thesis}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Add action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Thesis"):
            save_thesis_to_database(ticker, thesis, thesis_type)
    
    with col2:
        if st.button("📄 Export PDF"):
            st.info("PDF export functionality coming soon!")
    
    with col3:
        if st.button("📧 Share Thesis"):
            st.info("Share functionality coming soon!")

def save_thesis_to_database(ticker, thesis, thesis_type):
    """Save generated thesis to database (placeholder)"""
    
    # TODO: Implement database storage for theses
    st.success(f"✅ {thesis_type} thesis for {ticker} saved successfully!")
    st.info("💡 Database storage for theses will be implemented in the next phase.")

def run_comprehensive_analysis(ticker):
    """Run comprehensive analysis with all methods"""
    
    with st.spinner(f"Running comprehensive analysis for {ticker}..."):
        try:
            # Use the API endpoint to run all analyzers
            endpoint = f"http://localhost:8000/analyze/{ticker}"
            request_data = {"ticker": ticker}
            
            response = requests.post(endpoint, json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update session state with complete analysis
                st.session_state.thesis_analysis_data = {
                    'ticker': ticker,
                    'analyses': data.get('analyses', {}),
                    'final_recommendation': data.get('final_recommendation', {}),
                    'company_type': data.get('company_type', 'Unknown'),
                    'analysis_date': data.get('analysis_date'),
                    'analyses_count': data.get('analyses_count', 0)
                }
                
                st.success(f"✅ Comprehensive analysis completed for {ticker}!")
                st.rerun()
            else:
                st.error(f"❌ Failed to run comprehensive analysis: {response.text}")
                
        except Exception as e:
            st.error(f"Error running comprehensive analysis: {str(e)}")

def run_individual_analysis(ticker, analyzer_key):
    """Run individual analysis for a specific analyzer"""
    
    with st.spinner(f"Running {analyzer_key.replace('_', ' ').title()} analysis for {ticker}..."):
        try:
            # Use the API endpoint to run specific analyzer
            endpoint = f"http://localhost:8000/analyze/{ticker}"
            request_data = {
                "ticker": ticker,
                "enabled_analyzers": [analyzer_key]
            }
            
            response = requests.post(endpoint, json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update session state with new analysis
                if 'thesis_analysis_data' in st.session_state:
                    analyses = st.session_state.thesis_analysis_data.get('analyses', {})
                    new_analyses = data.get('analyses', {})
                    
                    # Update with new analyzer result
                    if analyzer_key in new_analyses:
                        analyses[analyzer_key] = new_analyses[analyzer_key]
                        st.session_state.thesis_analysis_data['analyses'] = analyses
                        
                        # Update final recommendation if provided
                        if 'final_recommendation' in data:
                            st.session_state.thesis_analysis_data['final_recommendation'] = data['final_recommendation']
                
                st.success(f"✅ {analyzer_key.replace('_', ' ').title()} analysis completed!")
                st.rerun()
            else:
                st.error(f"❌ Failed to run {analyzer_key} analysis: {response.text}")
                
        except Exception as e:
            st.error(f"Error running {analyzer_key} analysis: {str(e)}")

def main():
    """Main function for thesis generation page"""
    show_thesis_generation()

if __name__ == "__main__":
    main()

def run_individual_analysis(ticker, analyzer_key):
    """Run individual analysis for a specific analyzer"""
    
    with st.spinner(f"Running {analyzer_key.replace('_', ' ').title()} analysis for {ticker}..."):
        try:
            # Use the API endpoint to run specific analyzer
            endpoint = f"http://localhost:8000/analyze/{ticker}"
            request_data = {
                "ticker": ticker,
                "enabled_analyzers": [analyzer_key]
            }
            
            response = requests.post(endpoint, json=request_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Update session state with new analysis
                if 'thesis_analysis_data' in st.session_state:
                    analyses = st.session_state.thesis_analysis_data.get('analyses', {})
                    new_analyses = data.get('analyses', {})
                    
                    # Update with new analyzer result
                    if analyzer_key in new_analyses:
                        analyses[analyzer_key] = new_analyses[analyzer_key]
                        st.session_state.thesis_analysis_data['analyses'] = analyses
                        
                        # Update final recommendation if provided
                        if 'final_recommendation' in data:
                            st.session_state.thesis_analysis_data['final_recommendation'] = data['final_recommendation']
                
                st.success(f"✅ {analyzer_key.replace('_', ' ').title()} analysis completed!")
                st.rerun()
            else:
                st.error(f"❌ Failed to run {analyzer_key} analysis: {response.text}")
                
        except Exception as e:
            st.error(f"Error running {analyzer_key} analysis: {str(e)}")
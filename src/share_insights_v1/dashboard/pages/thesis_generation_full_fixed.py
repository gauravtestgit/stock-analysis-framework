import streamlit as st
import pandas as pd
import json
import requests
import time
from datetime import datetime
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path for absolute imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.share_insights_v1.implementations.llm_providers.llm_manager import LLMManager
from src.share_insights_v1.services.database.database_service import DatabaseService

def show_thesis_generation():
    """Show thesis generation page with full detailed analysis functionality"""
    
    st.title("📝 Investment Thesis Generator")
    st.markdown("*Generate comprehensive investment theses with full analysis capabilities*")
    
    # Stock input
    ticker = st.text_input("Enter Stock Ticker:", value="AAPL").upper()
    
    # News sentiment options
    st.subheader("News Sentiment Options")
    col1, col2 = st.columns(2)
    with col1:
        enable_web_scraping = st.checkbox("Enable Web Scraping", value=True, help="Fetch full article content for better accuracy (slower)")
    with col2:
        enable_llm_sentiment = st.checkbox("Enable LLM Sentiment", value=True, help="Use AI for sentiment analysis (slower but more accurate)")
    
    # Analyzer selection
    st.subheader("Select Analyzers")
    available_analyzers = [
        "dcf", "technical", "comparable", "startup", 
        "ai_insights", "news_sentiment", "business_model", 
        "financial_health", "analyst_consensus", "industry_analysis"
    ]
    
    selected_analyzers = st.multiselect(
        "Choose analyzers to run:",
        available_analyzers,
        default=available_analyzers,
        help="Select which analysis methods to include. Startup analyzer runs for loss-making companies."
    )
    
    if st.button("🔍 Analyze Stock") and ticker:
        if selected_analyzers:
            # Store news sentiment options in session state
            st.session_state.news_options = {
                'enable_web_scraping': enable_web_scraping,
                'enable_llm_sentiment': enable_llm_sentiment
            }
            analyze_single_stock(ticker, selected_analyzers)
        else:
            st.error("Please select at least one analyzer")
    
    # Display analysis data if loaded
    if 'thesis_analysis_data' in st.session_state and 'thesis_ticker' in st.session_state:
        display_detailed_results(st.session_state.thesis_ticker, st.session_state.thesis_analysis_data)
        
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
            # Use the latest analysis data from session state
            latest_analysis_data = st.session_state.thesis_analysis_data
            latest_ticker = st.session_state.thesis_ticker
            
            # Debug info to verify we're using latest data
            st.info(f"Generating thesis using analysis from: {latest_analysis_data.get('timestamp', 'Unknown time')}")
            
            generate_investment_thesis(
                latest_ticker, 
                latest_analysis_data, 
                thesis_type
            )

def analyze_single_stock(ticker, selected_analyzers=None):
    """Analyze a single stock with selected analyzers"""
    with st.spinner(f"Analyzing {ticker}..."):
        try:
            # Measure analysis time
            analysis_start = time.time()
            
            endpoint = f"http://localhost:8000/analyze/{ticker}"
            
            # Prepare request data with selected analyzers
            request_data = {"ticker": ticker}
            if selected_analyzers:
                request_data["enabled_analyzers"] = selected_analyzers
            
            response = requests.post(endpoint, json=request_data)
            analysis_end = time.time()
            total_request_time = analysis_end - analysis_start
            
            if response.status_code == 200:
                data = response.json()
                
                # Add timing info to data
                data['dashboard_timing'] = {
                    'total_request_time': round(total_request_time, 2),
                    'orchestrator_time': data.get('execution_time_seconds', 0),
                    'analyses_count': data.get('analyses_count', 0)
                }
                
                # Add timestamp for thesis generation verification
                data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                st.success(f"Analysis completed in {total_request_time:.2f}s!")
                
                # Store analysis data for thesis generation
                st.session_state.thesis_analysis_data = data
                st.session_state.thesis_ticker = ticker
                
            else:
                st.error(f"Failed to analyze {ticker}: {response.text}")
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}")

def get_current_price(ticker):
    """Get current stock price using yfinance with debugging"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Try multiple price sources (including ETF-specific fields)
        current_price = (info.get('currentPrice') or 
                        info.get('regularMarketPrice') or 
                        info.get('navPrice') or  # ETF Net Asset Value
                        info.get('previousClose') or
                        info.get('ask') or
                        info.get('bid') or
                        info.get('open'))
        
        if not current_price:
            # Try getting price from history as fallback
            try:
                hist = stock.history(period='1d')
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
            except:
                pass
        
        return current_price
    except Exception as e:
        return None

def display_detailed_results(ticker, data):
    """Display comprehensive analysis results"""
    # Add CSS for smaller metric font size
    st.markdown("""
    <style>
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 0.8rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get current price from yfinance
    current_price = get_current_price(ticker)
    
    # Header info with current price and timing
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Current Price", f"${current_price:.2f}" if current_price else "N/A")
    with col2:
        st.metric("Company Type", data.get('company_type', 'N/A'))
    with col3:
        final_rec = data.get('final_recommendation', {})
        st.metric("Recommendation", final_rec.get('recommendation', 'N/A'))
    with col4:
        target_price = final_rec.get('target_price', 0) or 0
        st.metric("Target Price", f"${target_price:.2f}" if target_price else "N/A")
        
        # Show upside/downside if we have both prices
        if current_price and target_price:
            upside = ((target_price - current_price) / current_price) * 100
            st.caption(f"Upside: {upside:+.1f}%")
    with col5:
        # Display timing information
        timing = data.get('dashboard_timing', {})
        orchestrator_time = timing.get('orchestrator_time', data.get('execution_time_seconds', 0))
        analyses_count = timing.get('analyses_count', data.get('analyses_count', 0))
        
        st.metric("Analysis Time", f"{orchestrator_time}s")
        if analyses_count > 0:
            avg_time = orchestrator_time / analyses_count
            st.caption(f"{analyses_count} analyses, {avg_time:.2f}s avg")
    
    analyses = data.get('analyses', {})
    
    # Display analysis cards in horizontal scrollable format
    if analyses:
        st.subheader("📊 Analysis Results")
        display_horizontal_analysis_cards(ticker, data, analyses)

def display_horizontal_analysis_cards(ticker, data, analyses):
    """Display analysis cards in grid format with modals"""
    
    # Create sanitized ticker for JavaScript usage
    sanitized_ticker = ticker.replace('.', '_')
    
    # Get data for the cards
    financial_metrics = data.get('financial_metrics') or {}
    current_price = financial_metrics.get('current_price') or data.get('current_price')
    final_rec = data.get('final_recommendation', {})
    
    # Create all cards
    all_cards = []
    
    # Stock Symbol and Basic Info Card (first card)
    company_type = data.get('company_type', 'N/A')
    target_price = final_rec.get('target_price', 0) or 0
    upside_pct = None
    if current_price and target_price and current_price > 0 and target_price > 0:
        upside_pct = ((target_price - current_price) / current_price) * 100
    
    market_cap = financial_metrics.get('market_cap', 0) or 0
    stock_card = f"""
    <div style="min-width: 220px; max-height: 300px; overflow-y: auto; padding: 15px; border: 2px solid #007acc; border-radius: 8px; margin-right: 10px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
        <h4 style="margin: 0 0 10px 0; color: #007acc; font-weight: bold;">{ticker}</h4>
        <p style="color: #28a745; font-weight: bold;"><strong>Overall:</strong> {final_rec.get('recommendation', 'N/A')}</p>
        <p><strong>Price:</strong> {f'${current_price:.2f}' if current_price else 'N/A'}</p>
        <p><strong>Target:</strong> {f'${target_price:.2f}' if target_price else 'N/A'}</p>
        <p><strong>Upside:</strong> {f'{upside_pct:.1f}%' if upside_pct is not None else 'N/A'}</p>
        <p><strong>Industry:</strong> {financial_metrics.get('industry', 'N/A')}</p>
        <p><strong>Type:</strong> {company_type}</p>
        <p><strong>Market Cap:</strong> ${market_cap:,.0f}</p>
    </div>
    """
    all_cards.append(stock_card)
    
    # Add analysis-specific cards
    for analysis_type, analysis_data in analyses.items():
        if analysis_type == 'dcf':
            dcf_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">
                <h5>💰 DCF</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Upside:</strong> {(analysis_data.get('upside_downside_pct', 0) or 0):.1f}%</p>
                <p><strong>Confidence:</strong> {analysis_data.get('confidence', 'N/A')}</p>
            </div>
            """
            all_cards.append(dcf_card)
        
        elif analysis_type == 'technical':
            tech_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">
                <h5>📈 Technical</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Trend:</strong> {analysis_data.get('trend', 'N/A')}</p>
                <p><strong>RSI:</strong> {analysis_data.get('rsi_14', 'N/A')}</p>
            </div>
            """
            all_cards.append(tech_card)
        
        elif analysis_type == 'ai_insights':
            ai_insights = analysis_data.get('ai_insights', {})
            ai_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">
                <h5>🤖 AI Insights</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Position:</strong> {ai_insights.get('market_position', 'N/A')}</p>
                <p><strong>Growth:</strong> {ai_insights.get('growth_prospects', 'N/A')}</p>
            </div>
            """
            all_cards.append(ai_card)
        
        elif analysis_type == 'news_sentiment':
            news_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">
                <h5>📰 News</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Score:</strong> {analysis_data.get('overall_sentiment_score', 0) or 0:.2f}</p>
                <p><strong>Count:</strong> {analysis_data.get('news_count', 0)}</p>
                <p><strong>Rating:</strong> {analysis_data.get('sentiment_rating', 'N/A')}</p>
            </div>
            """
            all_cards.append(news_card)
        
        elif analysis_type == 'comparable':
            multiples = analysis_data.get('target_multiples', {})
            comp_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">
                <h5>📊 Comparable</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>P/E:</strong> {multiples.get('pe', 'N/A')}x</p>
            </div>
            """
            all_cards.append(comp_card)
        
        elif analysis_type == 'analyst_consensus':
            analyst_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">
                <h5>👥 Analyst</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Count:</strong> {analysis_data.get('num_analysts', 0)}</p>
            </div>
            """
            all_cards.append(analyst_card)
    
    # Arrange cards in grid with 3 cards per row
    cards_html = ''.join(all_cards)
    grid_layout = f"""
    <div id="analysis-cards-container" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; padding: 15px;">
        {cards_html}
    </div>
    """
    
    # Calculate height based on number of rows (each row ~300px)
    num_cards = len(all_cards)
    num_rows = (num_cards + 2) // 3  # Round up to nearest row
    grid_height = max(320, num_rows * 320)
    
    st.components.v1.html(grid_layout, height=grid_height)

def generate_investment_thesis(ticker, analysis_data, thesis_type):
    """Generate investment thesis based on analysis data"""
    
    with st.spinner(f"Generating {thesis_type.lower()} thesis for {ticker}..."):
        try:
            # Extract key data points
            final_rec = analysis_data.get('final_recommendation', {})
            analyses = analysis_data.get('analyses', {})
            
            # Build enhanced thesis components
            thesis_components = extract_enhanced_thesis_components(ticker, analysis_data, analyses)
            
            # Generate thesis with LLM enhancement
            if thesis_type == "Bull Case":
                thesis = generate_enhanced_bull_case(ticker, thesis_components)
            elif thesis_type == "Bear Case":
                thesis = generate_enhanced_bear_case(ticker, thesis_components)
            else:  # Balanced
                thesis = generate_enhanced_balanced_thesis(ticker, thesis_components)
            
            # Display generated thesis
            display_generated_thesis(ticker, thesis, thesis_type)
            
        except Exception as e:
            st.error(f"Error generating thesis: {str(e)}")

def extract_enhanced_thesis_components(ticker, analysis_data, analyses):
    """Extract enhanced thesis components with cross-method analysis"""
    
    # Get base components
    components = extract_thesis_components(ticker, analysis_data, analyses)
    
    # Add cross-method valuation analysis
    components['cross_method_analysis'] = reconcile_valuation_methods(components['valuation_methods'])
    
    # Extract catalysts with timeframes
    components['key_catalysts'] = extract_catalysts_with_timeframes(analyses)
    
    # Generate investment narrative
    components['investment_narrative'] = generate_investment_narrative(analyses, components)
    
    return components

def reconcile_valuation_methods(valuation_methods):
    """Analyze discrepancies between valuation methods"""
    
    targets = [v.get('target_price', 0) for v in valuation_methods.values() if v.get('target_price', 0) > 0]
    if not targets:
        return {'consensus_strength': 'No Data', 'valuation_spread': 0, 'average_target': 0}
    
    avg_target = sum(targets) / len(targets)
    max_target = max(targets)
    min_target = min(targets)
    spread = ((max_target - min_target) / avg_target) * 100 if avg_target > 0 else 0
    
    # Analyze recommendation consensus
    recommendations = [v.get('recommendation', '') for v in valuation_methods.values()]
    buy_signals = sum(1 for r in recommendations if r in ['Buy', 'Strong Buy'])
    total_methods = len([r for r in recommendations if r != 'N/A'])
    
    return {
        'average_target': avg_target,
        'valuation_spread': spread,
        'consensus_strength': 'High' if spread < 20 else 'Medium' if spread < 40 else 'Low',
        'buy_consensus': buy_signals / total_methods if total_methods > 0 else 0,
        'method_agreement': f"{buy_signals}/{total_methods} methods bullish"
    }

def extract_catalysts_with_timeframes(analyses):
    """Extract growth catalysts with time horizons"""
    
    catalysts = {'short_term': [], 'medium_term': [], 'long_term': []}
    
    # Extract from AI insights
    if 'ai_insights' in analyses:
        ai_data = analyses['ai_insights'].get('ai_insights', {})
        catalysts['medium_term'].extend(ai_data.get('growth_drivers', []))
        catalysts['long_term'].append(ai_data.get('competitive_advantage', 'N/A'))
    
    # Extract from news sentiment
    if 'news_sentiment' in analyses:
        news_data = analyses['news_sentiment']
        catalysts['short_term'].extend(news_data.get('key_developments', [])[:3])
    
    return catalysts

def generate_investment_narrative(analyses, components):
    """Generate investment narrative from analysis data"""
    
    cross_analysis = components.get('cross_method_analysis', {})
    consensus_strength = cross_analysis.get('consensus_strength', 'Medium')
    
    if consensus_strength == 'High':
        narrative = f"Strong valuation consensus across methods supports investment thesis."
    elif consensus_strength == 'Medium':
        narrative = f"Moderate valuation agreement suggests balanced risk-reward profile."
    else:
        narrative = f"Valuation methods show divergence, requiring careful risk assessment."
    
    # Add sentiment context
    sentiment = components.get('market_sentiment', {}).get('sentiment_rating', 'Neutral')
    narrative += f" Market sentiment is {sentiment.lower()}, providing additional context for timing."
    
    return narrative

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

def generate_enhanced_bull_case(ticker, components):
    """Generate enhanced bullish investment thesis with LLM synthesis"""
    
    try:
        llm_manager = LLMManager()
        
        # Prepare data for LLM synthesis
        cross_analysis = components['cross_method_analysis']
        catalysts = components['key_catalysts']
        
        prompt = f"""
        Generate a professional bull case investment thesis for {ticker} using this data:
        
        VALUATION ANALYSIS:
        - Average target price: ${cross_analysis.get('average_target', 0):.2f}
        - Method consensus: {cross_analysis.get('method_agreement', 'N/A')}
        - Valuation spread: {cross_analysis.get('valuation_spread', 0):.1f}%
        
        KEY STRENGTHS: {', '.join(components['strengths'][:5])}
        
        CATALYSTS:
        - Short-term: {', '.join(catalysts['short_term'][:3])}
        - Medium-term: {', '.join(catalysts['medium_term'][:3])}
        
        COMPETITIVE POSITION: {components['competitive_position']}
        
        Provide a structured thesis with:
        1. Executive summary with target price rationale
        2. Key investment strengths (3-5 points)
        3. Growth catalysts by timeframe
        4. Valuation rationale reconciling different methods
        5. Investment recommendation
        
        Keep it professional, concise, and data-driven.
        """
        
        llm_response = llm_manager.generate_response(prompt)
        
        # Fallback to template if LLM fails
        if not llm_response or len(llm_response.strip()) < 100:
            return generate_bull_case(ticker, components)
        
        return llm_response
        
    except Exception as e:
        st.warning(f"LLM enhancement failed, using template: {str(e)}")
        return generate_bull_case(ticker, components)

def generate_enhanced_bear_case(ticker, components):
    """Generate enhanced bearish investment thesis with LLM synthesis"""
    
    try:
        llm_manager = LLMManager()
        
        cross_analysis = components['cross_method_analysis']
        
        prompt = f"""
        Generate a professional bear case investment thesis for {ticker} using this data:
        
        VALUATION CONCERNS:
        - Valuation spread: {cross_analysis.get('valuation_spread', 0):.1f}%
        - Method disagreement suggests uncertainty
        
        KEY RISKS: {', '.join(components['risks'][:5])}
        
        MARKET SENTIMENT: {components['market_sentiment'].get('sentiment_rating', 'Neutral')}
        
        Provide a structured bear case with:
        1. Executive summary highlighting key concerns
        2. Primary risk factors
        3. Valuation concerns and method discrepancies
        4. Market headwinds
        5. Investment recommendation
        
        Focus on downside risks and valuation concerns.
        """
        
        llm_response = llm_manager.generate_response(prompt)
        
        if not llm_response or len(llm_response.strip()) < 100:
            return generate_bear_case(ticker, components)
        
        return llm_response
        
    except Exception as e:
        st.warning(f"LLM enhancement failed, using template: {str(e)}")
        return generate_bear_case(ticker, components)

def generate_enhanced_balanced_thesis(ticker, components):
    """Generate enhanced balanced investment thesis with LLM synthesis"""
    
    try:
        llm_manager = LLMManager()
        
        final_rec = components['final_recommendation']
        cross_analysis = components['cross_method_analysis']
        
        prompt = f"""
        Generate a balanced investment thesis for {ticker} using this comprehensive analysis:
        
        OVERALL RECOMMENDATION: {final_rec.get('recommendation', 'Hold')}
        TARGET PRICE: ${final_rec.get('target_price', 0):.2f}
        
        VALUATION CONSENSUS:
        - Average target: ${cross_analysis.get('average_target', 0):.2f}
        - Consensus strength: {cross_analysis.get('consensus_strength', 'Medium')}
        - Method agreement: {cross_analysis.get('method_agreement', 'Mixed')}
        
        INVESTMENT NARRATIVE: {components.get('investment_narrative', 'Balanced outlook')}
        
        STRENGTHS: {', '.join(components['strengths'][:3])}
        RISKS: {', '.join(components['risks'][:3])}
        
        Provide a balanced analysis with:
        1. Executive summary with recommendation rationale
        2. Key investment strengths (top 3)
        3. Primary risk factors (top 3)
        4. Cross-method valuation analysis
        5. Investment recommendation with risk-reward assessment
        
        Present both sides objectively with data-driven conclusions.
        """
        
        llm_response = llm_manager.generate_response(prompt)
        
        if not llm_response or len(llm_response.strip()) < 100:
            return generate_balanced_thesis(ticker, components)
        
        return llm_response
        
    except Exception as e:
        st.warning(f"LLM enhancement failed, using template: {str(e)}")
        return generate_balanced_thesis(ticker, components)

def generate_bull_case(ticker, components):
    """Generate bullish investment thesis (template fallback)"""
    
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

## Investment Recommendation
**BUY** - {ticker} offers strong upside potential with manageable risks.
"""
    
    return thesis

def generate_bear_case(ticker, components):
    """Generate bearish investment thesis (template fallback)"""
    
    thesis = f"""
# 🐻 Bear Case Investment Thesis: {ticker}

## Executive Summary
{ticker} faces significant headwinds and risks that could impact future performance.

## Key Risk Factors
"""
    
    # Add risks
    if components['risks']:
        for risk in components['risks'][:5]:  # Top 5 risks
            thesis += f"• {risk}\n"
    else:
        thesis += "• Market volatility and competitive pressures\n"
    
    thesis += f"""
## Investment Recommendation
**HOLD/AVOID** - Given the risk factors, investors should exercise caution.
"""
    
    return thesis

def generate_balanced_thesis(ticker, components):
    """Generate balanced investment thesis (template fallback)"""
    
    final_rec = components['final_recommendation']
    recommendation = final_rec.get('recommendation', 'Hold')
    target_price = final_rec.get('target_price', 0)
    
    thesis = f"""
# ⚖️ Balanced Investment Thesis: {ticker}

## Executive Summary
{ticker} presents a mixed investment profile. Our analysis suggests a **{recommendation}** recommendation with a target price of ${target_price:.2f}.

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
    
    # Summarize all valuation methods with proper formatting
    for method, data in components['valuation_methods'].items():
        method_name = method.replace('_', ' ').title()
        target_price = data.get('target_price', 0)
        recommendation = data.get('recommendation', 'N/A')
        confidence = data.get('confidence', 'N/A')
        thesis += f"• **{method_name}**: {recommendation} - ${target_price:.2f} ({confidence} confidence)\n"
    
    thesis += f"""
## Investment Recommendation
**{recommendation}** - {ticker} offers a balanced risk-reward profile.
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

def main():
    """Main function for thesis generation page"""
    show_thesis_generation()

if __name__ == "__main__":
    main()
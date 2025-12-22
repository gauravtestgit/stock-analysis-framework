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

def show_detailed_analysis():
    """Show detailed analysis page with AI insights and news sentiment"""
    
    st.title("🔍 Detailed Stock Analysis")
    
    # Chat interface at the top
    show_chat_interface()
    
    # Display persisted analysis results if available
    if 'analysis_data' in st.session_state and 'analysis_ticker' in st.session_state:
        st.markdown("---")
        st.subheader(f"📊 Previous Analysis Results for {st.session_state.analysis_ticker}")
        display_detailed_results(st.session_state.analysis_ticker, st.session_state.analysis_data)
    
    # Display persisted batch results if available
    if 'batch_results' in st.session_state and 'batch_timing' in st.session_state:
        st.markdown("---")
        st.subheader(f"📊 Previous Batch Analysis Results ({len(st.session_state.batch_watchlist)} stocks)")
        display_batch_results(st.session_state.batch_results, st.session_state.batch_timing)
    
    st.markdown("---")
    
    from watchlist_component import get_watchlist
    
    # Analysis mode selection
    analysis_mode = st.radio("Analysis Mode:", ["Single Stock", "Watchlist Batch"])
    
    if analysis_mode == "Single Stock":
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
        
        if st.button("Analyze Stock") and ticker:
            if selected_analyzers:
                # Store news sentiment options in session state
                st.session_state.news_options = {
                    'enable_web_scraping': enable_web_scraping,
                    'enable_llm_sentiment': enable_llm_sentiment
                }
                analyze_single_stock(ticker, selected_analyzers)
            else:
                st.error("Please select at least one analyzer")
    
    else:  # Watchlist Batch
        watchlist = get_watchlist()
        
        if not watchlist:
            st.info("No stocks in watchlist. Add stocks using the sidebar.")
            return
        
        st.write(f"**Watchlist ({len(watchlist)} stocks):** {', '.join(watchlist)}")
        
        # News sentiment options for batch
        st.subheader("News Sentiment Options")
        col1, col2 = st.columns(2)
        with col1:
            batch_web_scraping = st.checkbox("Enable Web Scraping (Batch)", value=False, help="Fetch full article content (much slower for batch)")
        with col2:
            batch_llm_sentiment = st.checkbox("Enable LLM Sentiment (Batch)", value=False, help="Use AI for sentiment analysis (slower for batch)")
        
        # Analyzer selection for batch
        st.subheader("Select Analyzers for Batch")
        available_analyzers = [
            "dcf", "technical", "comparable", "startup", 
            "ai_insights", "news_sentiment", "business_model", 
            "financial_health", "analyst_consensus", "industry_analysis"
        ]
        
        batch_analyzers = st.multiselect(
            "Choose analyzers for batch analysis:",
            available_analyzers,
            default=available_analyzers,
            help="Select which analysis methods to run for all stocks"
        )
        
        if st.button("Analyze All Watchlist Stocks"):
            if batch_analyzers:
                # Store batch news sentiment options
                st.session_state.batch_news_options = {
                    'enable_web_scraping': batch_web_scraping,
                    'enable_llm_sentiment': batch_llm_sentiment
                }
                analyze_watchlist_batch(watchlist, batch_analyzers)
            else:
                st.error("Please select at least one analyzer")

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
                print(request_data)
            
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
                
                st.success(f"Analysis completed in {total_request_time:.2f}s!")
                
                # Store analysis data for chat context and persistence
                st.session_state.current_analysis = {
                    'ticker': ticker,
                    'company_type': data.get('company_type', 'Unknown'),
                    'final_recommendation': data.get('final_recommendation', {}),
                    'analyses': data.get('analyses', {})
                }
                st.session_state.analysis_data = data
                st.session_state.analysis_ticker = ticker
                
                display_detailed_results(ticker, data)
            else:
                st.error(f"Failed to analyze {ticker}: {response.text}")
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}")

def analyze_single_stock_api(ticker, selected_analyzers=None):
    """Analyze a single stock via API - helper function for parallel execution"""
    try:
        stock_start = time.time()
        
        endpoint = f"http://localhost:8000/analyze/{ticker}"
        request_data = {"ticker": ticker}
        if selected_analyzers:
            request_data["enabled_analyzers"] = selected_analyzers
        
        response = requests.post(endpoint, json=request_data)
        stock_end = time.time()
        
        if response.status_code == 200:
            data = response.json()
            data['dashboard_timing'] = {
                'total_request_time': round(stock_end - stock_start, 2),
                'orchestrator_time': data.get('execution_time_seconds', 0),
                'analyses_count': data.get('analyses_count', 0)
            }
            return ticker, data
        else:
            return ticker, {"error": response.text}
    except Exception as e:
        return ticker, {"error": str(e)}

def analyze_watchlist_batch(watchlist, selected_analyzers=None):
    """Analyze all stocks in watchlist with selected analyzers in parallel"""
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Track batch timing
    batch_start = time.time()
    
    # Parallel execution with balanced workers for performance and cost
    max_workers = min(len(watchlist), 4)  # Balanced for performance and cost
    status_text.text(f"Starting parallel analysis of {len(watchlist)} stocks with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all analysis tasks
        future_to_ticker = {
            executor.submit(analyze_single_stock_api, ticker, selected_analyzers): ticker
            for ticker in watchlist
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_ticker):
            ticker, result = future.result()
            results[ticker] = result
            completed += 1
            
            # Update progress
            progress_bar.progress(completed / len(watchlist))
            status_text.text(f"Completed {completed}/{len(watchlist)} stocks ({ticker})")
            

    
    batch_end = time.time()
    total_batch_time = batch_end - batch_start
    
    status_text.text(f"Parallel batch analysis complete! Total time: {total_batch_time:.2f}s")
    
    # Add batch timing to results
    batch_timing = {
        'total_batch_time': round(total_batch_time, 2),
        'stocks_analyzed': len(watchlist),
        'avg_time_per_stock': round(total_batch_time / len(watchlist), 2) if watchlist else 0,
        'parallel_workers': max_workers
    }
    
    # Store batch results in session state
    st.session_state.batch_results = results
    st.session_state.batch_timing = batch_timing
    st.session_state.batch_watchlist = watchlist
    
    display_batch_results(results, batch_timing)

def get_current_price(ticker):
    """Get current stock price using yfinance with debugging"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Debug: Check what's in info for ETFs
        price_fields = ['currentPrice', 'regularMarketPrice', 'previousClose', 'ask', 'bid', 'navPrice', 'open']
        available_prices = {field: info.get(field) for field in price_fields if info.get(field)}
        print(f"Available price fields for {ticker}: {available_prices}")
        
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
                    print(f"Using historical price for {ticker}: {current_price}")
            except:
                pass
        
        print(f"Final price for {ticker}: {current_price}")
        return current_price
    except Exception as e:
        # Debug: Print the actual error
        print(f"Error getting price for {ticker}: {e}")
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
    


    
    # AI Insights Section
    if 'ai_insights' in analyses:
        st.subheader("🤖 AI Insights Analysis")
        ai_data = analyses['ai_insights']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Recommendation:**", ai_data.get('recommendation', 'N/A'))
            predicted_price = ai_data.get('predicted_price', 0) or 0
            st.write("**Target Price:**", f"${predicted_price:.2f}" if predicted_price else "N/A")
            st.write("**Confidence:**", ai_data.get('confidence', 'N/A'))
        
        with col2:
            ai_insights = ai_data.get('ai_insights', {})
            st.write("**Market Position:**", ai_insights.get('market_position', 'N/A'))
            st.write("**Growth Prospects:**", ai_insights.get('growth_prospects', 'N/A'))
            st.write("**Competitive Advantage:**", ai_insights.get('competitive_advantage', 'N/A'))
        
        # Key strengths and risks
        ai_insights = ai_data.get('ai_insights', {})
        strengths = ai_insights.get('key_strengths', [])
        risks = ai_insights.get('key_risks', [])
        
        if strengths:
            st.write("**Key Strengths:**")
            for strength in strengths:
                st.write(f"• {strength}")
        
        if risks:
            st.write("**Key Risks:**")
            for risk in risks:
                st.write(f"• {risk}")
    
    # News Sentiment Section
    if 'news_sentiment' in analyses:
        st.subheader("📰 News Sentiment Analysis")
        news_data = analyses['news_sentiment']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            sentiment_score = news_data.get('overall_sentiment_score', 0)
            st.metric("Sentiment Score", f"{sentiment_score:.2f}")
        with col2:
            st.metric("News Count", news_data.get('news_count', 0))
        with col3:
            st.metric("Sentiment Rating", news_data.get('sentiment_rating', 'N/A'))
        
        # Overall Summary
        overall_summary = news_data.get('overall_summary', [])
        if overall_summary:
            st.write("**Overall Summary:**")
            for summary_point in overall_summary:
                st.write(f"• {summary_point}")
        
        # Key developments
        key_developments = news_data.get('key_developments', [])
        if key_developments:
            st.write("**Key Developments:**")
            for dev in key_developments:
                st.write(f"• {dev}")
        
        # Sentiment drivers and risks
        drivers = news_data.get('sentiment_drivers', [])
        risks = news_data.get('risk_factors', [])
        
        if drivers or risks:
            col1, col2 = st.columns(2)
            with col1:
                if drivers:
                    st.write("**Sentiment Drivers:**")
                    for driver in drivers:
                        st.write(f"• {driver}")
            
            with col2:
                if risks:
                    st.write("**Risk Factors:**")
                    for risk in risks:
                        st.write(f"• {risk}")
        
        # Recent news with links
        recent_news = news_data.get('recent_news', [])
        if recent_news:
            st.write("**Recent News:**")
            for i, news in enumerate(recent_news[:5], 1):  # Show top 5
                with st.expander(f"{i}. {news.get('title', 'No title')[:80]}..."):
                    st.write(f"**Source:** {news.get('source', 'Unknown')}")
                    st.write(f"**Date:** {news.get('date', 'N/A')}")
                    st.write(f"**Summary:** {news.get('summary', 'No summary')}")
                    st.write(f"**Sentiment Score:** {news.get('sentiment_score', 0):.2f}")
                    if news.get('url'):
                        st.markdown(f"**[Read Full Article]({news['url']})**")
    
    # DCF Analysis
    if 'dcf' in analyses:
        st.subheader("💰 DCF Valuation")
        dcf_data = analyses['dcf']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            dcf_price = dcf_data.get('predicted_price', 0) or 0
            st.metric("Fair Value", f"${dcf_price:.2f}" if dcf_price else "N/A")
        with col2:
            upside_pct = dcf_data.get('upside_downside_pct', 0) or 0
            st.metric("Upside/Downside", f"{upside_pct:.1f}%" if upside_pct else "N/A")
        with col3:
            st.metric("Recommendation", dcf_data.get('recommendation', 'N/A'))
        
        # DCF parameters
        params = dcf_data.get('dcf_calculations', {})
        if params:
            st.write("**Key Parameters:**")
            for key, value in params.items():
                st.write(f"• {key}: {value}")
    
    # Technical Analysis
    if 'technical' in analyses:
        st.subheader("📈 Technical Analysis")
        tech_data = analyses['technical']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            tech_price = tech_data.get('predicted_price', 0) or 0
            st.metric("Target Price", f"${tech_price:.2f}" if tech_price else "N/A")
        with col2:
            st.metric("Trend", tech_data.get('trend', 'N/A'))
        with col3:
            st.metric("Recommendation", tech_data.get('recommendation', 'N/A'))
        
        # Signal scoring system
        signals = tech_data.get('technical_signals', {})
        if signals:
            st.write("**Signal Analysis:**")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Net Signal:** {signals.get('net_signal', 0)}")
                st.write(f"**Recommendation:** {signals.get('recommendation', 'N/A')}")
            with col2:
                st.write(f"**Bullish Signals:** {signals.get('bullish_signals', 0)}")
                st.write(f"**Bearish Signals:** {signals.get('bearish_signals', 0)}")
        
        # Enhanced indicators
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("**Moving Averages:**")
            ma_20 = tech_data.get('ma_20') or 0
            ma_50 = tech_data.get('ma_50') or 0
            ma_200 = tech_data.get('ma_200') or 0
            st.write(f"• MA 20: ${ma_20:.2f}" if ma_20 else "• MA 20: N/A")
            st.write(f"• MA 50: ${ma_50:.2f}" if ma_50 else "• MA 50: N/A")
            st.write(f"• MA 200: ${ma_200:.2f}" if ma_200 else "• MA 200: N/A")
            
        with col2:
            st.write("**Momentum Indicators:**")
            st.write(f"• RSI (14): {tech_data.get('rsi_14', 'N/A')}")
            macd_line = tech_data.get('macd_line')
            macd_signal = tech_data.get('macd_signal')
            if macd_line is not None and macd_signal is not None:
                st.write(f"• MACD: {macd_line:.3f}")
                st.write(f"• MACD Signal: {macd_signal:.3f}")
            stoch_k = tech_data.get('stoch_k')
            if stoch_k is not None:
                st.write(f"• Stochastic %K: {stoch_k:.1f}")
                
        with col3:
            st.write("**Volatility & Range:**")
            bb_upper = tech_data.get('bb_upper')
            bb_lower = tech_data.get('bb_lower')
            if bb_upper is not None and bb_lower is not None:
                st.write(f"• BB Upper: ${bb_upper:.2f}")
                st.write(f"• BB Lower: ${bb_lower:.2f}")
            st.write(f"• 52W High: ${tech_data.get('high_52w', 0):.2f}")
            st.write(f"• 52W Low: ${tech_data.get('low_52w', 0):.2f}")
        
        # Signal details
        signal_details = signals.get('signal_details', []) if signals else []
        if signal_details:
            st.write("**Signal Details:**")
            for detail in signal_details:
                st.write(f"• {detail}")
    
    # Business Model Analysis
    if 'business_model' in analyses:
        st.subheader("🏢 Business Model Analysis")
        bm_data = analyses['business_model']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Business Model Type:**", bm_data.get('business_model_type', 'N/A'))
            st.write("**Primary Revenue Stream:**", bm_data.get('primary_revenue_stream', 'N/A'))
            st.write("**Revenue Quality:**", bm_data.get('revenue_quality', 'N/A'))
        
        with col2:
            st.write("**Competitive Moat:**", bm_data.get('competitive_moat', 'N/A'))
            st.write("**Scalability Score:**", bm_data.get('scalability_score', 'N/A'))
            st.write("**Recurring %:**", f"{bm_data.get('recurring_percentage', 0)*100:.1f}%")
        
        # Strengths and risks
        strengths = bm_data.get('strengths', [])
        risks = bm_data.get('risks', [])
        
        if strengths:
            st.write("**Strengths:**")
            for strength in strengths:
                st.write(f"• {strength}")
        
        if risks:
            st.write("**Risks:**")
            for risk in risks:
                st.write(f"• {risk}")
    
    # Financial Health
    if 'financial_health' in analyses:
        st.subheader("💊 Financial Health")
        fh_data = analyses['financial_health']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overall Grade", fh_data.get('overall_grade', 'N/A'))
        with col2:
            st.metric("Cash Flow Score", fh_data.get('cash_flow_score', 'N/A'))
        with col3:
            st.metric("Debt Score", fh_data.get('debt_score', 'N/A'))
        
        # Strengths and risks
        strengths = fh_data.get('strengths', [])
        risks = fh_data.get('key_risks', [])
        
        col1, col2 = st.columns(2)
        with col1:
            if strengths:
                st.write("**Strengths:**")
                for strength in strengths:
                    st.write(f"• {strength}")
        
        with col2:
            if risks:
                st.write("**Key Risks:**")
                for risk in risks:
                    st.write(f"• {risk}")
    
    # Startup Analysis
    if 'startup' in analyses:
        st.subheader("🚀 Startup Valuation")
        startup_data = analyses['startup']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            startup_price = startup_data.get('predicted_price', 0) or 0
            st.metric("Fair Value", f"${startup_price:.2f}" if startup_price else "N/A")
        with col2:
            st.metric("Stage", startup_data.get('stage', 'N/A'))
        with col3:
            st.metric("Recommendation", startup_data.get('recommendation', 'N/A'))
        
        # Financial metrics
        col1, col2 = st.columns(2)
        with col1:
            runway = startup_data.get('cash_runway_years', 0)
            st.write(f"**Cash Runway:** {runway:.1f} years" if runway else "N/A")
            burn_rate = startup_data.get('quarterly_burn_rate', 0)
            st.write(f"**Quarterly Burn:** ${burn_rate:,.0f}" if burn_rate else "N/A")
            st.write(f"**Growth Quality:** {startup_data.get('growth_quality', 'N/A')}")
        with col2:
            median_growth = startup_data.get('median_growth', 'N/A')
            st.write(f"**Median Growth:** {median_growth}")
            volatility = startup_data.get('revenue_volatility', 'N/A')
            st.write(f"**Revenue Volatility:** {volatility}")
            risk_score = startup_data.get('risk_score', 0)
            st.write(f"**Risk Score:** {risk_score}/100" if risk_score else "N/A")
        
        # Revenue projections
        current_rev = startup_data.get('current_revenue', 0)
        proj_1y = startup_data.get('projected_revenue_1yr', 0)
        proj_2y = startup_data.get('projected_revenue_2yr', 0)
        if current_rev or proj_1y or proj_2y:
            st.write("**Revenue Projections:**")
            st.write(f"• Current: ${current_rev:,.0f}" if current_rev else "• Current: N/A")
            st.write(f"• 1 Year: ${proj_1y:,.0f}" if proj_1y else "• 1 Year: N/A")
            st.write(f"• 2 Year: ${proj_2y:,.0f}" if proj_2y else "• 2 Year: N/A")
        
        # Risk factors
        risk_factors = startup_data.get('risk_factors', [])
        if risk_factors:
            st.write("**Risk Factors:**")
            for risk in risk_factors:
                st.write(f"• {risk}")
        
        # Investment details
        confidence = startup_data.get('confidence_level', 'N/A')
        investment_type = startup_data.get('investment_type', 'N/A')
        st.write(f"**Confidence Level:** {confidence}")
        st.write(f"**Investment Type:** {investment_type}")
    
    # Comparable Analysis
    if 'comparable' in analyses:
        st.subheader("📊 Comparable Company Analysis")
        comp_data = analyses['comparable']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            comp_price = comp_data.get('predicted_price', 0) or 0
            st.metric("Fair Value", f"${comp_price:.2f}" if comp_price else "N/A")
        with col2:
            pe_multiple = comp_data.get('target_multiples', 0).get('pe',0) or 0
            st.metric("P/E Multiple", f"{pe_multiple:.1f}x" if pe_multiple else "N/A")
        with col3:
            st.metric("Recommendation", comp_data.get('recommendation', 'N/A'))
        
        # Valuation multiples
        multiples = comp_data.get('valuation_multiples', {})
        if multiples:
            st.write("**Valuation Multiples:**")
            for multiple, value in multiples.items():
                st.write(f"• {multiple}: {value}")
        
        # Peer comparison
        peers = comp_data.get('peer_companies', [])
        if peers:
            st.write("**Peer Companies:**")
            for peer in peers[:5]:  # Show top 5
                st.write(f"• {peer}")
    
    # Analyst Consensus
    if 'analyst_consensus' in analyses:
        st.subheader("👥 Analyst Consensus")
        analyst_data = analyses['analyst_consensus']
        
        # Debug info
        with st.expander("🔍 Analyst Consensus Debug Data"):
            st.write("**Analyst Analysis Keys:**", list(analyst_data.keys()) if analyst_data else "None")
            st.json(analyst_data)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            predicted_price = analyst_data.get('predicted_price', 0) or 0
            st.metric("Consensus Target", f"${predicted_price:.2f}" if predicted_price else "N/A")
        with col2:
            st.metric("Analyst Count", analyst_data.get('num_analysts', 0) or 0)
        with col3:
            st.metric("Consensus Rating", analyst_data.get('recommendation', 'N/A'))
        with col4:
            upside_pct = analyst_data.get('upside_downside_pct', 0) or 0
            st.metric("Upside to Target", f"{upside_pct:.1f}%" if upside_pct else "N/A")
        
        # Rating information
        recommendation_mean = analyst_data.get('recommendation_mean', 0)
        if recommendation_mean:
            st.write("**Rating Information:**")
            st.write(f"• Recommendation Mean: {recommendation_mean:.1f}")
            st.write(f"• Confidence: {analyst_data.get('confidence', 'N/A')}")
        
        # Price targets
        col1, col2 = st.columns(2)
        with col1:
            high_target = analyst_data.get('target_high', 0) or 0
            low_target = analyst_data.get('target_low', 0) or 0
            st.write(f"**High Target:** ${high_target:.2f}" if high_target else "N/A")
            st.write(f"**Low Target:** ${low_target:.2f}" if low_target else "N/A")
        with col2:
            current_price = analyst_data.get('current_price', 0) or 0
            predicted_price = analyst_data.get('predicted_price', 0) or 0
            st.write(f"**Current Price:** ${current_price:.2f}" if current_price else "N/A")
            st.write(f"**Target Price:** ${predicted_price:.2f}" if predicted_price else "N/A")
    
    # Raw data expander
    with st.expander("🔧 Raw Analysis Data"):
        financial_metrics = data.get('financial_metrics', {})
        st.write("**Available Analyses:**", list(analyses.keys()) if analyses else "None")
        st.write("**Company Type:**", data.get('company_type', 'N/A'))
        st.write("**Financial Metrics Keys:**", list(financial_metrics.keys()) if financial_metrics else "None")
        st.write("**Current Price Sources:**")
        st.write(f"- financial_metrics.current_price: {financial_metrics.get('current_price')}")
        st.write(f"- financial_metrics.currentPrice: {financial_metrics.get('currentPrice')}")
        st.write(f"- financial_metrics.regularMarketPrice: {financial_metrics.get('regularMarketPrice')}")
        st.write(f"- financial_metrics.previousClose: {financial_metrics.get('previousClose')}")
        st.write(f"- data.current_price: {data.get('current_price')}")
        st.json(data)

def display_batch_results(results, batch_timing=None):
    """Display batch analysis results"""
    st.subheader("📈 Batch Analysis Results")
    
    # Display batch timing if available
    if batch_timing:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Batch Time", f"{batch_timing['total_batch_time']}s")
        with col2:
            st.metric("Stocks Analyzed", batch_timing['stocks_analyzed'])
        with col3:
            st.metric("Avg Time/Stock", f"{batch_timing['avg_time_per_stock']}s")
    
    # Summary metrics
    successful = len([r for r in results.values() if 'error' not in r])
    failed = len(results) - successful
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Analyzed", len(results))
    with col2:
        st.metric("Successful", successful)
    with col3:
        st.metric("Failed", failed)
    
    # Quick summary table with current prices from analysis results
    if successful > 0:
        summary_data = []
        for ticker, data in results.items():
            if 'error' not in data:
                current_price = get_current_price(ticker)
                final_rec = data.get('final_recommendation', {})
                target_price = final_rec.get('target_price', 0) or 0
                upside = ((target_price - current_price) / current_price) * 100 if current_price and target_price else None
                
                summary_data.append({
                    'Ticker': ticker,
                    'Current Price': f"${current_price:.2f}" if current_price else "N/A",
                    'Target Price': f"${target_price:.2f}" if target_price else "N/A",
                    'Upside': f"{upside:+.1f}%" if upside is not None else "N/A",
                    'Recommendation': final_rec.get('recommendation', 'N/A')
                })
        
        if summary_data:
            st.subheader("📊 Quick Summary")
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    # Scrollable detailed results
    st.subheader("📋 Detailed Analysis Results")
    
    # Generate text summary for all stocks
    detailed_text = generate_batch_text_summary(results)
    
    # Display in scrollable text area
    st.text_area(
        "Analysis Results (Scrollable)",
        value=detailed_text,
        height=400,
        help="Scroll through detailed analysis results for all stocks"
    )
    
    # Horizontal scrollable stock analysis cards
    with st.expander("🔍 Individual Stock Deep Dive (Horizontal Scroll)"):
        display_horizontal_stock_cards(results)

def show_chat_interface():
    """Show chat interface for LLM queries"""
    st.subheader("🤖 AI Chat Assistant")
    
    # Initialize LLM manager and register additional providers
    if 'llm_manager' not in st.session_state:
        from src.share_insights_v1.implementations.llm_providers.openai_provider import OpenAIProvider
        from src.share_insights_v1.implementations.llm_providers.xai_provider import XAIProvider
        
        st.session_state.llm_manager = LLMManager()
        
        # Register additional providers
        st.session_state.llm_manager.register_provider(OpenAIProvider())
        st.session_state.llm_manager.register_provider(XAIProvider())
    
    llm_manager = st.session_state.llm_manager
    available_providers = llm_manager.get_available_providers()
    
    # Debug: Show provider status
    with st.expander("🔍 Provider Debug Info"):
        st.write(f"Available providers: {available_providers}")
        st.write(f"Total providers initialized: {len(llm_manager.providers)}")
        for provider in llm_manager.providers:
            st.write(f"- {provider.get_provider_name()}: Available = {provider.is_available()}")
    
    if not available_providers:
        st.error("No LLM providers available")
        return
    
    # Provider selection and chat input
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_provider = st.selectbox(
            "Select AI Provider:",
            available_providers,
            key="chat_provider"
        )
    
    with col2:
        user_query = st.text_input(
            "Ask about the stock analysis:",
            placeholder="e.g., What are the key risks for this company?",
            key="chat_input"
        )
    
    # Chat button and response
    if st.button("Ask AI", key="chat_button") and user_query:
        with st.spinner(f"Getting response from {selected_provider}..."):
            try:
                # Get current analysis context if available
                context = ""
                if 'current_analysis' in st.session_state:
                    analysis_data = st.session_state.current_analysis
                    ticker = analysis_data.get('ticker', 'Unknown')
                    company_type = analysis_data.get('company_type', 'Unknown')
                    final_rec = analysis_data.get('final_recommendation', {})
                    
                    context = f"""
                    Context: Stock analysis for {ticker}
                    Company Type: {company_type}
                    Recommendation: {final_rec.get('recommendation', 'N/A')}
                    Target Price: ${final_rec.get('target_price', 0):.2f}
                    
                    User Question: {user_query}
                    
                    Please provide a concise, helpful response based on the analysis context.
                    """
                else:
                    context = f"User Question: {user_query}\n\nPlease provide a helpful response about stock analysis."
                
                # Generate response
                response = llm_manager.generate_response_with_provider(
                    context, selected_provider
                )
                
                # Display response
                st.success(f"**{selected_provider} Response:**")
                st.write(response)
                
            except Exception as e:
                st.error(f"Error getting response from {selected_provider}: {str(e)}")
    
    st.markdown("---")

def display_horizontal_stock_cards(results):
    """Display stock analysis in horizontal scrollable rows"""
    
    for ticker, data in results.items():
        if 'error' in data:
            st.error(f"❌ {ticker}: {data['error']}")
            continue
            
        # Create sanitized ticker for ALL JavaScript usage
        sanitized_ticker = ticker.replace('.', '_')
        print(f"DEBUG: Processing {ticker} -> sanitized to {sanitized_ticker}")
            
        # Get data for the row
        financial_metrics = data.get('financial_metrics') or {}
        print(f"results data in detailed analysis\n ${results}")
        current_price = financial_metrics.get('current_price') or data.get('current_price')
        final_rec = data.get('final_recommendation', {})
        timing = data.get('dashboard_timing', {})
        analysis_time = timing.get('orchestrator_time', data.get('execution_time_seconds', 0))
        analyses = data.get('analyses', {})
        
        # Create horizontal scrollable container for this stock
        st.markdown(f"**📊 {ticker} - {final_rec.get('recommendation', 'N/A')}**")
            # Business Summary Section
        financial_metrics = data.get('financial_metrics', {})
        business_summary = financial_metrics.get('business_summary', '')
        market_cap = financial_metrics.get('market_cap', 0) or 0
        if business_summary:
            st.subheader("📋 Business Summary")
            st.write(business_summary)
            st.markdown("---")
        
        # Create all cards in one row with horizontal scroll
        all_cards = []
        
        # Stock Symbol and Basic Info Card (first card)
        company_type = data.get('company_type', 'N/A')
        target_price = final_rec.get('target_price', 0) or 0
        upside_pct = None
        if current_price and target_price and current_price > 0 and target_price > 0:
            upside_pct = ((target_price - current_price) / current_price) * 100
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
            <p><strong>P/E:</strong> {financial_metrics.get('pe_ratio', 'N/A')}</p>
            <p><strong>P/S:</strong> {financial_metrics.get('ps_ratio', 'N/A')}</p>
            <p><strong>P/B:</strong> {financial_metrics.get('pb_ratio', 'N/A')}</p>
            <p><strong>ROE:</strong> {financial_metrics.get('roe', 'N/A')}%</p>
            <p><strong>Debt Ratio:</strong> {financial_metrics.get('debt_to_equity', 'N/A')}</p>            
            <p><strong>Time:</strong> {analysis_time}s</p>
        </div>
        """
        all_cards.append(stock_card)
        
        # Financial Statements Card (second card)
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            
            # Get financial data
            income_stmt = stock.financials
            cashflow = stock.cashflow
            
            # Extract key metrics for last 4-5 years
            revenue_data = []
            gross_income_data = []
            net_income_data = []
            operating_cf_data = []
            free_cf_data = []
            years = []
            
            if not income_stmt.empty and not cashflow.empty:
                # Get last 4 years of data
                for col in income_stmt.columns[:4]:
                    year = str(col.year)
                    years.append(year)
                    
                    # Revenue (Total Revenue)
                    revenue = income_stmt.loc['Total Revenue', col] if 'Total Revenue' in income_stmt.index else 0
                    revenue_data.append(revenue if revenue else 0)  # Keep raw values
                    
                    # Gross Income (Gross Profit)
                    gross_income = income_stmt.loc['Gross Profit', col] if 'Gross Profit' in income_stmt.index else 0
                    gross_income_data.append(gross_income if gross_income else 0)  # Keep raw values
                    
                    # Net Income
                    net_income = income_stmt.loc['Net Income', col] if 'Net Income' in income_stmt.index else 0
                    net_income_data.append(net_income if net_income else 0)  # Keep raw values
                    
                    # Operating Cash Flow
                    op_cf = cashflow.loc['Operating Cash Flow', col] if 'Operating Cash Flow' in cashflow.index else 0
                    operating_cf_data.append(op_cf if op_cf else 0)  # Keep raw values
                    
                    # Free Cash Flow
                    free_cf = cashflow.loc['Free Cash Flow', col] if 'Free Cash Flow' in cashflow.index else 0
                    free_cf_data.append(free_cf if free_cf else 0)  # Keep raw values
            
            # Reverse data to show oldest to newest
            years.reverse()
            revenue_data.reverse()
            gross_income_data.reverse()
            net_income_data.reverse()
            operating_cf_data.reverse()
            free_cf_data.reverse()
            
            # Create bar chart data for modal
            chart_data = {
                'years': years,
                'revenue': revenue_data,
                'gross_income': gross_income_data,
                'net_income': net_income_data,
                'operating_cf': operating_cf_data,
                'free_cf': free_cf_data
            }
            
            # Determine scale and format data
            max_revenue = max([abs(x) for x in revenue_data]) if revenue_data else 0
            scale_billions = max_revenue >= 1e9
            scale_factor = 1e9 if scale_billions else 1e6
            scale_label = "B" if scale_billions else "M"
            
            # Format data for display
            def format_value(val, scale_factor):
                if val == 0:
                    return "0"
                scaled = val / scale_factor
                return f"{scaled:.1f}" if abs(scaled) < 10 else f"{scaled:.0f}"
            
            # Create simple bar chart HTML
            max_val = max(max([abs(x) for x in revenue_data]) if revenue_data else [0], 
                         max([abs(x) for x in gross_income_data]) if gross_income_data else [0],
                         max([abs(x) for x in net_income_data]) if net_income_data else [0],
                         max([abs(x) for x in operating_cf_data]) if operating_cf_data else [0],
                         max([abs(x) for x in free_cf_data]) if free_cf_data else [0])
            
            revenue_bars = ''.join([f'<div style="display: inline-block; width: 60px; margin: 2px; text-align: center;"><div style="height: {int(abs(rev)/max_val*100) if max_val > 0 else 0}px; background: #007acc; margin-bottom: 5px;"></div><small>{year}<br>${format_value(rev, scale_factor)}{scale_label}</small></div>' for year, rev in zip(years, revenue_data)])
            
            # Combined income bars showing both Gross and Net Income with negative axis
            income_bars = ''.join([
                f'<div style="display: inline-block; width: 80px; margin: 2px; text-align: center;">'
                f'<div style="position: relative; height: 120px; display: flex; justify-content: center; align-items: center; gap: 2px;">'
                f'<div style="position: absolute; bottom: 50%; width: 100%; height: 1px; background: #ccc; opacity: 0.5;"></div>'
                f'<div style="width: 18px; height: {int(abs(gross)/max_val*50) if max_val > 0 else 0}px; background: #ffc107; border-radius: 2px; align-self: flex-end; margin-bottom: 60px;" title="Gross: ${format_value(gross, scale_factor)}{scale_label}"></div>'
                f'<div style="width: 18px; height: {int(abs(net)/max_val*50) if max_val > 0 else 0}px; background: {"#28a745" if net >= 0 else "#dc3545"}; border-radius: 2px; {"align-self: flex-end; margin-bottom: 60px;" if net >= 0 else "align-self: flex-start; margin-top: 60px;"}" title="Net: ${format_value(net, scale_factor)}{scale_label}"></div>'
                f'</div>'
                f'<small>{year}<br>G:${format_value(gross, scale_factor)}{scale_label}<br>N:${format_value(net, scale_factor)}{scale_label}</small>'
                f'</div>'
                for year, gross, net in zip(years, gross_income_data, net_income_data)
            ])
            
            # Combined cash flow bars showing both Operating and Free Cash Flow with negative axis
            cf_bars = ''.join([
                f'<div style="display: inline-block; width: 80px; margin: 2px; text-align: center;">'
                f'<div style="position: relative; height: 200px; display: flex; justify-content: center; align-items: center; gap: 4px;">'
                f'<div style="position: absolute; bottom: 35%; width: 100%; height: 1px; background: #666; opacity: 0.7;"></div>'
                f'<div style="width: 25px; height: {int(abs(op_cf)/max_val*90) if max_val > 0 else 0}px; background: {"#17a2b8" if op_cf >= 0 else "#ffc107"}; border-radius: 2px; {"align-self: flex-end; margin-bottom: 70px;" if op_cf >= 0 else "align-self: flex-start; margin-top: 70px;"}" title="Operating CF: ${format_value(op_cf, scale_factor)}{scale_label}"></div>'
                f'<div style="width: 25px; height: {int(abs(free_cf)/max_val*90) if max_val > 0 else 0}px; background: {"#28a745" if free_cf >= 0 else "#dc3545"}; border-radius: 2px; {"align-self: flex-end; margin-bottom: 70px;" if free_cf >= 0 else "align-self: flex-start; margin-top: 70px;"}" title="Free CF: ${format_value(free_cf, scale_factor)}{scale_label}"></div>'
                f'</div>'
                f'<small>{year}<br>Op:${format_value(op_cf, scale_factor)}{scale_label}<br>Free:${format_value(free_cf, scale_factor)}{scale_label}</small>'
                f'</div>'
                for year, op_cf, free_cf in zip(years, operating_cf_data, free_cf_data)
            ])
            
            # Latest year metrics for card preview (now last in reversed array)
            latest_revenue = revenue_data[-1] if revenue_data else 0
            latest_gross_income = gross_income_data[-1] if gross_income_data else 0
            latest_net_income = net_income_data[-1] if net_income_data else 0
            latest_op_cf = operating_cf_data[-1] if operating_cf_data else 0
            latest_free_cf = free_cf_data[-1] if free_cf_data else 0
            
            # Format latest values for card display
            latest_revenue_display = format_value(latest_revenue, scale_factor)
            latest_gross_display = format_value(latest_gross_income, scale_factor)
            latest_net_display = format_value(latest_net_income, scale_factor)
            latest_op_cf_display = format_value(latest_op_cf, scale_factor)
            latest_free_cf_display = format_value(latest_free_cf, scale_factor)
            
            # Calculate metrics outside f-string (compare latest to previous year)
            revenue_growth = f"{((revenue_data[-1] - revenue_data[-2]) / revenue_data[-2] * 100):.1f}%" if len(revenue_data) > 1 and revenue_data[-2] != 0 else 'N/A'
            gross_margin = f"{(latest_gross_income / latest_revenue * 100):.1f}%" if latest_revenue != 0 else 'N/A'
            net_margin = f"{(latest_net_income / latest_revenue * 100):.1f}%" if latest_revenue != 0 else 'N/A'
            capex_ratio = f"{((latest_op_cf - latest_free_cf) / latest_op_cf * 100):.1f}%" if latest_op_cf != 0 else 'N/A'
            
            financial_card = f"""
            <div style="min-width: 200px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>📊 Financials</h5>
                <p><strong>Revenue:</strong> ${latest_revenue_display}{scale_label}</p>
                <p><strong>Gross Income:</strong> ${latest_gross_display}{scale_label}</p>
                <p><strong>Net Income:</strong> ${latest_net_display}{scale_label}</p>
                <p><strong>Op Cash Flow:</strong> ${latest_op_cf_display}{scale_label}</p>
                <p><strong>Free Cash Flow:</strong> ${latest_free_cf_display}{scale_label}</p>
                <p><strong>Years:</strong> {len(years)} years</p>
                <button onclick="showModal('financials_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="financials_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="financials_{sanitized_ticker}_content" style="background-color: white; margin: 3% auto; padding: 20px; border-radius: 10px; width: 90%; max-width: 900px; max-height: 85%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">📊 {ticker} Financial Statements</h3>
                            <div>
                                <button id="financials_{sanitized_ticker}_maximize" onclick="maximizeModal('financials_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="financials_{sanitized_ticker}_restore" onclick="restoreModal('financials_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('financials_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        
                        <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                            <div style="flex: 1; min-width: 250px;">
                                <h4>📈 Revenue Trend ({"Billions" if scale_billions else "Millions"} $)</h4>
                                <div style="display: flex; align-items: end; height: 150px; border-bottom: 1px solid #ccc; padding: 10px;">
                                    {revenue_bars}
                                </div>
                            </div>
                            
                            <div style="flex: 1; min-width: 300px;">
                                <h4>💰 Income Trend ({"Billions" if scale_billions else "Millions"} $)</h4>
                                <div style="display: flex; align-items: center; height: 150px; border-bottom: 1px solid #ccc; padding: 10px; position: relative;">
                                    {income_bars}
                                </div>
                                <div style="margin-top: 5px; font-size: 12px; text-align: center;">
                                    <span style="color: #ffc107;">■</span> Gross Income &nbsp;
                                    <span style="color: #28a745;">■</span> Net Income (Profit) &nbsp;
                                    <span style="color: #dc3545;">■</span> Net Income (Loss)
                                </div>
                            </div>
                            
                            <div style="flex: 1; min-width: 300px;">
                                <h4>💧 Cash Flow Trend ({"Billions" if scale_billions else "Millions"} $)</h4>
                                <div style="display: flex; align-items: center; height: 220px; border-bottom: 1px solid #ccc; padding: 10px; position: relative;">
                                    {cf_bars}
                                </div>
                                <div style="margin-top: 5px; font-size: 12px; text-align: center;">
                                    <span style="color: #17a2b8;">■</span> Operating CF (Positive) &nbsp;
                                    <span style="color: #ffc107;">■</span> Operating CF (Negative) &nbsp;
                                    <span style="color: #28a745;">■</span> Free CF (Positive) &nbsp;
                                    <span style="color: #dc3545;">■</span> Free CF (Negative)
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin-top: 20px;">
                            <h4>📋 Key Financial Metrics Summary</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                    <strong>Latest Revenue:</strong> ${latest_revenue_display}{scale_label}<br>
                                    <strong>Revenue Growth:</strong> {revenue_growth}
                                </div>
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                    <strong>Latest Gross Income:</strong> ${latest_gross_display}{scale_label}<br>
                                    <strong>Gross Margin:</strong> {gross_margin}
                                </div>
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                    <strong>Latest Net Income:</strong> ${latest_net_display}{scale_label}<br>
                                    <strong>Net Margin:</strong> {net_margin}
                                </div>
                                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                                    <strong>Operating CF:</strong> ${latest_op_cf_display}{scale_label}<br>
                                    <strong>Free CF:</strong> ${latest_free_cf_display}{scale_label}<br>
                                    <strong>CapEx Ratio:</strong> {capex_ratio}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
            all_cards.append(financial_card)
            
        except Exception as e:
            # Fallback card if financial data unavailable
            financial_card = f"""
            <div style="min-width: 200px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>📊 Financials</h5>
                <p style="color: #dc3545;">Financial data unavailable</p>
                <p><small>Error: {str(e)[:50]}...</small></p>
            </div>
            """
            all_cards.append(financial_card)
        
        # DCF Card with modal
        if 'dcf' in analyses:
            dcf_data = analyses['dcf']
            params = dcf_data.get('parameters_used', {})
            dcf_calcs = dcf_data.get('dcf_calculations', {})
            params_html = ''.join([f"<p>• {key}: {value}</p>" for key, value in params.items()]) if params else "<p>No parameters available</p>"
            calcs_html = ''.join([f"<p>• {key}: {value}</p>" for key, value in dcf_calcs.items()]) if dcf_calcs else "<p>No calculations available</p>"
            
            dcf_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>💰 DCF</h5>
                <p><strong>Rec:</strong> {dcf_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${dcf_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Upside:</strong> {(dcf_data.get('upside_downside_pct', 0) or 0):.1f}%</p>
                <button onclick="showModal('dcf_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="dcf_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="dcf_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">💰 {ticker} DCF Analysis Details</h3>
                            <div>
                                <button id="dcf_{sanitized_ticker}_maximize" onclick="maximizeModal('dcf_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="dcf_{sanitized_ticker}_restore" onclick="restoreModal('dcf_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('dcf_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <h4>Parameters:</h4>
                        {params_html}
                        <h4>Calculations:</h4>
                        {calcs_html}
                        <p><strong>Confidence:</strong> {dcf_data.get('confidence', 'N/A')}</p>
                        <p><strong>Method:</strong> {dcf_data.get('method', 'N/A')}</p>
                    </div>
                </div>
            </div>
            """
            all_cards.append(dcf_card)
            

        
        # Technical Card with modal
        if 'technical' in analyses:
            tech_data = analyses['technical']
            indicators = ['rsi_14', 'ma_20', 'ma_50', 'ma_200', 'macd_line', 'macd_signal']
            indicators_html = ''.join([f"<p>• {indicator.upper()}: {tech_data.get(indicator, 'N/A')}</p>" for indicator in indicators if tech_data.get(indicator) is not None])
            
            tech_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>📈 Technical</h5>
                <p><strong>Rec:</strong> {tech_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${tech_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>MACD Trend:</strong> {tech_data.get('trend', 'N/A')}</p>
                <p><strong>Volume:</strong> {tech_data.get('volume_trend', 'N/A')}</p>                
                <button onclick="showModal('tech_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="tech_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="tech_{sanitized_ticker}_content" style="background-color: white; margin: 2% auto; padding: 20px; border-radius: 10px; width: 90%; max-width: 800px; max-height: 90%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">📈 {ticker} Technical Analysis Details</h3>
                            <div>
                                <button id="tech_{sanitized_ticker}_maximize" onclick="maximizeModal('tech_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="tech_{sanitized_ticker}_restore" onclick="restoreModal('tech_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('tech_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 20px;">
                            <div style="flex: 1;">
                                <h4>Technical Indicators:</h4>
                                {indicators_html}
                            </div>
                            <div style="flex: 1;">
                                <h4>Technical Signals:</h4>
                                {tech_data.get('technical_signals', 'N/A')}
                            </div>
                            <div style="flex: 1;">
                                <h4>Price Chart (Last 30 Days):</h4>
                                <div id="price_chart_{sanitized_ticker}" style="height: 400px; width: 100%; border: 1px solid #ddd; padding: 10px; background: #f9f9f9;">
                                    <div style="text-align: center; margin-top: 180px; color: #666;">📈 Loading price chart...</div>
                                </div>
                                <script>
                                console.log('DEBUG: Creating chart for {sanitized_ticker}');
                                window.chartData_{sanitized_ticker} = {tech_data.get('chart_data', {})};
                                setTimeout(() => {{
                                    const chartDiv = document.getElementById('price_chart_{sanitized_ticker}');
                                    const chartData = window.chartData_{sanitized_ticker};
                                    
                                    if (!chartData || !chartData.prices || chartData.prices.length === 0) {{
                                        chartDiv.innerHTML = '<div style="text-align: center; margin-top: 180px; color: #666;">Chart data not available</div>';
                                        return;
                                    }}
                                    
                                    const prices = chartData.prices;
                                    const dates = chartData.dates || [];
                                    const maxPrice = Math.max(...prices);
                                    const minPrice = Math.min(...prices);
                                    const priceRange = maxPrice - minPrice || 1;
                                    
                                    let chartHtml = '<div style="position: relative; height: 350px; padding: 20px;">';
                                    chartHtml += '<svg width="100%" height="300" style="position: absolute; top: 20px;">';
                                    
                                    let pathData = '';
                                    prices.forEach((price, i) => {{
                                        const x = (i / (prices.length - 1)) * 90 + 5;
                                        const y = ((maxPrice - price) / priceRange) * 80 + 10;
                                        pathData += i === 0 ? `M${{x}} ${{y}}` : ` L${{x}} ${{y}}`;
                                    }});
                                    
                                    chartHtml += `<path d="${{pathData}}" stroke="#007acc" stroke-width="2" fill="none"/>`;
                                    chartHtml += '</svg>';
                                    chartHtml += `<div style="position: absolute; top: 20px; left: 5px; font-size: 12px; color: #666;">$${{maxPrice.toFixed(2)}}</div>`;
                                    chartHtml += `<div style="position: absolute; bottom: 50px; left: 5px; font-size: 12px; color: #666;">$${{minPrice.toFixed(2)}}</div>`;
                                    
                                    if (dates.length > 0) {{
                                        chartHtml += `<div style="position: absolute; bottom: 20px; left: 20px; font-size: 11px; color: #666;">${{dates[0]}}</div>`;
                                        chartHtml += `<div style="position: absolute; bottom: 20px; right: 20px; font-size: 11px; color: #666;">${{dates[dates.length-1]}}</div>`;
                                    }}
                                    
                                    chartHtml += '</div>';
                                    chartDiv.innerHTML = chartHtml;
                                }}, 100);
                                </script>

                            </div>                            
                        </div>
                    </div>
                </div>
            </div>
            """
            all_cards.append(tech_card)
            

        
        # Comparable Card with modal
        if 'comparable' in analyses:
            comp_data = analyses['comparable']
            multiples = comp_data.get('target_multiples', {})
            peers = comp_data.get('peer_tickers', [])
            peer_avg = comp_data.get('peer_averages', {})
            current_mult = comp_data.get('current_multiples', {})
            
            multiples_html = ''.join([f"<p>• {k.upper()}: {v:.1f}x</p>" for k, v in multiples.items()]) if multiples else "<p>No multiples available</p>"
            peers_html = ', '.join(peers[:5]) if peers else "No peers listed"
            # Handle None values in comparison
            comparison_items = []
            if peer_avg and current_mult:
                for k in peer_avg.keys():
                    if k in current_mult:
                        current_val = current_mult.get(k, 0)
                        peer_val = peer_avg.get(k, 0)
                        current_str = f"{current_val:.1f}" if current_val is not None else "N/A"
                        peer_str = f"{peer_val:.1f}" if peer_val is not None else "N/A"
                        comparison_items.append(f"<p>• {k.upper()}: Current {current_str} vs Peer Avg {peer_str}</p>")
            comparison_html = ''.join(comparison_items) if comparison_items else "<p>No comparison data</p>"
            
            comp_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>📊 Comparable</h5>
                <p><strong>Rec:</strong> {comp_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${comp_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>P/E:</strong> {multiples.get('pe', 'N/A')}x</p>
                <button onclick="showModal('comp_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="comp_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="comp_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">📊 {ticker} Comparable Analysis Details</h3>
                            <div>
                                <button id="comp_{sanitized_ticker}_maximize" onclick="maximizeModal('comp_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="comp_{sanitized_ticker}_restore" onclick="restoreModal('comp_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('comp_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <h4>Target Multiples:</h4>
                        {multiples_html}
                        <h4>Peer Companies:</h4>
                        <p>{peers_html}</p>
                        <h4>Valuation Comparison:</h4>
                        {comparison_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(comp_card)
        
        # Startup Card with modal (moved before AI Insights)
        if 'startup' in analyses:
            startup_data = analyses['startup']
            risk_factors = startup_data.get('risk_factors', [])
            risk_html = ''.join([f"<p>• {risk}</p>" for risk in risk_factors]) if risk_factors else "<p>No risk factors listed</p>"
            
            startup_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>🚀 Startup</h5>
                <p><strong>Rec:</strong> {startup_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${startup_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Stage:</strong> {startup_data.get('stage', 'N/A')}</p>
                <button onclick="showModal('startup_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="startup_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="startup_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">🚀 {ticker} Startup Valuation Details</h3>
                            <div>
                                <button id="startup_{sanitized_ticker}_maximize" onclick="maximizeModal('startup_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="startup_{sanitized_ticker}_restore" onclick="restoreModal('startup_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('startup_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <p><strong>Cash Runway:</strong> {startup_data.get('cash_runway_years', 0):.1f} years</p>
                        <p><strong>Quarterly Burn:</strong> ${startup_data.get('quarterly_burn_rate', 0):,.0f}</p>
                        <p><strong>Growth Quality:</strong> {startup_data.get('growth_quality', 'N/A')}</p>
                        <p><strong>Risk Score:</strong> {startup_data.get('risk_score', 0)}/100</p>
                        <p><strong>Investment Type:</strong> {startup_data.get('investment_type', 'N/A')}</p>
                        <p><strong>Confidence Level:</strong> {startup_data.get('confidence_level', 'N/A')}</p>
                        <h4>Risk Factors:</h4>
                        {risk_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(startup_card)
        
        # AI Insights Card with modal
        if 'ai_insights' in analyses:
            ai_data = analyses['ai_insights']
            ai_insights = ai_data.get('ai_insights', {})
            strengths = ai_insights.get('key_strengths', [])
            risks = ai_insights.get('key_risks', [])
            strengths_html = ''.join([f"<p>• {strength}</p>" for strength in strengths]) if strengths else "<p>No strengths listed</p>"
            risks_html = ''.join([f"<p>• {risk}</p>" for risk in risks]) if risks else "<p>No risks listed</p>"
            
            ai_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>🤖 AI Insights</h5>
                <p><strong>Rec:</strong> {ai_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${ai_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Position:</strong> {ai_insights.get('market_position', 'N/A')}</p>
                <button onclick="showModal('ai_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="ai_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="ai_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">🤖 {ticker} AI Insights Details</h3>
                            <div>
                                <button id="ai_{sanitized_ticker}_maximize" onclick="maximizeModal('ai_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="ai_{sanitized_ticker}_restore" onclick="restoreModal('ai_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('ai_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <p><strong>Growth Prospects:</strong> {ai_insights.get('growth_prospects', 'N/A')}</p>
                        <p><strong>Competitive Advantage:</strong> {ai_insights.get('competitive_advantage', 'N/A')}</p>
                        <h4>Key Strengths:</h4>
                        {strengths_html}
                        <h4>Key Risks:</h4>
                        {risks_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(ai_card)
            

        
        # Business Model Card with modal
        if 'business_model' in analyses:
            bm_data = analyses['business_model']
            strengths = bm_data.get('strengths', [])
            risks = bm_data.get('risks', [])
            strengths_html = ''.join([f"<p>• {strength}</p>" for strength in strengths]) if strengths else "<p>No strengths listed</p>"
            risks_html = ''.join([f"<p>• {risk}</p>" for risk in risks]) if risks else "<p>No risks listed</p>"
            
            bm_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>🏢 Business Model</h5>
                <p><strong>Rec:</strong> {bm_data.get('recommendation', 'N/A')}</p>
                <p><strong>Type:</strong> {bm_data.get('business_model_type', 'N/A')}</p>
                <p><strong>Quality:</strong> {bm_data.get('revenue_quality', 'N/A')}</p>
                <button onclick="showModal('bm_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="bm_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="bm_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">🏢 {ticker} Business Model Details</h3>
                            <div>
                                <button id="bm_{sanitized_ticker}_maximize" onclick="maximizeModal('bm_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="bm_{sanitized_ticker}_restore" onclick="restoreModal('bm_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('bm_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <p><strong>Primary Revenue Stream:</strong> {bm_data.get('primary_revenue_stream', 'N/A')}</p>
                        <p><strong>Competitive Moat:</strong> {bm_data.get('competitive_moat', 'N/A')}</p>
                        <p><strong>Scalability Score:</strong> {bm_data.get('scalability_score', 'N/A')}</p>
                        <p><strong>Recurring Revenue:</strong> {bm_data.get('recurring_percentage', 0)*100:.1f}%</p>
                        <h4>Strengths:</h4>
                        {strengths_html}
                        <h4>Risks:</h4>
                        {risks_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(bm_card)
        
        # Financial Health Card with modal
        if 'financial_health' in analyses:
            fh_data = analyses['financial_health']
            strengths = fh_data.get('strengths', [])
            risks = fh_data.get('key_risks', [])
            strengths_html = ''.join([f"<p>• {strength}</p>" for strength in strengths]) if strengths else "<p>No strengths listed</p>"
            risks_html = ''.join([f"<p>• {risk}</p>" for risk in risks]) if risks else "<p>No risks listed</p>"
            
            fh_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>💊 Financial Health</h5>
                <p><strong>Grade:</strong> {fh_data.get('overall_grade', 'N/A')}</p>
                <p><strong>Cash Flow:</strong> {fh_data.get('cash_flow_score', 'N/A')}</p>
                <p><strong>Debt:</strong> {fh_data.get('debt_score', 'N/A')}</p>
                <button onclick="showModal('fh_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="fh_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="fh_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">💊 {ticker} Financial Health Details</h3>
                            <div>
                                <button id="fh_{sanitized_ticker}_maximize" onclick="maximizeModal('fh_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="fh_{sanitized_ticker}_restore" onclick="restoreModal('fh_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('fh_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <p><strong>Filing Date:</strong> {fh_data.get('filing_date', 'N/A')}</p>
                        <p><strong>Revenue Score:</strong> {fh_data.get('revenue_score', 'N/A')}</p>
                        <p><strong>Overall Grade:</strong> {fh_data.get('overall_grade', 'N/A')}</p>
                        <h4>Strengths:</h4>
                        {strengths_html}
                        <h4>Key Risks:</h4>
                        {risks_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(fh_card)
        
        # Analyst Consensus Card with modal
        if 'analyst_consensus' in analyses:
            analyst_data = analyses['analyst_consensus']
            
            # Handle None values for formatting
            rec_mean = analyst_data.get('recommendation_mean')
            rec_mean_str = f"{rec_mean:.1f}" if rec_mean is not None else "N/A"
            
            upside_pct = analyst_data.get('upside_downside_pct')
            upside_str = f"{upside_pct:.1f}" if upside_pct is not None else "N/A"
            
            # Handle None values for analyst data
            predicted_price = analyst_data.get('predicted_price', 0) or 0
            target_high = analyst_data.get('target_high', 0) or 0
            target_low = analyst_data.get('target_low', 0) or 0
            
            analyst_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>👥 Analyst</h5>
                <p><strong>Rec:</strong> {analyst_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${predicted_price or 0:.2f}</p>
                <p><strong>Count:</strong> {analyst_data.get('num_analysts', 0)}</p>
                <button onclick="showModal('analyst_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="analyst_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="analyst_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">👥 {ticker} Analyst Consensus Details</h3>
                            <div>
                                <button id="analyst_{sanitized_ticker}_maximize" onclick="maximizeModal('analyst_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="analyst_{sanitized_ticker}_restore" onclick="restoreModal('analyst_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('analyst_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <p><strong>Consensus Target:</strong> ${predicted_price:.2f}</p>
                        <p><strong>High Target:</strong> ${target_high:.2f}</p>
                        <p><strong>Low Target:</strong> ${target_low:.2f}</p>
                        <p><strong>Number of Analysts:</strong> {analyst_data.get('num_analysts', 0)}</p>
                        <p><strong>Recommendation Mean:</strong> {rec_mean_str}</p>
                        <p><strong>Upside to Target:</strong> {upside_str}%</p>
                        <p><strong>Confidence:</strong> {analyst_data.get('confidence', 'N/A')}</p>
                    </div>
                </div>
            </div>
            """
            all_cards.append(analyst_card)
        
        # News Sentiment Card with modal
        if 'news_sentiment' in analyses:
            news_data = analyses['news_sentiment']
            recent_news = news_data.get('recent_news', [])
            news_html = ''.join([
                f"""<div style="margin-bottom: 15px; padding: 10px; border-left: 3px solid #007acc;">
                <h5>{article.get('title', 'No title')}</h5>
                <p><strong>Source:</strong> {article.get('source', 'Unknown')} | <strong>Date:</strong> {article.get('date', 'N/A')} | <strong>Sentiment:</strong> {article.get('sentiment_score', 0):.2f}</p>
                <p><strong>Summary:</strong> {article.get('summary', 'No summary')[:200]}...</p>
                {'<p><a href="' + article['url'] + '" target="_blank">Read Article</a></p>' if article.get('url') else ''}
                </div>"""
                for article in recent_news[:5]
            ]) if recent_news else "<p>No recent news available</p>"
            
            news_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-right: 10px; background: #fff; position: relative;">
                <h5>📰 News</h5>
                <p><strong>Rec:</strong> {news_data.get('recommendation', 'N/A')}</p>
                <p><strong>Score:</strong> {news_data.get('overall_sentiment_score', 0) or 0:.2f}</p>
                <p><strong>Count:</strong> {news_data.get('news_count', 0)}</p>
                <button onclick="showModal('news_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="news_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div id="news_{sanitized_ticker}_content" style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; transition: all 0.3s ease;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">📰 {ticker} News Sentiment Details</h3>
                            <div>
                                <button id="news_{sanitized_ticker}_maximize" onclick="maximizeModal('news_{sanitized_ticker}')" style="background: #28a745; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px;">⛶</button>
                                <button id="news_{sanitized_ticker}_restore" onclick="restoreModal('news_{sanitized_ticker}')" style="background: #ffc107; color: black; border: none; padding: 4px 8px; border-radius: 3px; font-size: 12px; cursor: pointer; margin-right: 5px; display: none;">❐</button>
                                <span onclick="closeModal('news_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                            </div>
                        </div>
                        <p><strong>Overall Sentiment:</strong> {news_data.get('sentiment_rating', 'N/A')} ({news_data.get('overall_sentiment_score', 0):.2f})</p>
                        <h4>Recent Articles:</h4>
                        {news_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(news_card)

        
        # Combine all cards with modal JavaScript
        cards_html = ''.join(all_cards)
        scrollable_row = f"""
        <div style="display: flex; overflow-x: auto; overflow-y: visible; padding: 10px 0; gap: 10px; height: 320px;">
            {cards_html}
        </div>
        <script>
        function showModal(modalId) {{
            document.getElementById(modalId).style.display = 'block';
        }}
        function closeModal(modalId) {{
            document.getElementById(modalId).style.display = 'none';
        }}
        function maximizeModal(modalId) {{
            const content = document.getElementById(modalId + '_content');
            const maximizeBtn = document.getElementById(modalId + '_maximize');
            const restoreBtn = document.getElementById(modalId + '_restore');
            
            content.style.width = '95%';
            content.style.height = '95%';
            content.style.maxWidth = 'none';
            content.style.maxHeight = 'none';
            content.style.margin = '2.5% auto';
            
            maximizeBtn.style.display = 'none';
            restoreBtn.style.display = 'inline-block';
        }}
        function restoreModal(modalId) {{
            const content = document.getElementById(modalId + '_content');
            const maximizeBtn = document.getElementById(modalId + '_maximize');
            const restoreBtn = document.getElementById(modalId + '_restore');
            
            // Restore original size based on modal type
            if (modalId.startsWith('tech_') || modalId.startsWith('financials_')) {{
                content.style.width = '90%';
                content.style.maxWidth = modalId.startsWith('financials_') ? '900px' : '800px';
                content.style.margin = '3% auto';
                content.style.maxHeight = '85%';
            }} else {{
                content.style.width = '80%';
                content.style.maxWidth = '600px';
                content.style.margin = '5% auto';
                content.style.maxHeight = '80%';
            }}
            content.style.height = 'auto';
            
            maximizeBtn.style.display = 'inline-block';
            restoreBtn.style.display = 'none';
        }}
        window.onclick = function(event) {{
            if (event.target.classList.contains('modal')) {{
                event.target.style.display = 'none';
            }}
        }}
        </script>
        """
        
        # Calculate dynamic height based on number of cards
        card_count = len(all_cards)
        dynamic_height = max(200, min(400, card_count * 50 + 100))
        st.components.v1.html(scrollable_row, height=dynamic_height)
        
        st.markdown("---")

def generate_batch_text_summary(results):
    """Generate text summary of batch analysis results for scrollable display"""
    text_lines = []
    text_lines.append("=" * 80)
    text_lines.append("BATCH ANALYSIS RESULTS SUMMARY")
    text_lines.append("=" * 80)
    text_lines.append("")
    
    for ticker, data in results.items():
        if 'error' in data:
            text_lines.append(f"❌ {ticker}: FAILED - {data['error']}")
            text_lines.append("-" * 40)
            continue
        
        # Header
        text_lines.append(f"✅ {ticker} - ANALYSIS COMPLETE")
        text_lines.append("-" * 40)
        
        # Basic info
        company_type = data.get('company_type', 'N/A')
        final_rec = data.get('final_recommendation', {})
        recommendation = final_rec.get('recommendation', 'N/A')
        target_price = final_rec.get('target_price', 0) or 0
        
        
        text_lines.append(f"Company Type: {company_type}")
        text_lines.append(f"Final Recommendation: {recommendation}")
        text_lines.append(f"Target Price: ${target_price:.2f}" if target_price else "Target Price: N/A")
        
        # Individual analyzer results
        analyses = data.get('analyses', {})
        if analyses:
            text_lines.append("\nAnalyzer Results:")
            for analyzer, result in analyses.items():
                if result and not result.get('error'):
                    rec = result.get('recommendation', 'N/A')
                    price = result.get('predicted_price', 0) or 0
                    confidence = result.get('confidence', 'N/A')
                    text_lines.append(f"  • {analyzer.upper()}: {rec} | ${price:.2f} | {confidence}")
        
        # Key insights for specific analyzers
        if 'ai_insights' in analyses and analyses['ai_insights']:
            ai_data = analyses['ai_insights']
            ai_insights = ai_data.get('ai_insights', {})
            if ai_insights:
                text_lines.append("\nAI Insights:")
                text_lines.append(f"  Market Position: {ai_insights.get('market_position', 'N/A')}")
                text_lines.append(f"  Growth Prospects: {ai_insights.get('growth_prospects', 'N/A')}")
                text_lines.append(f"  Competitive Advantage: {ai_insights.get('competitive_advantage', 'N/A')}")
        
        if 'news_sentiment' in analyses and analyses['news_sentiment']:
            news_data = analyses['news_sentiment']
            sentiment_score = news_data.get('overall_sentiment_score', 0)
            news_count = news_data.get('news_count', 0)
            text_lines.append(f"\nNews Sentiment: {sentiment_score:.2f} ({news_count} articles)")
        
        if 'technical' in analyses and analyses['technical']:
            tech_data = analyses['technical']
            trend = tech_data.get('trend', 'N/A')
            rsi = tech_data.get('rsi_14', 'N/A')
            text_lines.append(f"\nTechnical: Trend={trend}, RSI={rsi}")
        
        text_lines.append("")
        text_lines.append("=" * 80)
        text_lines.append("")
    
    return "\n".join(text_lines)

if __name__ == "__main__":
    show_detailed_analysis()
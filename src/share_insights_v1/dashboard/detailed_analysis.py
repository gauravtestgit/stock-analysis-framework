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
        
        # Analyzer selection
        st.subheader("Select Analyzers")
        available_analyzers = [
            "dcf", "technical", "comparable", "startup", 
            "ai_insights", "news_sentiment", "business_model", 
            "financial_health", "analyst_consensus"
        ]
        
        selected_analyzers = st.multiselect(
            "Choose analyzers to run:",
            available_analyzers,
            default=available_analyzers,
            help="Select which analysis methods to include. Startup analyzer runs for loss-making companies."
        )
        
        if st.button("Analyze Stock") and ticker:
            if selected_analyzers:
                analyze_single_stock(ticker, selected_analyzers)
            else:
                st.error("Please select at least one analyzer")
    
    else:  # Watchlist Batch
        watchlist = get_watchlist()
        
        if not watchlist:
            st.info("No stocks in watchlist. Add stocks using the sidebar.")
            return
        
        st.write(f"**Watchlist ({len(watchlist)} stocks):** {', '.join(watchlist)}")
        
        # Analyzer selection for batch
        st.subheader("Select Analyzers for Batch")
        available_analyzers = [
            "dcf", "technical", "comparable", "startup", 
            "ai_insights", "news_sentiment", "business_model", 
            "financial_health", "analyst_consensus"
        ]
        
        batch_analyzers = st.multiselect(
            "Choose analyzers for batch analysis:",
            available_analyzers,
            default=available_analyzers,
            help="Select which analysis methods to run for all stocks"
        )
        
        if st.button("Analyze All Watchlist Stocks"):
            if batch_analyzers:
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
    """Get current stock price using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
    except:
        return None

def display_detailed_results(ticker, data):
    """Display comprehensive analysis results"""
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
    
    # Optional: Keep expandable sections for individual deep dive
    with st.expander("🔍 Individual Stock Deep Dive (Expandable Sections)"):
        with st.container(height=400):
            for ticker, data in results.items():
                with st.expander(f"{ticker} - {'✅ Success' if 'error' not in data else '❌ Failed'}"):
                    if 'error' not in data:
                        display_detailed_results(ticker, data)
                    else:
                        st.error(f"Analysis failed: {data['error']}")

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
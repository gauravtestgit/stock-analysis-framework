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
from src.share_insights_v1.implementations.llm_providers.config_service import LLMConfigService
from src.share_insights_v1.utils.prompt_loader import ThesisPromptLoader
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer
from src.share_insights_v1.utils.formatters import format_currency, get_scale_and_label
from src.share_insights_v1.utils.logging import (
    log_page_view,
    log_user_action,
    log_batch_analysis_start,
    log_batch_analysis_complete,
    log_api_call,
    log_api_response,
    log_error
)
import yaml

def load_llm_config():
    """Load LLM configuration from config file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'llm_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('llm_providers', [])
    except Exception as e:
        st.error(f"Failed to load LLM config: {e}")
        return []

def get_provider_models(providers_config, provider_name):
    """Get models for a specific provider"""
    for provider in providers_config:
        if provider['name'] == provider_name:
            return provider.get('models', [])
    return []

def show_thesis_generation():
    """Show thesis generation page with full detailed analysis functionality"""
    
    # Check for show_history query parameter
    query_params = st.query_params
    if 'show_history' in query_params:
        ticker = query_params['show_history']
        show_thesis_history(ticker)
        # Clear the query parameter
        del st.query_params['show_history']
        return
    
    st.title("📝 Investment Thesis Generator")
    show_disclaimer()
    st.markdown("*Generate comprehensive investment theses with full analysis capabilities*")
    
    # Log page view
    log_page_view('thesis_generation', metadata={'mode': 'initial_load'})
    
    from watchlist_component import get_watchlist, show_watchlist_sidebar
    
    # Show watchlist in sidebar
    show_watchlist_sidebar()
    
    # Load LLM configuration
    providers_config = load_llm_config()
    
    # LLM Provider Selection (affects both analysis and thesis generation)
    st.subheader("🤖 LLM Provider Selection")
    col1, col2 = st.columns(2)
    
    with col1:
        # Provider selection
        provider_options = [(p['name'], f"{p['display_name']} {p['icon']}") for p in providers_config if os.getenv(p['api_key_env'])]
        if provider_options:
            selected_provider_name = st.selectbox(
                "Provider:",
                options=[p[0] for p in provider_options],
                format_func=lambda x: next(p[1] for p in provider_options if p[0] == x),
                key="global_provider_selector"
            )
        else:
            st.error("No LLM providers available (missing API keys)")
            selected_provider_name = None
    
    with col2:
        # Model selection based on selected provider
        if selected_provider_name:
            models = get_provider_models(providers_config, selected_provider_name)
            if models:
                selected_model = st.selectbox(
                    "Model:",
                    options=[m['name'] for m in models],
                    format_func=lambda x: next(f"{m['display_name']} ({m['name']})" for m in models if m['name'] == x),
                    key="global_model_selector"
                )
            else:
                st.error(f"No models available for {selected_provider_name}")
                selected_model = None
        else:
            selected_model = None
    
    # Initialize shared LLM manager with selected provider/model
    if selected_provider_name and selected_model:
        try:
            shared_llm_manager = LLMManager(use_plugin_system=True)
            shared_llm_manager.set_primary_provider(selected_provider_name, selected_model)
            st.session_state.thesis_llm_manager = shared_llm_manager
            # Store provider and model names for API calls
            st.session_state.thesis_llm_provider = selected_provider_name
            st.session_state.thesis_llm_model = selected_model
            st.success(f"✅ Using {selected_provider_name} with {selected_model}")
        except Exception as e:
            st.error(f"Failed to initialize LLM provider: {e}")
            shared_llm_manager = LLMManager()
            st.session_state.thesis_llm_manager = shared_llm_manager
            # Clear provider/model on failure
            st.session_state.thesis_llm_provider = None
            st.session_state.thesis_llm_model = None
    else:
        # Fallback to default
        shared_llm_manager = LLMManager()
        st.session_state.thesis_llm_manager = shared_llm_manager
        # Clear provider/model when no selection
        st.session_state.thesis_llm_provider = None
        st.session_state.thesis_llm_model = None
    
    # Define available analyzers for both modes
    available_analyzers = [
        "dcf", "technical", "comparable", "startup", 
        "ai_insights", "news_sentiment", "business_model", 
        "financial_health", "analyst_consensus", "industry_analysis",
        "competitive_position", "management_quality"
    ]
    
    # Analysis mode selection
    analysis_mode = st.radio("Analysis Mode:", ["Watchlist Batch", "Single Stock"])
    
    if analysis_mode == "Single Stock":
        # Stock input
        ticker = st.text_input("Enter Stock Ticker:", value="AAPL").upper()
        
        # News sentiment options
        st.subheader("News Sentiment Options")
        col1, col2, col3 = st.columns(3)
        with col1:
            enable_web_scraping = st.checkbox("Enable Web Scraping", value=True, help="Fetch full article content for better accuracy (slower)")
        with col2:
            enable_llm_sentiment = st.checkbox("Enable LLM Sentiment", value=True, help="Use AI for sentiment analysis (slower but more accurate)")
        with col3:
            max_news_articles = st.number_input(
                "Max News Articles",
                min_value=1,
                max_value=20,
                value=5,
                help="Number of news articles to analyze for sentiment"
            )
        
        # Analyzer selection
        st.subheader("Select Analyzers")
        
        selected_analyzers = st.multiselect(
            "Choose analyzers to run:",
            available_analyzers,
            default=available_analyzers,
            help="Select which analysis methods to include. Startup analyzer runs for loss-making companies."
        )
        
        if st.button("🔍 Analyze Stock") and ticker:
            if not selected_provider_name or not selected_model:
                st.error("Please select LLM provider and model first")
            elif selected_analyzers:
                # Store news sentiment options in session state
                st.session_state.news_options = {
                    'enable_web_scraping': enable_web_scraping,
                    'enable_llm_sentiment': enable_llm_sentiment,
                    'max_news_articles': max_news_articles
                }
                # Pass LLM manager to analysis
                analyze_single_stock(ticker, selected_analyzers, st.session_state.thesis_llm_manager, max_news_articles)
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
        col1, col2, col3 = st.columns(3)
        with col1:
            batch_web_scraping = st.checkbox("Enable Web Scraping (Batch)", value=False, help="Fetch full article content (much slower for batch)")
        with col2:
            batch_llm_sentiment = st.checkbox("Enable LLM Sentiment (Batch)", value=False, help="Use AI for sentiment analysis (slower for batch)")
        with col3:
            batch_max_news_articles = st.number_input(
                "Max News Articles (Batch)",
                min_value=1,
                max_value=20,
                value=7,
                help="Number of news articles per stock for batch analysis"
            )
        
        # Analyzer selection for batch
        st.subheader("Select Analyzers for Batch")
        batch_analyzers = st.multiselect(
            "Choose analyzers for batch analysis:",
            available_analyzers,
            default=available_analyzers,
            help="Select which analysis methods to run for all stocks"
        )
        
        if st.button("Analyze All Watchlist Stocks"):
            # Log batch analysis button click
            log_user_action(
                action='BATCH_ANALYSIS_CLICKED',
                page='thesis_generation',
                metadata={
                    'stock_count': len(watchlist),
                    'analyzers': batch_analyzers,
                    'llm_provider': selected_provider_name,
                    'llm_model': selected_model
                }
            )
            
            if not selected_provider_name or not selected_model:
                st.error("Please select LLM provider and model first")
            elif batch_analyzers:
                # Store batch news sentiment options
                st.session_state.batch_news_options = {
                    'enable_web_scraping': batch_web_scraping,
                    'enable_llm_sentiment': batch_llm_sentiment,
                    'max_news_articles': batch_max_news_articles
                }
                # Pass LLM manager to batch analysis
                analyze_watchlist_batch(watchlist, batch_analyzers, st.session_state.thesis_llm_manager, batch_max_news_articles)
            else:
                st.error("Please select at least one analyzer")
    
    # Get available thesis types dynamically (outside conditional blocks)
    prompt_loader = ThesisPromptLoader()
    available_prompts = prompt_loader.list_available_prompts()
    
    # Convert prompt types to display names dynamically
    thesis_options = [prompt.replace('_', ' ').title() for prompt in available_prompts]
    
    # Display analysis data if loaded
    if 'thesis_analysis_data' in st.session_state and 'thesis_ticker' in st.session_state:
        display_detailed_results(st.session_state.thesis_ticker, st.session_state.thesis_analysis_data)
        
        # Thesis generation section
        st.markdown("---")
        st.subheader("🎯 Generate Investment Thesis")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            thesis_type = st.selectbox("Thesis Type:", thesis_options)
        with col2:
            prompt_chaining = st.checkbox("Prompt Chaining", help="Use output from previous prompt as input to next prompt")
        with col3:
            generate_button = st.button("🚀 Generate Thesis", type="primary")
            if st.button("🔄 Refresh Prompts"):
                st.rerun()
        
        # Handle thesis generation
        if generate_button:
            if not selected_provider_name or not selected_model:
                st.error("Please select LLM provider and model first")
            else:
                latest_analysis_data = st.session_state.thesis_analysis_data
                latest_ticker = st.session_state.thesis_ticker
                
                st.info(f"Generating thesis using analysis from: {latest_analysis_data.get('timestamp', 'Unknown time')}")
                st.info(f"Using LLM: {selected_provider_name} with {selected_model}")
                
                # Convert display name back to prompt type dynamically
                prompt_type = thesis_type.lower().replace(' ', '_')
                
                # Debug the prompt type conversion
                print(f"🔍 DEBUG: thesis_type='{thesis_type}', prompt_type='{prompt_type}'")
                
                # Check if prompt file exists, if not try alternative names
                prompt_loader = ThesisPromptLoader()
                available_prompts = prompt_loader.list_available_prompts()
                print(f"🔍 DEBUG: Available prompts: {available_prompts}")
                
                if prompt_type not in available_prompts:
                    # Try alternative mappings
                    if prompt_type == 'objective_case':
                        prompt_type = 'objective_case'
                    elif prompt_type == 'product_portfolio_catalyst':
                        prompt_type = 'product_portfolio_catalyst'
                    print(f"🔍 DEBUG: Mapped to prompt_type='{prompt_type}'")
                
                # Handle prompt chaining
                if prompt_chaining:
                    # Initialize stock-specific prompt outputs if not exists
                    if 'stock_prompt_outputs' not in st.session_state:
                        st.session_state.stock_prompt_outputs = {}
                    
                    # Get previous output for this specific stock
                    previous_output = st.session_state.stock_prompt_outputs.get(latest_ticker, '')
                    
                    # Generate thesis with chaining
                    thesis_response = generate_investment_thesis(
                        latest_ticker, 
                        latest_analysis_data, 
                        thesis_type,
                        st.session_state.thesis_llm_manager,
                        show_prompt=True,
                        return_response=True,
                        previous_output=previous_output
                    )
                    
                    # Store output for this specific stock
                    if thesis_response:
                        st.session_state.stock_prompt_outputs[latest_ticker] = thesis_response
                        st.success(f"✅ Thesis generated and stored for {latest_ticker} chaining ({len(thesis_response)} characters)")
                else:
                    # Regular generation without chaining
                    generate_investment_thesis(
                        latest_ticker, 
                        latest_analysis_data, 
                        thesis_type,
                        st.session_state.thesis_llm_manager,
                        show_prompt=True
                    )
    
    # Display persisted batch results if available
    if 'batch_results' in st.session_state and 'batch_timing' in st.session_state:
        st.markdown("---")
        st.subheader(f"📊 Previous Batch Analysis Results ({len(st.session_state.batch_watchlist)} stocks)")
        display_batch_results(st.session_state.batch_results, st.session_state.batch_timing)
        
        # Batch thesis generation section
        successful_stocks = {ticker: data for ticker, data in st.session_state.batch_results.items() if 'error' not in data}
        if successful_stocks:
            batch_thesis_fragment(successful_stocks, thesis_options, selected_provider_name, selected_model)

@st.fragment
def batch_thesis_fragment(successful_stocks, thesis_options, selected_provider_name, selected_model):
    """Fragment for batch thesis generation to prevent full page refresh"""
    st.markdown("---")
    st.subheader("🎯 Generate Thesis from Batch Results")
    
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        selected_stock = st.selectbox(
            "Select Stock:",
            options=list(successful_stocks.keys()),
            key="batch_thesis_stock_selector"
        )
    with col2:
        batch_thesis_type = st.selectbox(
            "Thesis Type:", 
            thesis_options,
            key="batch_thesis_type_selector"
        )
    with col3:
        batch_prompt_chaining = st.checkbox("Prompt Chaining", help="Use output from previous prompt as input to next prompt", key="batch_prompt_chaining")
    with col4:
        generate_thesis_button = st.button("🚀 Generate Thesis", key="batch_thesis_generate")
    
    # Handle batch thesis generation
    if generate_thesis_button:
        if not selected_provider_name or not selected_model:
            st.error("Please select LLM provider and model first")
        elif selected_stock and selected_stock in successful_stocks:
            st.info(f"Using LLM: {selected_provider_name} with {selected_model}")
            
            # Handle prompt chaining for batch
            if batch_prompt_chaining:
                # Initialize stock-specific prompt outputs if not exists
                if 'stock_prompt_outputs' not in st.session_state:
                    st.session_state.stock_prompt_outputs = {}
                
                # Get previous output for this specific stock
                previous_output = st.session_state.stock_prompt_outputs.get(selected_stock, '')
                
                thesis_response = generate_investment_thesis(
                    selected_stock,
                    successful_stocks[selected_stock],
                    batch_thesis_type,
                    st.session_state.thesis_llm_manager,
                    show_prompt=True,
                    return_response=True,
                    previous_output=previous_output
                )
                if thesis_response:
                    st.session_state.stock_prompt_outputs[selected_stock] = thesis_response
                    st.success(f"✅ Thesis generated and stored for {selected_stock} chaining ({len(thesis_response)} characters)")
            else:
                generate_investment_thesis(
                    selected_stock,
                    successful_stocks[selected_stock],
                    batch_thesis_type,
                    st.session_state.thesis_llm_manager,
                    show_prompt=True
                )

def analyze_watchlist_batch(watchlist, selected_analyzers=None, llm_manager=None, max_news_articles=5):
    """Analyze all stocks in watchlist with selected analyzers in parallel"""
    import uuid
    
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Track batch timing
    batch_start = time.time()
    
    # Get LLM configuration from session state
    llm_provider = None
    llm_model = None
    if 'thesis_llm_provider' in st.session_state and 'thesis_llm_model' in st.session_state:
        llm_provider = st.session_state.thesis_llm_provider
        llm_model = st.session_state.thesis_llm_model
    
    # Parallel execution with balanced workers for performance and cost
    max_workers = min(len(watchlist), 4)  # Balanced for performance and cost
    
    # Log batch analysis start
    log_batch_analysis_start(
        watchlist=watchlist,
        analyzers=selected_analyzers or [],
        metadata={
            'max_workers': max_workers,
            'llm_provider': llm_provider,
            'llm_model': llm_model,
            'max_news_articles': max_news_articles
        }
    )
    status_text.text(f"Starting parallel analysis of {len(watchlist)} stocks with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all analysis tasks - let orchestrator generate stock_analysis_id
        future_to_ticker = {
            executor.submit(analyze_single_stock_api, ticker, selected_analyzers, llm_provider, llm_model, max_news_articles): ticker
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
    
    # Log batch analysis complete
    successful = len([r for r in results.values() if 'error' not in r])
    failed = len(results) - successful
    
    log_batch_analysis_complete(
        stock_count=len(watchlist),
        success_count=successful,
        failed_count=failed,
        duration=total_batch_time,
        metadata={
            'max_workers': max_workers,
            'avg_time_per_stock': total_batch_time / len(watchlist) if watchlist else 0
        }
    )
    
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
    
    # Debug: Print batch_analysis_id availability for each ticker
    print("\n🔍 DEBUG: Batch analysis ID availability:")
    for ticker, data in results.items():
        if 'error' not in data:
            batch_id = data.get('batch_analysis_id')
            print(f"  {ticker}: {batch_id if batch_id else 'MISSING'}")
        else:
            print(f"  {ticker}: ERROR - {data['error']}")
    print("")
    
    display_batch_results(results, batch_timing)

def analyze_single_stock_api(ticker, selected_analyzers=None, llm_provider=None, llm_model=None, max_news_articles=5):
    """Analyze a single stock via API - helper function for parallel execution"""
    from src.share_insights_v1.utils.logging import generate_request_id, set_request_id
    
    # Generate unique request ID for this ticker analysis
    request_id = generate_request_id()
    set_request_id(request_id)
    
    try:
        stock_start = time.time()
        
        endpoint = f"http://localhost:8000/analyze/{ticker}"
        request_data = {"ticker": ticker}
        if selected_analyzers:
            request_data["enabled_analyzers"] = selected_analyzers
        if llm_provider:
            request_data["llm_provider"] = llm_provider
        if llm_model:
            request_data["llm_model"] = llm_model
        if max_news_articles != 5:  # Only include if different from default
            request_data["max_news_articles"] = max_news_articles
        
        # Log API call with request ID
        log_api_call(
            endpoint=endpoint,
            method='POST',
            ticker=ticker,
            metadata={
                'request_id': request_id,
                'analyzers': selected_analyzers,
                'llm_provider': llm_provider,
                'llm_model': llm_model
            }
        )
        
        # Send request ID in headers for API to use
        headers = {'X-Request-ID': request_id}
        response = requests.post(endpoint, json=request_data, headers=headers)
        stock_end = time.time()
        
        if response.status_code == 200:
            # Log successful API response
            log_api_response(
                endpoint=endpoint,
                status_code=response.status_code,
                duration=stock_end - stock_start,
                success=True,
                metadata={'ticker': ticker, 'request_id': request_id}
            )
            data = response.json()
            
            # Debug: Show what API actually returned
            print(f"🔍 DEBUG: API response keys for {ticker}: {list(data.keys())}")
            
            # Debug: Check financial_metrics content
            if 'financial_metrics' in data:
                fm = data['financial_metrics']
                print(f"🔍 DEBUG: financial_metrics keys: {list(fm.keys()) if fm else 'None'}")
                print(f"🔍 DEBUG: trailing_eps={fm.get('trailing_eps')} (type: {type(fm.get('trailing_eps'))}), forward_eps={fm.get('forward_eps')} (type: {type(fm.get('forward_eps'))}), shares_outstanding={fm.get('shares_outstanding')} (type: {type(fm.get('shares_outstanding'))}), float_shares={fm.get('float_shares')} (type: {type(fm.get('float_shares'))})")  
            else:
                print(f"⚠️ WARNING: No financial_metrics in API response for {ticker}")
            
            data['dashboard_timing'] = {
                'total_request_time': round(stock_end - stock_start, 2),
                'orchestrator_time': data.get('execution_time_seconds', 0),
                'analyses_count': data.get('analyses_count', 0)
            }
            # Ensure batch_analysis_id is available for thesis linking
            if 'batch_analysis_id' not in data:
                print(f"⚠️ WARNING: No batch_analysis_id returned for {ticker} (request_id: {request_id})")
            else:
                print(f"✅ DEBUG: batch_analysis_id found for {ticker}: {data['batch_analysis_id']} (request_id: {request_id})")
            return ticker, data
        else:
            # Log failed API response
            log_api_response(
                endpoint=endpoint,
                status_code=response.status_code,
                duration=stock_end - stock_start,
                success=False,
                error=response.text,
                metadata={'ticker': ticker, 'request_id': request_id}
            )
            return ticker, {"error": response.text}
    except Exception as e:
        # Log error
        log_error(
            error_type='API_CALL_EXCEPTION',
            error_message=str(e),
            page='thesis_generation',
            metadata={'ticker': ticker, 'endpoint': endpoint, 'request_id': request_id if 'request_id' in locals() else 'unknown'}
        )
        return ticker, {"error": str(e)}

def display_batch_results(results, batch_timing=None):
    """Display batch analysis results with tabbed interface"""
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
    
    # Quick summary table
    if successful > 0:
        summary_data = []
        for ticker, data in results.items():
            if 'error' not in data:
                current_price = data.get('financial_metrics', {}).get('current_price') or 0
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
    
    # Tabbed interface for detailed results
    st.markdown("---")
    st.subheader("🔍 Detailed Analysis by Stock")
    display_tabbed_batch_results(results)

def display_tabbed_batch_results(results):
    """Display batch results with stock selector and analyzer tabs"""
    
    # Filter successful results
    successful_results = {ticker: data for ticker, data in results.items() if 'error' not in data}
    
    if not successful_results:
        st.warning("No successful analyses to display")
        return
    
    # Initialize selected stock in session state
    if 'selected_batch_stock' not in st.session_state:
        st.session_state.selected_batch_stock = list(successful_results.keys())[0]
    
    # Create two columns: stock selector (left) and analyzer tabs (right)
    col_stocks, col_analysis = st.columns([1, 3])
    
    with col_stocks:
        st.markdown("### 🎯 Select Stock")
        
        # Stock selector buttons
        for ticker in successful_results.keys():
            data = successful_results[ticker]
            final_rec = data.get('final_recommendation', {})
            recommendation = final_rec.get('recommendation', 'N/A')
            
            is_selected = ticker == st.session_state.selected_batch_stock
            
            # Use custom HTML button for selected stock to get green outline
            if is_selected:
                button_html = f"""
                <button style="
                    width: 100%;
                    padding: 0.5rem 1rem;
                    background: #123d1c;
                    color: white;
                    border: 3px solid #123d1c;
                    border-radius: 0.5rem;
                    font-size: 1rem;
                    cursor: default;
                    margin-bottom: 0.5rem;
                    box-shadow: 0 0 0 0.2rem rgba(40, 167, 69, 0.25);
                ">{ticker} - {recommendation}</button>
                """
                st.markdown(button_html, unsafe_allow_html=True)
            else:
                # Regular Streamlit button for non-selected stocks
                if st.button(
                    f"{ticker} - {recommendation}",
                    key=f"stock_btn_{ticker}",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.selected_batch_stock = ticker
                    st.rerun()
    
    with col_analysis:
        selected_ticker = st.session_state.selected_batch_stock
        
        # Safety check: if selected ticker not in results, reset to first available
        if selected_ticker not in successful_results:
            st.session_state.selected_batch_stock = list(successful_results.keys())[0]
            st.rerun()
            return
        
        selected_data = successful_results[selected_ticker]
        
        st.markdown(f"### 📊 Analysis for {selected_ticker}")
        
        # Display basic info
        analyses = selected_data.get('analyses', {})
        financial_metrics = selected_data.get('financial_metrics', {})
        # Use cached price from analysis data
        current_price = financial_metrics.get('current_price') or 0
        final_rec = selected_data.get('final_recommendation', {})
        
        # Quick metrics row
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        with metric_col1:
            st.metric("Current Price", f"${current_price:.2f}" if current_price else "N/A")
        with metric_col2:
            target_price = final_rec.get('target_price', 0) or 0
            st.metric("Target Price", f"${target_price:.2f}" if target_price else "N/A")
        with metric_col3:
            if current_price and target_price:
                upside = ((target_price - current_price) / current_price) * 100
                st.metric("Upside", f"{upside:+.1f}%")
            else:
                st.metric("Upside", "N/A")
        with metric_col4:
            st.metric("Recommendation", final_rec.get('recommendation', 'N/A'))
        
        st.markdown("---")
        
        # Inject CSS to make tabs horizontally scrollable with always-visible scrollbar
        st.markdown("""
        <style>
        button[data-baseweb="tab"] {
            flex-shrink: 0 !important;
        }
        div[data-baseweb="tab-list"] {
            gap: 8px;
            overflow-x: scroll !important;
            overflow-y: hidden !important;
            flex-wrap: nowrap !important;
            scrollbar-width: thin;
            scrollbar-color: #888 #f0f0f0;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar {
            height: 14px;
            display: block !important;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar-track {
            background: #f0f0f0;
            border-radius: 7px;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 7px;
            border: 2px solid #f0f0f0;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create tabs for each analyzer
        analyzer_names = [
            "Overview", "DCF", "Technical", "Comparable", "Startup",
            "AI Insights", "News", "Business Model", "Financial Health",
            "Analyst Consensus", "Industry", "Competitive Position", "Management"
        ]
        
        tabs = st.tabs(analyzer_names)
        
        # Overview Tab
        with tabs[0]:
            display_overview_tab(selected_ticker, selected_data, analyses)
        
        # DCF Tab
        with tabs[1]:
            display_analyzer_tab(selected_ticker, analyses, 'dcf', 'DCF Analysis')
        
        # Technical Tab
        with tabs[2]:
            display_analyzer_tab(selected_ticker, analyses, 'technical', 'Technical Analysis')
        
        # Comparable Tab
        with tabs[3]:
            display_analyzer_tab(selected_ticker, analyses, 'comparable', 'Comparable Analysis')
        
        # Startup Tab
        with tabs[4]:
            display_analyzer_tab(selected_ticker, analyses, 'startup', 'Startup Analysis')
        
        # AI Insights Tab
        with tabs[5]:
            display_analyzer_tab(selected_ticker, analyses, 'ai_insights', 'AI Insights')
        
        # News Tab
        with tabs[6]:
            display_analyzer_tab(selected_ticker, analyses, 'news_sentiment', 'News Sentiment')
        
        # Business Model Tab
        with tabs[7]:
            display_analyzer_tab(selected_ticker, analyses, 'business_model', 'Business Model')
        
        # Financial Health Tab
        with tabs[8]:
            display_analyzer_tab(selected_ticker, analyses, 'financial_health', 'Financial Health')
        
        # Analyst Consensus Tab
        with tabs[9]:
            display_analyzer_tab(selected_ticker, analyses, 'analyst_consensus', 'Analyst Consensus')
        
        # Industry Tab
        with tabs[10]:
            display_analyzer_tab(selected_ticker, analyses, 'industry_analysis', 'Industry Analysis')
        
        # Competitive Position Tab
        with tabs[11]:
            display_analyzer_tab(selected_ticker, analyses, 'competitive_position', 'Competitive Position')
        
        # Management Tab
        with tabs[12]:
            display_analyzer_tab(selected_ticker, analyses, 'management_quality', 'Management Quality')

def display_overview_tab(ticker, data, analyses):
    """Display overview tab with summary of all analyses"""
    
    # Add CSS for smaller metric font size
    st.markdown("""
    <style>
    [data-testid="stMetricLabel"] {
        font-size: 0.7rem !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 0.9rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Business Summary
    financial_metrics = data.get('financial_metrics', {})
    business_summary = financial_metrics.get('business_summary', '')
    if business_summary:
        st.markdown("### 📋 Business Summary")
        st.write(business_summary)
        st.markdown("---")
    
    # Basic Info Cards
    st.markdown("### 📊 Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        market_cap = financial_metrics.get('market_cap', 0) or 0
        st.metric("Market Cap", f"${market_cap:,.0f}")
        pe_ratio = financial_metrics.get('pe_ratio', 'N/A')
        st.metric("P/E Ratio", pe_ratio)
    
    with col2:
        industry = financial_metrics.get('industry', 'N/A')
        st.metric("Industry", industry)
        sector = financial_metrics.get('sector', 'N/A')
        st.metric("Sector", sector)
    
    with col3:
        roe = financial_metrics.get('roe', 0)
        st.metric("ROE", f"{roe*100:.1f}%" if isinstance(roe, (int, float)) else roe)
        debt_ratio = financial_metrics.get('debt_to_equity', 'N/A')
        st.metric("Debt/Equity", debt_ratio)
    
    with col4:
        revenue_growth = financial_metrics.get('revenue_growth', 0)
        st.metric("Revenue Growth", f"{revenue_growth*100:.1f}%" if isinstance(revenue_growth, (int, float)) else revenue_growth)
        current_ratio = financial_metrics.get('current_ratio', 'N/A')
        st.metric("Current Ratio", current_ratio)
    
    st.markdown("---")
    
    # Financial Info with Charts
    st.markdown("### 📊 Financial Information")
    display_financial_info_with_charts(ticker, financial_metrics)
    
    st.markdown("---")
    
    # Company info
    st.markdown("### 🏛️ Company Information")
    st.markdown(f"**Company Type:** {data.get('company_type', 'N/A')}")
    st.markdown(f"**Industry:** {industry}")
    st.markdown(f"**Sector:** {sector}")
    
    st.markdown("---")
    st.markdown("### 📈 Analysis Methods Run")
    
    # Create summary table of all analyses
    analysis_summary = []
    for analysis_type, analysis_data in analyses.items():
        if isinstance(analysis_data, dict):
            analysis_summary.append({
                'Method': analysis_type.replace('_', ' ').title(),
                'Recommendation': analysis_data.get('recommendation', 'N/A'),
                'Target Price': f"${analysis_data.get('predicted_price', 0) or 0:.2f}",
                'Confidence': analysis_data.get('confidence', 'N/A')
            })
    
    if analysis_summary:
        st.dataframe(pd.DataFrame(analysis_summary), use_container_width=True)
    else:
        st.info("No analysis data available")

def display_financial_info_with_charts(ticker, financial_metrics):
    """Display financial info card with revenue, income, and cash flow charts"""
    try:
        revenue_data_statements = financial_metrics.get('revenue_data_statements', {})
        
        # Extract latest values
        latest_revenue = 0
        latest_gross_income = 0
        latest_net_income = 0
        latest_op_cf = 0
        latest_free_cf = 0
        
        annual_income = revenue_data_statements.get('annual_income_stmt', {})
        if annual_income:
            latest_year = list(annual_income.keys())[0]
            annual_data = annual_income[latest_year]
            latest_revenue = annual_data.get('Total Revenue', 0) or 0
            latest_gross_income = annual_data.get('Gross Profit', 0) or 0
            latest_net_income = annual_data.get('Net Income', 0) or 0
        
        cashflow_data = revenue_data_statements.get('cashflow', {})
        if cashflow_data:
            latest_cf_date = list(cashflow_data.keys())[0]
            cf_data = cashflow_data[latest_cf_date]
            # Try multiple possible keys for operating cash flow
            latest_op_cf = (cf_data.get('Operating Cash Flow', 0) or 
                          cf_data.get('Total Cash From Operating Activities', 0) or 
                          cf_data.get('Cash Flowsfromusedin Operating Activities Direct', 0) or 
                          cf_data.get('OperatingCashFlow', 0) or 0)
            latest_free_cf = (cf_data.get('Free Cash Flow', 0) or 
                            cf_data.get('FreeCashFlow', 0) or 0)
        
        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Revenue", format_currency(latest_revenue))
        with col2:
            st.metric("Gross Income", format_currency(latest_gross_income))
        with col3:
            st.metric("Net Income", format_currency(latest_net_income))
        with col4:
            st.metric("Op Cash Flow", format_currency(latest_op_cf))
        with col5:
            st.metric("Free Cash Flow", format_currency(latest_free_cf))
        
        # Show charts button with unique key based on context
        import hashlib
        context_hash = hashlib.md5(str(id(revenue_data_statements)).encode()).hexdigest()[:8]
        if st.button("📈 View Financial Charts", key=f"charts_{ticker}_{context_hash}"):
            display_financial_charts_modal(ticker, revenue_data_statements)
    
    except Exception as e:
        st.error(f"Financial data unavailable: {str(e)}")

def display_financial_charts_modal(ticker, revenue_data_statements):
    """Display financial charts in expander"""
    with st.expander("📈 Financial Charts", expanded=True):
        # Build chart data - use a common date list to ensure alignment
        revenue_data = []
        gross_income_data = []
        net_income_data = []
        operating_cf_data = []
        free_cf_data = []
        years = []
        
        # Get all available dates from all sources
        annual_revenue = revenue_data_statements.get('annual_revenue', {})
        annual_income = revenue_data_statements.get('annual_income_stmt', {})
        cashflow_data = revenue_data_statements.get('cashflow', {})
        
        # Use the dates from annual_revenue as the primary source
        if annual_revenue:
            for date_str in reversed(sorted(annual_revenue.keys())):
                years.append(date_str[:4])
                revenue_data.append(annual_revenue.get(date_str, 0))
                
                # Get corresponding data from other sources using the same date
                if annual_income and date_str in annual_income:
                    income_data = annual_income[date_str]
                    gross_income_data.append(income_data.get('Gross Profit', 0) or 0)
                    net_income_data.append(income_data.get('Net Income', 0) or 0)
                else:
                    gross_income_data.append(0)
                    net_income_data.append(0)
                
                if cashflow_data and date_str in cashflow_data:
                    cf_data = cashflow_data[date_str]
                    op_cf = (cf_data.get('Operating Cash Flow', 0) or 
                            cf_data.get('Total Cash From Operating Activities', 0) or 
                            cf_data.get('Cash Flowsfromusedin Operating Activities Direct', 0) or 
                            cf_data.get('OperatingCashFlow', 0) or 0)
                    free_cf = (cf_data.get('Free Cash Flow', 0) or 
                              cf_data.get('FreeCashFlow', 0) or 0)
                    operating_cf_data.append(op_cf)
                    free_cf_data.append(free_cf)
                else:
                    operating_cf_data.append(0)
                    free_cf_data.append(0)
        
        # Determine individual scales for each chart
        rev_max = max([abs(v) for v in revenue_data]) if revenue_data else 0
        rev_scale, rev_label = get_scale_and_label(rev_max)
        
        income_max = max([abs(v) for v in gross_income_data + net_income_data]) if (gross_income_data or net_income_data) else 0
        income_scale, income_label = get_scale_and_label(income_max)
        
        cf_max = max([abs(v) for v in operating_cf_data + free_cf_data]) if (operating_cf_data or free_cf_data) else 0
        cf_scale, cf_label = get_scale_and_label(cf_max)
        
        # Display charts
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Revenue Trend ({rev_label})**")
            chart_data = pd.DataFrame({'Year': years, 'Revenue': [r/rev_scale for r in revenue_data]})
            st.bar_chart(chart_data.set_index('Year'))
        
        with col2:
            st.markdown(f"**Income Trend ({income_label})**")
            chart_data = pd.DataFrame({
                'Year': years,
                'Gross': [g/income_scale for g in gross_income_data],
                'Net': [n/income_scale for n in net_income_data]
            })
            st.bar_chart(chart_data.set_index('Year'))
        
        with col3:
            st.markdown(f"**Cash Flow Trend ({cf_label})**")
            chart_data = pd.DataFrame({
                'Year': years,
                'Operating': [o/cf_scale for o in operating_cf_data],
                'Free': [f/cf_scale for f in free_cf_data]
            })
            st.bar_chart(chart_data.set_index('Year'))

def display_analyzer_tab(ticker, analyses, analyzer_key, analyzer_name):
    """Display individual analyzer tab content"""
    
    if analyzer_key not in analyses:
        st.info(f"{analyzer_name} was not run for this stock")
        return
    
    analysis_data = analyses[analyzer_key]
    
    if not analysis_data or 'error' in analysis_data:
        st.error(f"{analyzer_name} failed: {analysis_data.get('error', 'Unknown error')}")
        return
    
    # Display common fields
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Recommendation", analysis_data.get('recommendation', 'N/A'))
    with col2:
        target = analysis_data.get('predicted_price', 0) or 0
        st.metric("Target Price", f"${target:.2f}" if target else "N/A")
    with col3:
        st.metric("Confidence", analysis_data.get('confidence', 'N/A'))
    
    st.markdown("---")
    
    # Display analyzer-specific content
    if analyzer_key == 'dcf':
        display_dcf_details(analysis_data)
    elif analyzer_key == 'technical':
        display_technical_details(analysis_data, ticker)
    elif analyzer_key == 'comparable':
        display_comparable_details(analysis_data)
    elif analyzer_key == 'ai_insights':
        display_ai_insights_details(analysis_data)
    elif analyzer_key == 'news_sentiment':
        display_news_details(analysis_data)
    elif analyzer_key == 'business_model':
        display_business_model_details(analysis_data)
    elif analyzer_key == 'analyst_consensus':
        display_analyst_consensus_details(analysis_data)
    elif analyzer_key == 'industry_analysis':
        display_industry_analysis_details(analysis_data)
    elif analyzer_key == 'startup':
        display_startup_details(analysis_data)
    else:
        # Generic display for other analyzers
        st.json(analysis_data)

def display_dcf_details(data):
    """Display DCF analysis details"""
    st.markdown("### 💰 DCF Calculations")
    
    dcf_calcs = data.get('dcf_calculations', {})
    params = data.get('parameters_used', {})
    
    if dcf_calcs or params:
        dcf_html = ""
        
        if params:
            dcf_html += '<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #28a745; background: #f8f9fa;">'
            dcf_html += '<h6 style="margin: 0 0 8px 0; color: #28a745;">Parameters Used</h6>'
            for key, value in params.items():
                dcf_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• <strong>{key}:</strong> {value}</p>'
            dcf_html += '</div>'
        
        if dcf_calcs:
            dcf_html += '<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #007acc; background: #f8f9fa;">'
            dcf_html += '<h6 style="margin: 0 0 8px 0; color: #007acc;">DCF Calculations</h6>'
            for key, value in dcf_calcs.items():
                dcf_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• <strong>{key}:</strong> {value}</p>'
            dcf_html += '</div>'
        
        st.markdown(f'<div style="max-height: 500px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">{dcf_html}</div>', unsafe_allow_html=True)
    else:
        st.info("No DCF calculation details available")

def display_technical_details(data, ticker=None):
    """Display technical analysis details"""
    st.markdown("### 📈 Technical Indicators")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**RSI (14):** {data.get('rsi_14', 'N/A')}")
        st.write(f"**MACD:** {data.get('macd_line', 'N/A')}")
    with col2:
        st.write(f"**MA 20:** {data.get('ma_20', 'N/A')}")
        st.write(f"**MA 50:** {data.get('ma_50', 'N/A')}")
    with col3:
        st.write(f"**Trend:** {data.get('trend', 'N/A')}")
        st.write(f"**Volume:** {data.get('volume_trend', 'N/A')}")
    
    if ticker:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period="6mo")
            
            if not hist.empty:
                st.markdown("### 📊 Price Chart with Indicators")
                
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
                exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()
                
                chart_data = pd.DataFrame({
                    'Price': hist['Close'],
                    'MA20': hist['Close'].rolling(window=20).mean(),
                    'MA50': hist['Close'].rolling(window=50).mean()
                })
                st.line_chart(chart_data)
                
                st.markdown("**RSI (14)**")
                st.line_chart(pd.DataFrame({'RSI': rsi}))
                
                st.markdown("**MACD**")
                st.line_chart(pd.DataFrame({'MACD': macd, 'Signal': signal}))
        except Exception as e:
            st.warning(f"Could not load price chart: {str(e)}")
    
    signals = data.get('technical_signals', {})
    if signals:
        st.markdown("### 🚦 Signals")
        st.json(signals)

def display_comparable_details(data):
    """Display comparable analysis details"""
    st.markdown("### 📉 Valuation Multiples")
    
    multiples = data.get('target_multiples', {})
    if multiples:
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**P/E:** {multiples.get('pe', 'N/A')}x")
            st.write(f"**P/S:** {multiples.get('ps', 'N/A')}x")
        with col2:
            st.write(f"**P/B:** {multiples.get('pb', 'N/A')}x")
            st.write(f"**EV/EBITDA:** {multiples.get('ev_ebitda', 'N/A')}x")
    
    peers = data.get('peer_tickers', [])
    if peers:
        st.markdown("### 🏭 Peer Companies")
        st.write(", ".join(peers[:10]))

def display_ai_insights_details(data):
    """Display AI insights details"""
    st.markdown("### 🤖 AI Assessment")
    
    ai_insights = data.get('ai_insights', {})
    
    if ai_insights:
        ai_html = ""
        
        # Assessment metrics
        ai_html += '<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #17a2b8; background: #f8f9fa;">'
        ai_html += '<h6 style="margin: 0 0 8px 0; color: #17a2b8;">Assessment Metrics</h6>'
        ai_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• <strong>Market Position:</strong> {ai_insights.get("market_position", "N/A")}</p>'
        ai_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• <strong>Growth Prospects:</strong> {ai_insights.get("growth_prospects", "N/A")}</p>'
        ai_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• <strong>Competitive Advantage:</strong> {ai_insights.get("competitive_advantage", "N/A")}</p>'
        ai_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• <strong>Management Quality:</strong> {ai_insights.get("management_quality", "N/A")}</p>'
        ai_html += '</div>'
        
        # Key strengths
        strengths = ai_insights.get('key_strengths', [])
        if strengths:
            ai_html += '<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #28a745; background: #f8f9fa;">'
            ai_html += '<h6 style="margin: 0 0 8px 0; color: #28a745;">Key Strengths</h6>'
            for strength in strengths:
                ai_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• {strength}</p>'
            ai_html += '</div>'
        
        # Key risks
        risks = ai_insights.get('key_risks', [])
        if risks:
            ai_html += '<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #dc3545; background: #f8f9fa;">'
            ai_html += '<h6 style="margin: 0 0 8px 0; color: #dc3545;">Key Risks</h6>'
            for risk in risks:
                ai_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• {risk}</p>'
            ai_html += '</div>'
        
        st.markdown(f'<div style="max-height: 500px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">{ai_html}</div>', unsafe_allow_html=True)
    else:
        st.info("No AI insights available")

def display_news_details(data):
    """Display news sentiment details"""
    st.markdown("### 📰 News Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sentiment Score", f"{data.get('overall_sentiment_score', 0):.2f}")
    with col2:
        st.metric("Articles Analyzed", data.get('news_count', 0))
    with col3:
        st.metric("Recommendation", data.get('recommendation', 'N/A'))
    
    recent_news = data.get('recent_news', [])
    if recent_news:
        st.markdown("### 📰 Recent Articles")
        news_html = ""
        for i, article in enumerate(recent_news[:5], 1):
            news_html += f"""<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #007acc; background: #f8f9fa;">
                <h6 style="margin: 0 0 8px 0; color: #007acc;">Article {i}: {article.get('title', 'No title')}</h6>
                <p style="margin: 5px 0; font-size: 0.9em; color: #000;"><strong>Source:</strong> {article.get('source', 'Unknown')} | <strong>Date:</strong> {article.get('date', 'N/A')} | <strong>Sentiment:</strong> {article.get('sentiment_score', 0):.2f}</p>
                {f'<p style="margin: 5px 0; font-size: 0.85em; color: #000;"><a href="{article["url"]}" target="_blank" style="color: #007acc;">🔗 Read Article</a></p>' if article.get('url') else ''}
                {f'<p style="margin: 8px 0; font-size: 0.9em; color: #000;">{article["summary"][:200]}...</p>' if article.get('summary') else ''}
            """
            enhanced_facts = article.get('enhanced_facts')
            if enhanced_facts and any(enhanced_facts.values()):
                news_html += '<div style="background: #e8f4fd; padding: 10px; margin: 8px 0; border-radius: 5px;"><p style="margin: 0 0 5px 0; font-weight: bold; color: #0066cc;">🎯 Key Facts:</p>'
                if enhanced_facts.get('lead_fact'):
                    news_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• {enhanced_facts["lead_fact"]}</p>'
                if enhanced_facts.get('quantitative_evidence'):
                    news_html += f'<p style="margin: 3px 0; font-size: 0.9em; color: #000;">• {enhanced_facts["quantitative_evidence"]}</p>'
                if enhanced_facts.get('verbatim_quote'):
                    news_html += f'<p style="margin: 3px 0; font-size: 0.9em; font-style: italic; color: #000;">• "{enhanced_facts["verbatim_quote"]}"</p>'
                news_html += '</div>'
            news_html += '</div>'
        
        st.markdown(f'<div style="max-height: 500px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff;">{news_html}</div>', unsafe_allow_html=True)

def display_business_model_details(data):
    """Display business model details in styled cards"""
    st.markdown("### 🏢 Business Model")
    
    bm_html = '<div style="max-height: 500px; overflow-y: auto; padding: 10px;">'
    
    # Business model metrics card
    bm_html += '<div style="border-left: 3px solid #6f42c1; background: #f8f9fa; padding: 15px; margin-bottom: 15px; border-radius: 5px;">'
    bm_html += '<h4 style="margin-top: 0; color: #6f42c1;">📊 Business Model Metrics</h4>'
    bm_html += f'<p style="color: #000;"><strong>Type:</strong> {data.get("business_model_type", "N/A")}</p>'
    bm_html += f'<p style="color: #000;"><strong>Competitive Moat:</strong> {data.get("competitive_moat", "N/A")}</p>'
    bm_html += f'<p style="color: #000;"><strong>Scalability Score:</strong> {data.get("scalability_score", "N/A")}/10</p>'
    bm_html += '</div>'
    
    # Strengths card
    strengths = data.get('strengths', [])
    if strengths:
        bm_html += '<div style="border-left: 3px solid #28a745; background: #f8f9fa; padding: 15px; margin-bottom: 15px; border-radius: 5px;">'
        bm_html += '<h4 style="margin-top: 0; color: #28a745;">💪 Key Strengths</h4>'
        bm_html += '<ul style="margin: 0; padding-left: 20px; color: #000;">'
        for strength in strengths:
            bm_html += f'<li style="color: #000;">{strength}</li>'
        bm_html += '</ul></div>'
    
    # Risks card
    risks = data.get('risks', [])
    if risks:
        bm_html += '<div style="border-left: 3px solid #dc3545; background: #f8f9fa; padding: 15px; margin-bottom: 15px; border-radius: 5px;">'
        bm_html += '<h4 style="margin-top: 0; color: #dc3545;">⚠️ Key Risks</h4>'
        bm_html += '<ul style="margin: 0; padding-left: 20px; color: #000;">'
        for risk in risks:
            bm_html += f'<li style="color: #000;">{risk}</li>'
        bm_html += '</ul></div>'
    
    bm_html += '</div>'
    st.markdown(bm_html, unsafe_allow_html=True)

def display_analyst_consensus_details(data):
    """Display analyst consensus details"""
    st.markdown("### 👥 Analyst Ratings")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Consensus Target", f"${data.get('predicted_price', 0) or 0:.2f}")
    with col2:
        st.metric("High Target", f"${data.get('target_high', 0) or 0:.2f}")
    with col3:
        st.metric("Low Target", f"${data.get('target_low', 0) or 0:.2f}")
    
    st.write(f"**Number of Analysts:** {data.get('num_analysts', 0)}")

def display_industry_analysis_details(data):
    """Display industry analysis details"""
    st.markdown("### 🏭 Industry Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Outlook:** {data.get('industry_outlook', 'N/A')}")
        st.write(f"**Competitive Position:** {data.get('competitive_position', 'N/A')}")
    with col2:
        st.write(f"**Regulatory Risk:** {data.get('regulatory_risk', 'N/A')}")
        st.write(f"**ESG Score:** {data.get('esg_score', 0)}/10")
    
    porters = data.get('porters_five_forces', {})
    if porters:
        st.markdown("### 🛡️ Porter's Five Forces")
        st.json(porters)

def display_startup_details(data):
    """Display startup analysis details"""
    st.markdown("### 🚀 Startup Metrics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Stage:** {data.get('stage', 'N/A')}")
        st.write(f"**Cash Runway:** {data.get('cash_runway_years', 0):.1f} years")
    with col2:
        st.write(f"**Risk Score:** {data.get('risk_score', 0)}/100")
        st.write(f"**Growth Quality:** {data.get('growth_quality', 'N/A')}")

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
        
        text_lines.append("")
        text_lines.append("=" * 80)
        text_lines.append("")
    
    return "\n".join(text_lines)

def analyze_single_stock(ticker, selected_analyzers=None, llm_manager=None, max_news_articles=5):
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
            if max_news_articles != 5:  # Only include if different from default
                request_data["max_news_articles"] = max_news_articles
            
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
            params = analysis_data.get('parameters_used', {})
            dcf_calcs = analysis_data.get('dcf_calculations', {})
            params_html = ''.join([f"<p>• {key}: {value}</p>" for key, value in params.items()]) if params else "<p>No parameters available</p>"
            calcs_html = ''.join([f"<p>• {key}: {value}</p>" for key, value in dcf_calcs.items()]) if dcf_calcs else "<p>No calculations available</p>"
            
            dcf_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff; position: relative;">
                <h5>💰 DCF</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Upside:</strong> {(analysis_data.get('upside_downside_pct', 0) or 0):.1f}%</p>
                <p><strong>Confidence:</strong> {analysis_data.get('confidence', 'N/A')}</p>
                <button onclick="showModal('dcf_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="dcf_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: #1e1e1e; color: #e0e0e0; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; -webkit-font-smoothing: antialiased; color-scheme: dark;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0; color: #e0e0e0;">💰 {ticker} DCF Analysis Details</h3>
                            <span onclick="closeModal('dcf_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                        </div>
                        <h4>Parameters:</h4>
                        {params_html}
                        <h4>Calculations:</h4>
                        {calcs_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(dcf_card)
        
        elif analysis_type == 'technical':
            indicators = ['rsi_14', 'ma_20', 'ma_50', 'ma_200', 'macd_line', 'macd_signal']
            indicators_html = ''.join([f"<p>• {indicator.upper()}: {analysis_data.get(indicator, 'N/A')}</p>" for indicator in indicators if analysis_data.get(indicator) is not None])
            
            tech_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff; position: relative;">
                <h5>📈 Technical</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Trend:</strong> {analysis_data.get('trend', 'N/A')}</p>
                <p><strong>RSI:</strong> {analysis_data.get('rsi_14', 'N/A')}</p>
                <button onclick="showModal('tech_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="tech_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">📈 {ticker} Technical Analysis Details</h3>
                            <span onclick="closeModal('tech_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                        </div>
                        <h4>Technical Indicators:</h4>
                        {indicators_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(tech_card)
        
        elif analysis_type == 'ai_insights':
            ai_insights = analysis_data.get('ai_insights', {})
            strengths = ai_insights.get('key_strengths', [])
            risks = ai_insights.get('key_risks', [])
            strengths_html = ''.join([f"<p>• {strength}</p>" for strength in strengths]) if strengths else "<p>No strengths listed</p>"
            risks_html = ''.join([f"<p>• {risk}</p>" for risk in risks]) if risks else "<p>No risks listed</p>"
            
            ai_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff; position: relative;">
                <h5>🤖 AI Insights</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Position:</strong> {ai_insights.get('market_position', 'N/A')}</p>
                <p><strong>Growth:</strong> {ai_insights.get('growth_prospects', 'N/A')}</p>
                <button onclick="showModal('ai_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="ai_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: #1e1e1e; color: #e0e0e0; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; -webkit-font-smoothing: antialiased; color-scheme: dark;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0; color: #e0e0e0;">🤖 {ticker} AI Insights Details</h3>
                            <span onclick="closeModal('ai_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                        </div>
                        <h4>Key Strengths:</h4>
                        {strengths_html}
                        <h4>Key Risks:</h4>
                        {risks_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(ai_card)
        
        elif analysis_type == 'news_sentiment':
            recent_news = analysis_data.get('recent_news', [])
            news_html = ''.join([
                f"""<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #007acc; background: #f8f9fa;">
                <h6><a href="{article.get('url', '#')}" target="_blank" style="color: #007acc; text-decoration: none;">{article.get('title', 'No title')}</a></h6>
                <p style="margin: 5px 0;"><strong>Source:</strong> {article.get('source', 'Unknown')} | <strong>Sentiment:</strong> {article.get('sentiment_score', 0):.2f} | <strong>Date:</strong> {article.get('date', 'NA')}</p>
                <p style="margin: 5px 0; font-size: 0.9em; color: #666;">{article.get('summary', 'No summary available')[:200]}...</p>
                {f'''<div style="background: #e8f4fd; padding: 10px; margin: 10px 0; border-radius: 5px;">
                    <h6 style="color: #0066cc; margin: 0 0 8px 0;">🎯 Extracted Fact Block:</h6>
                    <p style="margin: 3px 0;"><strong>Lead Fact:</strong> {article.get('enhanced_facts', {}).get('lead_fact', 'Not extracted')}</p>
                    <p style="margin: 3px 0;"><strong>Quantitative:</strong> {article.get('enhanced_facts', {}).get('quantitative_evidence', 'Not extracted')}</p>
                    <p style="margin: 3px 0;"><strong>Business Impact:</strong> {article.get('enhanced_facts', {}).get('business_mechanism', 'Not extracted')}</p>
                    {f'<p style="margin: 3px 0;"><strong>Quote:</strong> "{article.get("enhanced_facts", {}).get("verbatim_quote", "")}"</p>' if article.get('enhanced_facts', {}).get('verbatim_quote') else ''}
                </div>''' if article.get('enhanced_facts') else '<p style="color: #999; font-style: italic;">No structured facts extracted (web scraping may be disabled)</p>'}
                </div>"""
                for article in recent_news
            ]) if recent_news else "<p>No recent news available</p>"
            
            news_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff; position: relative;">
                <h5>📰 News</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Score:</strong> {analysis_data.get('overall_sentiment_score', 0) or 0:.2f}</p>
                <p><strong>Count:</strong> {analysis_data.get('news_count', 0)}</p>
                <p><strong>Rating:</strong> {analysis_data.get('sentiment_rating', 'N/A')}</p>
                <button onclick="showModal('news_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="news_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: #1e1e1e; color: #e0e0e0; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto; -webkit-font-smoothing: antialiased; color-scheme: dark;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0; color: #e0e0e0;">📰 {ticker} News Sentiment Details</h3>
                            <span onclick="closeModal('news_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                        </div>
                        <h4>Recent Articles:</h4>
                        {news_html}
                    </div>
                </div>
            </div>
            """
            all_cards.append(news_card)
        
        elif analysis_type == 'comparable':
            multiples = analysis_data.get('target_multiples', {})
            peers = analysis_data.get('peer_tickers', [])
            peers_html = ', '.join(peers[:5]) if peers else "No peers listed"
            multiples_html = ''.join([f"<p>• {k.upper()}: {v:.1f}x</p>" for k, v in multiples.items()]) if multiples else "<p>No multiples available</p>"
            
            comp_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff; position: relative;">
                <h5>📊 Comparable</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Fair Value:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>P/E:</strong> {multiples.get('pe', 'N/A')}x</p>
                <button onclick="showModal('comp_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="comp_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">📊 {ticker} Comparable Analysis Details</h3>
                            <span onclick="closeModal('comp_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                        </div>
                        <h4>Target Multiples:</h4>
                        {multiples_html}
                        <h4>Peer Companies:</h4>
                        <p>{peers_html}</p>
                    </div>
                </div>
            </div>
            """
            all_cards.append(comp_card)
        
        elif analysis_type == 'analyst_consensus':
            analyst_card = f"""
            <div style="min-width: 180px; max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background: #fff; position: relative;">
                <h5>👥 Analyst</h5>
                <p><strong>Rec:</strong> {analysis_data.get('recommendation', 'N/A')}</p>
                <p><strong>Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                <p><strong>Count:</strong> {analysis_data.get('num_analysts', 0)}</p>
                <button onclick="showModal('analyst_{sanitized_ticker}')" style="background: #007acc; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 11px; cursor: pointer; margin-top: 5px;">🔍 Details</button>
                
                <div id="analyst_{sanitized_ticker}" class="modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5);">
                    <div style="background-color: white; margin: 5% auto; padding: 20px; border-radius: 10px; width: 80%; max-width: 600px; max-height: 80%; overflow-y: auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h3 style="margin: 0;">👥 {ticker} Analyst Consensus Details</h3>
                            <span onclick="closeModal('analyst_{sanitized_ticker}')" style="color: #aaa; font-size: 24px; font-weight: bold; cursor: pointer;">&times;</span>
                        </div>
                        <p><strong>Consensus Target:</strong> ${analysis_data.get('predicted_price', 0) or 0:.2f}</p>
                        <p><strong>High Target:</strong> ${analysis_data.get('target_high', 0) or 0:.2f}</p>
                        <p><strong>Low Target:</strong> ${analysis_data.get('target_low', 0) or 0:.2f}</p>
                        <p><strong>Number of Analysts:</strong> {analysis_data.get('num_analysts', 0)}</p>
                    </div>
                </div>
            </div>
            """
            all_cards.append(analyst_card)
    
    # Arrange cards in horizontal scroll
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
    
    st.components.v1.html(scrollable_row, height=320)

def generate_investment_thesis(ticker, analysis_data, thesis_type, llm_manager=None, show_prompt=False, return_response=False, previous_output=""):
    """Generate investment thesis based on analysis data"""
    print(f"[GEN-INV-THESIS]: Return Response: {return_response}")
    with st.spinner(f"Generating {thesis_type.lower()} thesis for {ticker}..."):
        try:
            # Extract key data points
            final_rec = analysis_data.get('final_recommendation', {})
            analyses = analysis_data.get('analyses', {})
            
            # Build enhanced thesis components
            thesis_components = extract_enhanced_thesis_components(ticker, analysis_data, analyses)
            
            # Generate thesis with unified LLM enhancement
            thesis, prompt_used = generate_unified_thesis(ticker, thesis_components, thesis_type, llm_manager, return_prompt=True, previous_output=previous_output)
            
            # Display prompt if requested
            if show_prompt and prompt_used:
                display_prompt_used(prompt_used)
            
            # Always display the generated thesis
            display_generated_thesis(ticker, thesis, thesis_type)
            
            # Return response if requested (for storage in blind test workflow)
            print(f"[GEN-INV-THESIS]: Return Response: {return_response}")
            # print(f"[GEN-INV-THESIS]: Thesis: {thesis}")
            if return_response:
                return thesis
            
        except Exception as e:
            st.error(f"Error generating thesis: {str(e)}")
            if return_response:
                return None

def extract_enhanced_thesis_components(ticker, analysis_data, analyses):
    """Extract enhanced thesis components with cross-method analysis"""
    
    # Get base components
    components = extract_thesis_components(ticker, analysis_data, analyses)
    
    # Add analyses to components for use in thesis generation
    components['analyses'] = analyses
    
    # Add financial metrics from analysis_data
    components['financial_metrics'] = analysis_data.get('financial_metrics', {})
    
    # Extract and calculate financial performance data
    components['financial_performance'] = extract_financial_performance_data(ticker, components['financial_metrics'])
    
    # Add industry analysis data
    if 'industry_analysis' in analyses:
        industry_data = analyses['industry_analysis']
        components['industry_analysis'] = {
            'industry_outlook': industry_data.get('industry_outlook', 'Neutral'),
            'competitive_position': industry_data.get('competitive_position', 'Average'),
            'market_catalysts': industry_data.get('market_catalysts', []),
            'porters_five_forces': industry_data.get('porters_five_forces', {}),
            'regulatory_risk': industry_data.get('regulatory_risk', 'Medium'),
            'esg_score': industry_data.get('esg_score', 5.0),
            'industry_insights': industry_data.get('industry_insights', {}),
            'competitive_analysis': industry_data.get('competitive_analysis', {})
        }
        
        # Extract industry-specific strengths and risks
        industry_insights = industry_data.get('industry_insights', {})
        components['strengths'].extend(industry_insights.get('growth_drivers', [])[:3])
        components['risks'].extend(industry_insights.get('headwinds', [])[:3])
        
        # Add competitive advantages from industry analysis
        comp_analysis = industry_data.get('competitive_analysis', {})
        components['strengths'].extend(comp_analysis.get('competitive_advantages', [])[:2])
        components['risks'].extend(comp_analysis.get('competitive_disadvantages', [])[:2])
    
    # Add cross-method valuation analysis
    components['cross_method_analysis'] = reconcile_valuation_methods(components['valuation_methods'])
    
    # Extract catalysts with timeframes
    components['key_catalysts'] = extract_catalysts_with_timeframes(analyses)
    
    # Generate investment narrative
    components['investment_narrative'] = generate_investment_narrative(analyses, components)
    
    return components

def extract_financial_performance_data(ticker, financial_metrics):
    """Extract and calculate financial performance metrics and growth rates"""
    
    performance_data = {
        'current_metrics': {},
        'growth_analysis': {},
        'profitability_trends': {},
        'financial_health': {}
    }
    
    # Current market metrics
    performance_data['current_metrics'] = {
        'current_price': financial_metrics.get('current_price', 0),
        'market_cap': financial_metrics.get('market_cap', 0),
        'pe_ratio': financial_metrics.get('pe_ratio', 0),
        'ps_ratio': financial_metrics.get('ps_ratio', 0),
        'pb_ratio': financial_metrics.get('pb_ratio', 0),
        'enterprise_value': financial_metrics.get('enterprise_value', 0)
    }
    
    # Growth metrics
    performance_data['growth_analysis'] = {
        'revenue_growth': financial_metrics.get('yearly_revenue_growth', 0),
        'earnings_growth': financial_metrics.get('earnings_growth', 0),
        'revenue_growth_quarterly': financial_metrics.get('revenue_growth', 0),
        'total_revenue': financial_metrics.get('total_revenue', 0)
    }
    
    # Profitability metrics
    performance_data['profitability_trends'] = {
        'roe': financial_metrics.get('roe', 0),
        'roa': financial_metrics.get('roa', 0),
        'gross_margin': financial_metrics.get('gross_margin', 0),
        'operating_margin': financial_metrics.get('operating_margin', 0),
        'net_margin': financial_metrics.get('net_margin', 0)
    }
    
    # Financial health metrics
    performance_data['financial_health'] = {
        'debt_to_equity': financial_metrics.get('debt_to_equity', 0),
        'current_ratio': financial_metrics.get('current_ratio', 0),
        'quick_ratio': financial_metrics.get('quick_ratio', 0),
        'cash_per_share': financial_metrics.get('cash_per_share', 0),
        'free_cash_flow': financial_metrics.get('free_cash_flow', 0)
    }
    
    # Get historical financial data for growth calculations
    try:
        # First try to use existing revenue trend data if available
        revenue_data_statements = financial_metrics.get('revenue_data_statements')
        
        if revenue_data_statements and isinstance(revenue_data_statements, dict):
            # Use existing financial statements data from Yahoo provider
            income_stmt = revenue_data_statements.get('annual_income_stmt')
            cashflow = revenue_data_statements.get('cashflow')
        else:
            # Fallback to direct yfinance call
            import yfinance as yf
            stock = yf.Ticker(ticker)
            income_stmt = stock.financials
            cashflow = stock.cashflow
        
        if not income_stmt.empty and len(income_stmt.columns) >= 2:
            # Calculate revenue growth from historical data
            latest_revenue = income_stmt.loc['Total Revenue', income_stmt.columns[0]] if 'Total Revenue' in income_stmt.index else 0
            previous_revenue = income_stmt.loc['Total Revenue', income_stmt.columns[1]] if 'Total Revenue' in income_stmt.index else 0
            
            if previous_revenue and previous_revenue != 0:
                historical_revenue_growth = ((latest_revenue - previous_revenue) / previous_revenue) * 100
                performance_data['growth_analysis']['historical_revenue_growth'] = historical_revenue_growth
            
            # Calculate net income growth
            latest_net_income = income_stmt.loc['Net Income', income_stmt.columns[0]] if 'Net Income' in income_stmt.index else 0
            previous_net_income = income_stmt.loc['Net Income', income_stmt.columns[1]] if 'Net Income' in income_stmt.index else 0
            
            if previous_net_income and previous_net_income != 0:
                net_income_growth = ((latest_net_income - previous_net_income) / previous_net_income) * 100
                performance_data['growth_analysis']['net_income_growth'] = net_income_growth
        
        if not cashflow.empty and len(cashflow.columns) >= 2:
            # Calculate cash flow growth
            latest_operating_cf = 0
            previous_operating_cf = 0
            
            if 'Operating Cash Flow' in cashflow.index:
                latest_operating_cf = cashflow.loc['Operating Cash Flow', cashflow.columns[0]]
                previous_operating_cf = cashflow.loc['Operating Cash Flow', cashflow.columns[1]] if len(cashflow.columns) > 1 else 0
            elif 'Cash Flowsfromusedin Operating Activities Direct' in cashflow.index:
                latest_operating_cf = cashflow.loc['Cash Flowsfromusedin Operating Activities Direct', cashflow.columns[0]]
                previous_operating_cf = cashflow.loc['Cash Flowsfromusedin Operating Activities Direct', cashflow.columns[1]] if len(cashflow.columns) > 1 else 0
            
            if previous_operating_cf and previous_operating_cf != 0:
                operating_cf_growth = ((latest_operating_cf - previous_operating_cf) / previous_operating_cf) * 100
                performance_data['growth_analysis']['operating_cf_growth'] = operating_cf_growth
    
    except Exception as e:
        # If yfinance data unavailable, use existing metrics
        pass
    
    return performance_data

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
    
    # Extract from Business Model (including segment revenue data)
    if 'business_model' in analyses:
        bm_data = analyses['business_model']
        components['strengths'].extend(bm_data.get('strengths', []))
        components['risks'].extend(bm_data.get('risks', []))
        
        # Add product portfolio and competitive differentiation data
        components['product_portfolio'] = bm_data.get('product_portfolio', {})
        components['competitive_differentiation'] = bm_data.get('competitive_differentiation', {})
        
        # Extract segment revenue data from business model analyzer
        components['segment_revenue_data'] = bm_data.get('segment_revenue_data', {})
    
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
            'news_count': news_data.get('news_count', 0),
            'recent_news': news_data.get('recent_news', [])  # Add recent_news with URLs
        }
    
    return components

def prepare_standardized_prompt_data(ticker, components, analyses, financial_metrics, target_price, current_price_str, dcf_calculation_details, startup_calculation_details):
    """Prepare standardized prompt data for all thesis types"""
    
    # Get cross-analysis data
    cross_analysis = components.get('cross_method_analysis', {})
    
    # Extract financial performance data
    financial_perf = components.get('financial_performance', {})
    growth_analysis = financial_perf.get('growth_analysis', {})
    
    # Calculate segment info
    segment_data = components.get('segment_revenue_data', {})
    segment_info = ""
    if segment_data and segment_data.get('primary_segments'):
        try:
            segments = segment_data['primary_segments']
            segment_breakdown = ", ".join([f"{seg['segment_name']}: {seg['revenue_percentage']:.1f}% ({seg['growth_trend']})" for seg in segments[:3]])
            segment_info = f"\n- Revenue segments: {segment_breakdown}"
            segment_info += f"\n- Largest segment: {segment_data.get('largest_segment', 'N/A')}"
            segment_info += f"\n- Fastest growing: {segment_data.get('fastest_growing_segment', 'N/A')}"
            segment_info += f"\n- Diversification: {segment_data.get('revenue_diversification', 'Medium')}"
        except (ValueError, TypeError, KeyError):
            segment_info = "\n- Segment data: Formatting error"
    
    # Standardized data dictionary
    return {
        'ticker': ticker,
        'company_type': components.get('company_type', 'Unknown'),
        'target_price': target_price,
        'current_price_str': current_price_str,
        'market_cap': financial_metrics.get('market_cap', 0),
        'enterprise_value': financial_metrics.get('enterprise_value', 0),
        'beta': financial_metrics.get('beta', 'N/A'),
        'pe_ratio': financial_metrics.get('pe_ratio', 'N/A'),
        'ps_ratio': financial_metrics.get('ps_ratio', 'N/A'),
        'pb_ratio': financial_metrics.get('pb_ratio', 'N/A'),
        'ev_ebitda_multiple': financial_metrics.get('ev_ebitda_multiple', 'N/A'),
        'gross_margin': financial_metrics.get('gross_margin', 0) * 100 if isinstance(financial_metrics.get('gross_margin', 0), (int, float)) else 0,
        'operating_margin': financial_metrics.get('operating_margin', 0) * 100 if isinstance(financial_metrics.get('operating_margin', 0), (int, float)) else 0,
        'net_margin': financial_metrics.get('net_margin', 0) * 100 if isinstance(financial_metrics.get('net_margin', 0), (int, float)) else 0,
        'roe': financial_metrics.get('roe', 0) * 100 if isinstance(financial_metrics.get('roe', 0), (int, float)) else 0,
        'roa': financial_metrics.get('roa', 0) * 100 if isinstance(financial_metrics.get('roa', 0), (int, float)) else 0,
        'revenue_growth': financial_metrics.get('revenue_growth', 0) * 100 if isinstance(financial_metrics.get('revenue_growth', 0), (int, float)) else 0,
        'earnings_growth': financial_metrics.get('earnings_growth', 0) * 100 if isinstance(financial_metrics.get('earnings_growth', 0), (int, float)) else 0,
        'debt_to_equity': financial_metrics.get('debt_to_equity', 'N/A'),
        'current_ratio': financial_metrics.get('current_ratio', 'N/A'),
        'quick_ratio': financial_metrics.get('quick_ratio', 'N/A'),
        'free_cash_flow': financial_metrics.get('free_cash_flow', 0),
        'cash_per_share': financial_metrics.get('cash_per_share', 'N/A'),
        'book_value_per_share': financial_metrics.get('book_value_per_share', 'N/A'),
        'dividend_yield': financial_metrics.get('dividend_yield', 'N/A'),
        'payout_ratio': financial_metrics.get('payout_ratio', 'N/A'),
        'total_revenue': financial_metrics.get('total_revenue', 0),
        'latest_net_income': financial_metrics.get('latest_net_income', 0),
        'latest_operating_income': financial_metrics.get('latest_operating_income', 0),
        'latest_gross_profit': financial_metrics.get('latest_gross_profit', 0),
        'latest_operating_cf': financial_metrics.get('latest_operating_cf', 0),
        'latest_capital_expenditures': financial_metrics.get('latest_capital_expenditures', 0),
        'trailing_eps': financial_metrics.get('trailing_eps', 'N/A'),
        'forward_eps': financial_metrics.get('forward_eps', 'N/A'),
        'shares_outstanding': financial_metrics.get('shares_outstanding') or 0,
        'float_shares': financial_metrics.get('float_shares') or 0,
        'industry': financial_metrics.get('industry', 'N/A'),
        'sector': financial_metrics.get('sector', 'N/A'),
        'segment_info': segment_info,
        'net_income_growth': growth_analysis.get('net_income_growth', 0),
        'operating_cf_growth': growth_analysis.get('operating_cf_growth', 0),
        'dcf_calculation_details': dcf_calculation_details,
        'startup_calculation_details': startup_calculation_details,
        'average_target': cross_analysis.get('average_target', 0),
        'consensus_strength': cross_analysis.get('consensus_strength', 'Medium'),
        'method_agreement': cross_analysis.get('method_agreement', 'Mixed'),
        'strengths': ', '.join([str(s) for s in components['strengths'][:5]]),
        'risks': ', '.join([str(r) for r in components['risks'][:5]]),
        'key_developments': ', '.join([str(d) for d in components['market_sentiment'].get('key_developments', [])]),
        'sentiment_rating': components['market_sentiment'].get('sentiment_rating', 'Neutral'),
        'news_count': components['market_sentiment'].get('news_count', 0),
        'news_sources_with_urls': ', '.join([f"{article.get('source', 'Unknown')}: {article.get('title', 'No title')[:40]}... ({article.get('url', 'No URL')}) - Facts: {article.get('enhanced_facts', {}).get('lead_fact', 'No structured facts')}" for article in components['market_sentiment'].get('recent_news', [])]),
        'industry_outlook': components.get('industry_analysis', {}).get('industry_outlook', 'Neutral'),
        'competitive_position': components.get('industry_analysis', {}).get('competitive_position', 'Average'),
        'regulatory_risk': components.get('industry_analysis', {}).get('regulatory_risk', 'Medium'),
        'esg_score': components.get('industry_analysis', {}).get('esg_score', 5.0),
        'business_segments': ', '.join([seg.get('segment_name', 'N/A') if isinstance(seg, dict) else str(seg) for seg in components.get('segment_revenue_data', {}).get('primary_segments', [])]),
        'revenue_breakdown': ', '.join([f"{seg.get('segment_name', 'N/A')} ({seg.get('revenue_percentage', 0):.1f}%)" if isinstance(seg, dict) else str(seg) for seg in components.get('segment_revenue_data', {}).get('primary_segments', [])]),
        'data_source': components.get('segment_revenue_data', {}).get('data_source', 'N/A'),
        'revenue_diversification': components.get('segment_revenue_data', {}).get('revenue_diversification', 'N/A'),
        'TOTAL_REVENUE': f"${financial_metrics.get('total_revenue', 0):,.0f}" if financial_metrics.get('total_revenue') else "$0",
        'enhanced_news_facts': json.dumps([{
            'title': article.get('title', ''),
            'url': article.get('url', ''),
            'lead_fact': article.get('enhanced_facts', {}).get('lead_fact', ''),
            'quantitative_evidence': article.get('enhanced_facts', {}).get('quantitative_evidence', ''),
            'business_mechanism': article.get('enhanced_facts', {}).get('business_mechanism', ''),
            'verbatim_quote': article.get('enhanced_facts', {}).get('verbatim_quote', '')
        } for article in components['market_sentiment'].get('recent_news', []) if article.get('enhanced_facts')], indent=2),
        'business_summary': financial_metrics.get('business_summary', 'No business summary available'),
    }

def generate_segment_revenue_table(segment_data, total_revenue):
    """Generate pre-calculated segment revenue table for prompt"""
    if not segment_data or not segment_data.get('primary_segments'):
        return "No segment data available"
    
    segments = segment_data['primary_segments']
    table_rows = []
    
    for seg in segments:
        # Ensure seg is a dictionary, not a string
        if isinstance(seg, dict):
            segment_name = seg.get('segment_name', 'Unknown')
            percentage = seg.get('revenue_percentage', 0)
            revenue_amount = (percentage / 100) * total_revenue if total_revenue else 0
            revenue_millions = revenue_amount / 1_000_000  # Convert to millions
            growth_trend = seg.get('growth_trend', 'Unknown')
            
            table_rows.append(f"| {segment_name} | ${revenue_millions:,.0f} | {percentage:.1f}% | {growth_trend} | Core | Medium |")
        else:
            # Handle case where seg is not a dictionary
            table_rows.append(f"| {str(seg)} | $0 | 0.0% | Unknown | Core | Medium |")
    
    return "\n".join(table_rows)

def generate_unified_thesis(ticker, components, thesis_type, llm_manager=None, return_prompt=False, previous_output=""):
    """Generate unified investment thesis with scenario-specific focus using external prompt templates"""
    
    try:
        # Use provided LLM manager or create new one
        if llm_manager is None:
            llm_manager = LLMManager()
        
        # Initialize prompt loader
        prompt_loader = ThesisPromptLoader()
        
        # Extract analyses from components (they should be available there)
        analyses = components.get('analyses', {})
        
        # Extract current price from analysis data
        current_price = None
        if 'financial_metrics' in components:
            current_price = components['financial_metrics'].get('current_price')
        
        if not current_price:
            try:
                import yfinance as yf
                stock = yf.Ticker(ticker)
                current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
            except:
                current_price = 0
        
        current_price_str = f"${current_price:.2f}" if current_price else "Unable to obtain current price"
        
        # Get recommendation and cross-analysis data
        final_rec = components['final_recommendation']
        cross_analysis = components['cross_method_analysis']
        target_price = final_rec.get('target_price', 0)
        
        # Extract financial performance data
        financial_perf = components.get('financial_performance', {})
        current_metrics = financial_perf.get('current_metrics', {})
        growth_analysis = financial_perf.get('growth_analysis', {})
        profitability = financial_perf.get('profitability_trends', {})
        financial_health = financial_perf.get('financial_health', {})
        print('[GEN-INV-THESIS]: retrieved basic metrics')
        # Extract comprehensive financial metrics from analysis data
        financial_metrics = components.get('financial_metrics', {})
        
        # Extract actual financial statement values from revenue_data_statements
        revenue_data_statements = financial_metrics.get('revenue_data_statements', {})
        
        # Get latest financial values from the serialized data structure
        latest_net_income = 0
        latest_gross_profit = 0
        latest_operating_income = 0
        latest_operating_cf = 0
        latest_capital_expenditures = 0
        latest_total_revenue = 0
        
        # Extract from annual income statement (most recent year) for margin calculations
        annual_income = revenue_data_statements.get('annual_income_stmt', {})
        if annual_income:
            latest_year = list(annual_income.keys())[0]  # Most recent year
            annual_data = annual_income[latest_year]
            latest_total_revenue = annual_data.get('Total Revenue', 0) or 0
            latest_gross_profit = annual_data.get('Gross Profit', 0) or 0
            latest_net_income = annual_data.get('Net Income', 0) or 0
            latest_operating_income = annual_data.get('Operating Income', 0) or 0
        
        # Calculate margins from annual data
        calculated_gross_margin = (latest_gross_profit / latest_total_revenue) if latest_total_revenue > 0 else 0
        calculated_operating_margin = (latest_operating_income / latest_total_revenue) if latest_total_revenue > 0 else 0
        calculated_net_margin = (latest_net_income / latest_total_revenue) if latest_total_revenue > 0 else 0
        
        # Extract from quarterly income statement (most recent quarter) as fallback
        quarterly_income = revenue_data_statements.get('quarterly_income_stmt', {})
        if quarterly_income and latest_total_revenue == 0:
            latest_quarter = list(quarterly_income.keys())[0]  # Most recent quarter
            quarter_data = quarterly_income[latest_quarter]
            latest_net_income = quarter_data.get('Net Income', 0) or 0
            latest_gross_profit = quarter_data.get('Gross Profit', 0) or 0
            latest_operating_income = quarter_data.get('Operating Income', 0) or 0
        
        # Extract from cash flow data (most recent period)
        cashflow_data = revenue_data_statements.get('cashflow', {})
        if cashflow_data:
            latest_cf_date = list(cashflow_data.keys())[0]  # Most recent date
            cf_data = cashflow_data[latest_cf_date]
            latest_operating_cf = (cf_data.get('Operating Cash Flow') or 
                                 cf_data.get('Cash Flowsfromusedin Operating Activities Direct') or 
                                 cf_data.get('Operating Cash Flow') or 0)
            latest_capital_expenditures = abs(cf_data.get('Capital Expenditures', 0) or 0)  # Make positive for display
        
        # Combine all financial data for comprehensive prompt
        all_financial_data = {
            'market_cap': financial_metrics.get('market_cap', current_metrics.get('market_cap', 0)),
            'pe_ratio': financial_metrics.get('pe_ratio', current_metrics.get('pe_ratio', 'N/A')),
            'ps_ratio': financial_metrics.get('ps_ratio', current_metrics.get('ps_ratio', 'N/A')),
            'pb_ratio': financial_metrics.get('pb_ratio', current_metrics.get('pb_ratio', 'N/A')),
            'enterprise_value': financial_metrics.get('enterprise_value', current_metrics.get('enterprise_value', 0)),
            'ev_ebitda_multiple': financial_metrics.get('ev_ebitda_multiple', 'N/A'),
            'roe': financial_metrics.get('roe', profitability.get('roe', 0)),
            'roa': financial_metrics.get('roa', profitability.get('roa', 0)),
            'debt_to_equity': financial_metrics.get('debt_to_equity', financial_health.get('debt_to_equity', 0)),
            'current_ratio': financial_metrics.get('current_ratio', financial_health.get('current_ratio', 0)),
            'quick_ratio': financial_metrics.get('quick_ratio', financial_health.get('quick_ratio', 0)),
            'gross_margin': calculated_gross_margin or financial_metrics.get('gross_margin', profitability.get('gross_margin', 0)),
            'operating_margin': calculated_operating_margin or financial_metrics.get('operating_margin', profitability.get('operating_margin', 0)),
            'net_margin': calculated_net_margin or financial_metrics.get('net_margin', profitability.get('net_margin', 0)),
            'revenue_growth': financial_metrics.get('revenue_growth', growth_analysis.get('revenue_growth', 0)),
            'earnings_growth': financial_metrics.get('earnings_growth', growth_analysis.get('earnings_growth', 0)),
            'free_cash_flow': financial_metrics.get('free_cash_flow', financial_health.get('free_cash_flow', 0)),
            'cash_per_share': financial_metrics.get('cash_per_share', financial_health.get('cash_per_share', 0)),
            'total_revenue': financial_metrics.get('total_revenue', growth_analysis.get('total_revenue', 0)),
            'latest_net_income': latest_net_income,
            'latest_operating_income': latest_operating_income,
            'latest_gross_profit': latest_gross_profit,
            'latest_operating_cf': latest_operating_cf,
            'latest_capital_expenditures': latest_capital_expenditures,
            'trailing_eps': financial_metrics.get('trailing_eps', 'N/A'),
            'forward_eps': financial_metrics.get('forward_eps', 'N/A'),
            'shares_outstanding': financial_metrics.get('shares_outstanding') or 0,
            'float_shares': financial_metrics.get('float_shares') or 0,
            'industry': financial_metrics.get('industry', 'N/A'),
            'sector': financial_metrics.get('sector', 'N/A'),
            'beta': financial_metrics.get('beta', 'N/A'),
            'dividend_yield': financial_metrics.get('dividend_yield', 'N/A'),
            'payout_ratio': financial_metrics.get('payout_ratio', 'N/A'),
            'book_value_per_share': financial_metrics.get('book_value_per_share', 'N/A'),
            'price_to_sales_ttm': financial_metrics.get('price_to_sales_ttm', 'N/A'),
            'price_to_book_mrq': financial_metrics.get('price_to_book_mrq', 'N/A'),
            'return_on_assets': financial_metrics.get('return_on_assets', 'N/A'),
            'return_on_equity': financial_metrics.get('return_on_equity', 'N/A'),
            'business_summary': financial_metrics.get('business_summary', 'No business summary available')
        }
        print('[GEN-INV-THESIS]: Combined all financial data')
        # Convert display name back to prompt type dynamically
        prompt_type = thesis_type.lower().replace(' ', '_')
        
        # Extract segment revenue data and format for prompt
        segment_data = components.get('segment_revenue_data', {})
        segment_info = ""
        if segment_data and segment_data.get('primary_segments'):
            try:
                segments = segment_data['primary_segments']
                # Ensure all segments are properly formatted as strings
                segment_list = []
                for seg in segments[:3]:
                    if isinstance(seg, dict) and 'segment_name' in seg:
                        segment_list.append(f"{seg['segment_name']}: {seg.get('revenue_percentage', 0):.1f}% ({seg.get('growth_trend', 'Unknown')})")
                    else:
                        segment_list.append(str(seg))
                segment_breakdown = ", ".join(segment_list)
                segment_info = f"\n- Revenue segments: {segment_breakdown}"
                segment_info += f"\n- Largest segment: {segment_data.get('largest_segment', 'N/A')}"
                segment_info += f"\n- Fastest growing: {segment_data.get('fastest_growing_segment', 'N/A')}"
                segment_info += f"\n- Diversification: {segment_data.get('revenue_diversification', 'Medium')}"
                
                # Add operating income data if available
                if segment_data.get('total_operating_income'):
                    segment_info += f"\n- Total operating income: ${segment_data['total_operating_income']:,.0f}"
                    # Calculate operating margin if both revenue and operating income available
                    total_revenue = segment_data.get('total_revenue', 0)
                    if total_revenue > 0:
                        operating_margin = (segment_data['total_operating_income'] / total_revenue) * 100
                        segment_info += f"\n- Operating margin: {operating_margin:.1f}%"
            except (ValueError, TypeError, KeyError):
                segment_info = "\n- Segment data: Formatting error"
        
        # Extract DCF calculation details if available
        dcf_calculation_details = ""
        if 'dcf' in analyses:
            dcf_data = analyses['dcf']
            dcf_calcs = dcf_data.get('dcf_calculations', {})
            params = dcf_data.get('parameters_used', {})
            
            if dcf_calcs:
                try:
                    dcf_calculation_details = f"""
        
        **DCF CALCULATION VALIDATION:**
        - WACC (Weighted Average Cost of Capital): {dcf_calcs.get('wacc', 'N/A'):.2%} 
        - FCF CAGR (Free Cash Flow Growth): {dcf_calcs.get('fcf_cagr', 'N/A'):.2%}
        - EBITDA CAGR: {dcf_calcs.get('ebitda_cagr', 'N/A'):.2%}
        - Terminal Growth Rate: {params.get('terminal_growth', 'N/A')}
        - EV/EBITDA Multiple Used: {dcf_calcs.get('ev_ebitda_multiple', 'N/A'):.1f}x
        - Terminal Value (Perpetual Growth): ${dcf_calcs.get('terminal_value_pg', 0):,.0f}
        - Terminal Value (EBITDA Multiple): ${dcf_calcs.get('terminal_value_ebitda_multiple', 0):,.0f}
        - Present Value of FCF: ${dcf_calcs.get('pv_fcf', 0):,.0f}
        - Present Value of Terminal Value: ${dcf_calcs.get('pv_terminal_value', 0):,.0f}
        - Enterprise Value: ${dcf_calcs.get('enterprise_value', 0):,.0f}
        - Equity Value: ${dcf_calcs.get('equity_value', 0):,.0f}
        - Terminal Value Dominance: {dcf_calcs.get('terminal_ratio', 0):.1%}
        - DCF Confidence Level: {dcf_calcs.get('confidence', 'N/A')}
        - Sector/Industry Adjustments: {params.get('sector', 'N/A')} / {params.get('industry', 'N/A')}
        - Quality Grade Adjustment: {params.get('quality_adjustment', 'N/A')}
        - Max CAGR Threshold: {params.get('max_cagr', 'N/A')}
        """
                except (ValueError, TypeError, KeyError):
                    dcf_calculation_details = "\n\n**DCF CALCULATION VALIDATION:** Data formatting error"
        
        # Extract startup analysis calculation details if available
        startup_calculation_details = ""
        if 'startup' in analyses:
            startup_data = analyses['startup']
            revenue_multiple = startup_data.get('revenue_multiple_breakdown', {})
            
            if revenue_multiple:
                try:
                    startup_calculation_details = f"""
        
        **STARTUP VALUATION CALCULATION VALIDATION:**
        - Current Revenue: ${startup_data.get('current_revenue', 0):,.0f}
        - Median Revenue Growth Rate: {startup_data.get('median_growth', 'N/A')}
        - Revenue Volatility: {startup_data.get('revenue_volatility', 'N/A')}
        - Cash Runway: {startup_data.get('cash_runway_years', 0):.1f} years
        - Quarterly Burn Rate: ${startup_data.get('quarterly_burn_rate', 0):,.0f}
        - Growth Quality Assessment: {startup_data.get('growth_quality', 'N/A')}
        - Company Stage: {startup_data.get('stage', 'N/A')}
        - Base Revenue Multiple: {revenue_multiple.get('base_multiple', 'N/A'):.1f}x
        - Risk Adjustment Factor: {revenue_multiple.get('risk_adjustment', 'N/A'):.2f}
        - Stage Adjustment Factor: {revenue_multiple.get('stage_adjustment', 'N/A'):.2f}
        - Final Revenue Multiple: {revenue_multiple.get('final_multiple', 'N/A'):.1f}x
        - Risk Score (0-100): {startup_data.get('risk_score', 'N/A')}/100
        - Projected Revenue (1Y): ${startup_data.get('projected_revenue_1yr', 0):,.0f}
        - Projected Revenue (2Y): ${startup_data.get('projected_revenue_2yr', 0):,.0f}
        - Implied Enterprise Value: ${startup_data.get('implied_value_estimate', 0):,.0f}
        - Investment Risk Level: {startup_data.get('confidence_level', 'N/A')}
        """
                except (ValueError, TypeError, KeyError):
                    startup_calculation_details = "\n\n**STARTUP VALUATION CALCULATION VALIDATION:** Data formatting error"
        
        # Generate segment revenue table for product portfolio catalyst prompt
        segment_revenue_table = generate_segment_revenue_table(
            components.get('segment_revenue_data', {}), 
            all_financial_data.get('total_revenue', 0)
        )
        
        # Prepare standardized prompt data
        prompt_data = prepare_standardized_prompt_data(
            ticker, components, analyses, all_financial_data, 
            target_price, current_price_str, dcf_calculation_details, startup_calculation_details
        )
        
        # Add segment revenue data for product portfolio catalyst prompt
        prompt_data['SEGMENT_REVENUE_DATA'] = segment_revenue_table
        
        # Add technical analysis details
        technical_analysis_details = ""
        if 'technical' in analyses:
            tech_data = analyses['technical']
            technical_analysis_details = f"""
        
        **TECHNICAL ANALYSIS DETAILS:**
        - Current Trend: {tech_data.get('trend', 'N/A')}
        - RSI (14-day): {tech_data.get('rsi_14', 'N/A')}
        - Moving Averages: MA20: {tech_data.get('ma_20', 'N/A')}, MA50: {tech_data.get('ma_50', 'N/A')}, MA200: {tech_data.get('ma_200', 'N/A')}
        - MACD Signal: Line: {tech_data.get('macd_line', 'N/A')}, Signal: {tech_data.get('macd_signal', 'N/A')}
        - Volume Trend: {tech_data.get('volume_trend', 'N/A')}
        - Support/Resistance: Support: {tech_data.get('support_level', 'N/A')}, Resistance: {tech_data.get('resistance_level', 'N/A')}
        - Technical Recommendation: {tech_data.get('recommendation', 'N/A')}
        - Technical Target Price: ${tech_data.get('predicted_price', 0) or 0:.2f}
        - Momentum Indicators: {tech_data.get('momentum_analysis', 'N/A')}
        """
        
        # Add comparable analysis details
        comparable_analysis_details = ""
        if 'comparable' in analyses:
            comp_data = analyses['comparable']
            peer_tickers = comp_data.get('peer_tickers', [])
            target_multiples = comp_data.get('target_multiples', {})
            comparable_analysis_details = f"""
        
        **COMPARABLE COMPANY ANALYSIS DETAILS:**
        - Peer Companies: {', '.join(peer_tickers[:5]) if peer_tickers else 'N/A'}
        - Target P/E Multiple: {target_multiples.get('pe', 'N/A')}x
        - Target P/S Multiple: {target_multiples.get('ps', 'N/A')}x
        - Target P/B Multiple: {target_multiples.get('pb', 'N/A')}x
        - Target EV/EBITDA Multiple: {target_multiples.get('ev_ebitda', 'N/A')}x
        - Comparable Recommendation: {comp_data.get('recommendation', 'N/A')}
        - Comparable Target Price: ${comp_data.get('predicted_price', 0) or 0:.2f}
        - Peer Valuation Premium/Discount: {comp_data.get('valuation_premium', 'N/A')}
        - Industry Multiple Range: {comp_data.get('industry_multiple_range', 'N/A')}
        """
        
        # Add analyst consensus details
        analyst_consensus_details = ""
        if 'analyst_consensus' in analyses:
            analyst_data = analyses['analyst_consensus']
            analyst_consensus_details = f"""
        
        **ANALYST CONSENSUS DETAILS:**
        - Consensus Target Price: ${analyst_data.get('predicted_price', 0) or 0:.2f}
        - Target Price High: ${analyst_data.get('target_high', 0) or 0:.2f}
        - Target Price Low: ${analyst_data.get('target_low', 0) or 0:.2f}
        - Number of Analysts: {analyst_data.get('num_analysts', 0)}
        - Consensus Recommendation: {analyst_data.get('recommendation', 'N/A')}
        - Buy Ratings: {analyst_data.get('buy_ratings', 0)}
        - Hold Ratings: {analyst_data.get('hold_ratings', 0)}
        - Sell Ratings: {analyst_data.get('sell_ratings', 0)}
        - Recent Estimate Revisions: {analyst_data.get('estimate_revisions', 'N/A')}
        - Earnings Surprise History: {analyst_data.get('earnings_surprises', 'N/A')}
        """
        
        # Add the analysis details to prompt data
        prompt_data['technical_analysis_details'] = technical_analysis_details
        prompt_data['comparable_analysis_details'] = comparable_analysis_details
        prompt_data['analyst_consensus_details'] = analyst_consensus_details
        prompt_data['previous_output'] = previous_output or ""
        
        # Load and format the appropriate prompt template
        prompt = prompt_loader.format_prompt(prompt_type, **prompt_data)
        
        # Print the formatted prompt to terminal for debugging
        print("\n" + "="*80)
        print(f"FORMATTED PROMPT FOR {ticker} - {thesis_type}")
        print("="*80)
        print(prompt)
        print("="*80 + "\n")
        
        llm_response = llm_manager.generate_response(prompt)
        
        # Fallback to appropriate template if LLM fails
        if not llm_response or len(llm_response.strip()) < 100:
            if thesis_type == "Bull Case":
                fallback_response = generate_bull_case(ticker, components)
            elif thesis_type == "Bear Case":
                fallback_response = generate_bear_case(ticker, components)
            else:
                fallback_response = generate_balanced_thesis(ticker, components)
            
            if return_prompt:
                return fallback_response, prompt
            return fallback_response
        
        if return_prompt:
            return llm_response, prompt
        return llm_response
        
    except Exception as e:
        st.warning(f"LLM enhancement failed, using template: {str(e)}")
        if thesis_type == "Bull Case":
            fallback_response = generate_bull_case(ticker, components)
        elif thesis_type == "Bear Case":
            fallback_response = generate_bear_case(ticker, components)
        else:
            fallback_response = generate_balanced_thesis(ticker, components)
        
        if return_prompt:
            return fallback_response, None
        return fallback_response

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

def display_prompt_used(prompt):
    """Display the prompt that was passed to the LLM"""
    
    st.subheader("🔍 LLM Prompt Used")
    
    with st.expander("View Full Prompt Sent to LLM", expanded=False):
        st.markdown(
            f"""
            <div style="
                background-color: #f8f9fa;
                padding: 15px;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                margin: 10px 0;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                max-height: 500px;
                max-width: 100%;
                overflow-y: auto;
                overflow-x: hidden;
                white-space: pre-wrap;
                word-wrap: break-word;
                overflow-wrap: break-word;
                word-break: break-word;
                box-sizing: border-box;
            ">
                {prompt}
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Show prompt statistics
        word_count = len(prompt.split())
        char_count = len(prompt)
        st.caption(f"📊 Prompt Statistics: {word_count:,} words, {char_count:,} characters")

@st.fragment
def save_thesis_fragment(ticker, thesis, thesis_type):
    """Fragment for save thesis button to prevent full page refresh"""
    save_key = f"save_{ticker}_{thesis_type.replace(' ', '_')}"
    saved_key = f"saved_{save_key}"
    
    # Show different button state if already saved
    if st.session_state.get(saved_key, False):
        st.success("✅ Thesis Saved")
    else:
        if st.button("💾 Save Thesis", key=save_key):
            success = save_thesis_to_database(ticker, thesis, thesis_type)
            if success:
                st.session_state[saved_key] = True
                st.rerun(scope="fragment")

def display_generated_thesis(ticker, thesis, thesis_type):
    """Display the generated investment thesis"""
    
    print(f"🔍 DEBUG: display_generated_thesis called for {ticker} - {thesis_type}")
    
    # Store thesis in session state for button actions
    thesis_key = f"thesis_{ticker}_{thesis_type.replace(' ', '_')}"
    st.session_state[thesis_key] = thesis
    print(f"🔍 DEBUG: Stored thesis in session state with key: {thesis_key}")
    
    st.subheader(f"📝 Generated {thesis_type} for {ticker}")
    
    # Display thesis using Streamlit's native markdown
    st.markdown(thesis)
    
    # Add action buttons
    col1, col2, col3 = st.columns(3)
    
    print(f"🔍 DEBUG: About to create save button for {ticker}")
    
    with col1:
        save_thesis_fragment(ticker, thesis, thesis_type)
    
    with col2:
        if st.button("📄 Export PDF"):
            st.info("PDF export functionality coming soon!")
    
    with col3:
        history_key = f"history_{ticker}_{thesis_type.replace(' ', '_')}"
        if st.button("📊 View History", key=history_key):
            show_thesis_history(ticker)

def save_thesis_to_database(ticker, thesis, thesis_type):
    """Save generated thesis to database"""
    print(f"🔍 DEBUG: save_thesis_to_database called with ticker={ticker}, type={thesis_type}")
    
    try:
        print("🔍 DEBUG: Importing ThesisStorageService...")
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from src.share_insights_v1.services.storage.thesis_storage_service import ThesisStorageService
        
        # Get LLM provider info from session state
        llm_provider = st.session_state.get('thesis_llm_provider')
        llm_model = st.session_state.get('thesis_llm_model')
        
        print(f"🔍 DEBUG: LLM Provider: {llm_provider}, Model: {llm_model}")
        
        # Convert thesis type to database format
        db_thesis_type = thesis_type.lower().replace(' ', '_')
        print(f"🔍 DEBUG: DB thesis type: {db_thesis_type}")
        
        # Get batch_analysis_id - try multiple sources in order of preference
        batch_analysis_id = None
        
        # Debug: Show what's available in session state
        print(f"🔍 DEBUG: Session state keys: {list(st.session_state.keys())}")
        if 'batch_results' in st.session_state:
            print(f"🔍 DEBUG: Batch results tickers: {list(st.session_state.batch_results.keys())}")
            if ticker in st.session_state.batch_results:
                batch_data = st.session_state.batch_results[ticker]
                print(f"🔍 DEBUG: {ticker} data keys: {list(batch_data.keys())}")
        
        # 1. First try to get from the specific ticker's batch results
        if 'batch_results' in st.session_state and ticker in st.session_state.batch_results:
            batch_data = st.session_state.batch_results[ticker]
            batch_analysis_id = batch_data.get('batch_analysis_id')
            print(f"🔍 DEBUG: Found batch_analysis_id from batch_results[{ticker}]: {batch_analysis_id}")
        
        # 2. If not found, try from single stock analysis data
        if not batch_analysis_id and 'thesis_analysis_data' in st.session_state:
            thesis_data = st.session_state.thesis_analysis_data
            batch_analysis_id = thesis_data.get('batch_analysis_id')
            print(f"🔍 DEBUG: Found batch_analysis_id from thesis_analysis_data: {batch_analysis_id}")
        
        # 3. If still not found, check if the ticker matches the current analysis ticker
        if not batch_analysis_id and 'thesis_ticker' in st.session_state:
            current_ticker = st.session_state.get('thesis_ticker')
            if current_ticker == ticker and 'thesis_analysis_data' in st.session_state:
                thesis_data = st.session_state.thesis_analysis_data
                batch_analysis_id = thesis_data.get('batch_analysis_id')
                print(f"🔍 DEBUG: Found batch_analysis_id from current analysis ticker match: {batch_analysis_id}")
        
        print(f"🔍 DEBUG: Using batch_analysis_id directly: {batch_analysis_id}")
        
        # If no batch_analysis_id found, warn but still save thesis without linking
        if not batch_analysis_id:
            print(f"🔍 DEBUG: No batch_analysis_id found for {ticker} - thesis will be saved without analysis linking")
            st.warning(f"⚠️ No analysis record found for {ticker}. Thesis will be saved but not linked to analysis data.")
        
        print("🔍 DEBUG: Creating storage service...")
        storage_service = ThesisStorageService()
        
        print("🔍 DEBUG: Calling store_thesis...")
        thesis_id = storage_service.store_thesis(
            ticker=ticker,
            thesis_type=db_thesis_type,
            content=thesis,
            llm_provider=llm_provider,
            llm_model=llm_model,
            prompt_template=f"{db_thesis_type}_prompt.txt",
            previous_thesis_id=None,
            batch_analysis_id=batch_analysis_id  # Use UUID directly
        )
        
        print(f"🔍 DEBUG: Returned thesis_id: {thesis_id}")
        
        if thesis_id:
            if batch_analysis_id:
                st.success(f"✅ Thesis saved to database (ID: {thesis_id}) and linked to analysis batch {batch_analysis_id}")
            else:
                st.success(f"✅ Thesis saved to database (ID: {thesis_id}) - no analysis link available")
            return True
        else:
            st.error("❌ Failed to save thesis to database")
            return False
            
    except Exception as e:
        print(f"🔍 DEBUG: Exception occurred: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        st.error(f"❌ Database save error: {str(e)}")
        return False

def show_thesis_history(ticker):
    """Show thesis history for a ticker"""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from src.share_insights_v1.services.storage.thesis_storage_service import ThesisStorageService
        
        storage_service = ThesisStorageService()
        history = storage_service.get_thesis_history(ticker, limit=5)
        
        if history:
            st.subheader(f"📈 Thesis History for {ticker}")
            for i, thesis in enumerate(history):
                with st.expander(f"{thesis['thesis_type'].replace('_', ' ').title()} - {thesis['created_at'].strftime('%Y-%m-%d %H:%M')}"):
                    st.write(f"**LLM:** {thesis['llm_provider']} - {thesis['llm_model']}")
                    st.write(thesis['content'][:500] + "..." if len(thesis['content']) > 500 else thesis['content'])
        else:
            st.info(f"No thesis history found for {ticker}")
            
    except Exception as e:
        st.error(f"Error loading thesis history: {str(e)}")

def main():
    """Main function for thesis generation page"""
    show_thesis_generation()

if __name__ == "__main__":
    main()

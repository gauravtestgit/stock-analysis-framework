import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import yfinance as yf

def show_historical_analysis():
    """Show historical analysis page"""
    
    st.title("📈 Historical Analysis")
    st.markdown("*Track analysis evolution and performance over time*")
    
    # Stock input
    ticker = st.text_input("Enter Stock Ticker:", value="AAPL").upper()
    
    if not ticker:
        st.info("Enter a stock ticker to view historical analysis")
        return
    
    # Load historical data
    try:
        timeline_data = get_timeline_data(ticker)
        method_data = get_method_data(ticker)
        thesis_data = get_thesis_data(ticker)
        
        if not timeline_data:
            st.warning(f"No historical analysis data found for {ticker}")
            return
        
        # Display sections
        show_recommendation_timeline(ticker, timeline_data)
        show_method_performance(ticker, method_data)
        show_thesis_evolution(ticker, thesis_data)
        
    except Exception as e:
        st.error(f"Error loading historical data: {str(e)}")

def get_timeline_data(ticker: str):
    """Get recommendation timeline data"""
    try:
        response = requests.get(f"http://localhost:8000/api/history/{ticker}/timeline")
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_method_data(ticker: str):
    """Get method performance data"""
    try:
        response = requests.get(f"http://localhost:8000/api/history/{ticker}/methods")
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def get_thesis_data(ticker: str):
    """Get thesis evolution data"""
    try:
        response = requests.get(f"http://localhost:8000/api/history/{ticker}/theses")
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def show_recommendation_timeline(ticker: str, timeline_data):
    """Show recommendation timeline chart"""
    
    st.subheader("🎯 Recommendation Timeline")
    
    if not timeline_data:
        st.info("No historical analysis data found in database. Run some analyses first to see timeline data.")
        
        # Show stock price chart as fallback
        try:
            stock_data = yf.download(ticker, period="6m")
            if not stock_data.empty:
                stock_data = stock_data.reset_index()
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=stock_data['Date'],
                    y=stock_data['Close'],
                    mode='lines',
                    name=f'{ticker} Stock Price',
                    line=dict(color='blue', width=2)
                ))
                fig.update_layout(
                    title=f"{ticker} - Stock Price (6 months)",
                    xaxis_title="Date",
                    yaxis_title="Price ($)",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Could not load stock price data: {e}")
        return
    
    # Convert to DataFrame
    df_original = pd.DataFrame(timeline_data)
    df_original['date'] = pd.to_datetime(df_original['date'])
    df_original = df_original.sort_values('date')  # Sort chronologically
    
    # Analysis type filter and chart in fragment
    @st.fragment
    def filtered_chart():
        if 'analysis_type' in df_original.columns:
            analysis_types = ['All'] + sorted(df_original['analysis_type'].unique().tolist())
            selected_type = st.selectbox(
                "Filter by Analysis Type:",
                analysis_types,
                index=1 if 'final_recommendation' in analysis_types else 0,
                key="analysis_type_filter"
            )
        else:
            selected_type = 'All'
        
        # Apply filter
        df = df_original.copy()
        if selected_type != 'All' and 'analysis_type' in df.columns:
            df = df[df['analysis_type'] == selected_type]
        
        # Filter out zero target prices
        df = df[df['target_price'] > 0]
        
        # Show info
        st.info(f"💡 **Chart Guide**: Showing {selected_type if selected_type != 'All' else 'all analysis types'} - {len(df)} records. Colored dots represent target prices. Hover over dots to see exact values.")
        
        # Create chart with secondary y-axis
        fig = go.Figure()
        
        # Get stock price data aligned with timeline dates
        try:
            if len(df) > 0:
                start_date = df['date'].min() - pd.Timedelta(days=30)
                end_date = df['date'].max() + pd.Timedelta(days=30)
                
                stock_data = yf.download(ticker, start=start_date, end=end_date)
                if not stock_data.empty:
                    if isinstance(stock_data.columns, pd.MultiIndex):
                        stock_data.columns = [col[0] for col in stock_data.columns]
                    stock_data = stock_data.reset_index()
                    
                    # Add stock price line
                    fig.add_trace(go.Scatter(
                        x=stock_data['Date'],
                        y=stock_data['Close'],
                        mode='lines',
                        name=f'{ticker} Stock Price',
                        line=dict(color='blue', width=2),
                        yaxis='y2'
                    ))
        except Exception as e:
            st.warning(f"Could not load stock price: {e}")
        
        # Add target prices colored by recommendation
        if len(df) > 0:
            rec_colors = {'Buy': 'green', 'Hold': 'orange', 'Sell': 'red', 'Strong Buy': 'darkgreen', 'Strong Sell': 'darkred'}
            
            for rec in df['recommendation'].unique():
                if pd.notna(rec):
                    rec_df = df[df['recommendation'] == rec]
                    fig.add_trace(go.Scatter(
                        x=rec_df['date'],
                        y=rec_df['target_price'],
                        mode='markers',
                        name=f'{rec} (Target Price)',
                        marker=dict(
                            color=rec_colors.get(rec, 'blue'),
                            size=8
                        ),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                      'Date: %{x}<br>' +
                                      'Target Price: $%{y:.2f}<br>' +
                                      '<extra></extra>'
                    ))
        
        fig.update_layout(
            title=f"{ticker} - Target Prices vs Stock Price ({selected_type})",
            xaxis_title="Date",
            yaxis=dict(title="Target Price ($)", side="left"),
            yaxis2=dict(title="Stock Price ($)", side="right", overlaying="y"),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show table
        st.subheader("📊 Recent Recommendations")
        display_df = df.copy()
        display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
        display_df = display_df[['date', 'recommendation', 'target_price', 'current_price', 'confidence']].head(10)
        st.dataframe(display_df, use_container_width=True)
    
    filtered_chart()

def show_method_performance(ticker: str, method_data):
    """Show analysis method performance"""
    
    st.subheader("🔬 Method Performance")
    
    if not method_data:
        st.info("No method performance data available")
        return
    
    # Create tabs for different methods
    methods = list(method_data.keys())
    if methods:
        tabs = st.tabs(methods)
        
        for i, method in enumerate(methods):
            with tabs[i]:
                method_df = pd.DataFrame(method_data[method])
                if not method_df.empty:
                    method_df['date'] = pd.to_datetime(method_df['date'])
                    
                    # Method performance chart
                    fig = px.line(
                        method_df, 
                        x='date', 
                        y='target_price',
                        title=f"{method.upper()} Target Price Evolution",
                        markers=True
                    )
                    
                    # Color by recommendation
                    rec_colors = {'Buy': 'green', 'Hold': 'orange', 'Sell': 'red', 'Strong Buy': 'darkgreen'}
                    for rec in method_df['recommendation'].unique():
                        if pd.notna(rec):
                            rec_df = method_df[method_df['recommendation'] == rec]
                            fig.add_scatter(
                                x=rec_df['date'],
                                y=rec_df['target_price'],
                                mode='markers',
                                name=rec,
                                marker=dict(color=rec_colors.get(rec, 'gray'), size=10)
                            )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Method statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Analyses", len(method_df))
                    with col2:
                        buy_pct = (method_df['recommendation'].isin(['Buy', 'Strong Buy']).sum() / len(method_df)) * 100
                        st.metric("Buy Recommendations", f"{buy_pct:.1f}%")
                    with col3:
                        avg_target = method_df['target_price'].mean()
                        st.metric("Avg Target Price", f"${avg_target:.2f}")

def show_thesis_evolution(ticker: str, thesis_data):
    """Show thesis evolution over time"""
    
    st.subheader("📝 Thesis Evolution")
    
    if not thesis_data:
        st.info("No thesis evolution data available")
        return

def show_bulk_analysis():
    """Show bulk analysis dashboard with exchange-level view"""
    
    st.title("📊 Bulk Analysis Dashboard")
    st.markdown("*Top-down view from exchange level to bullish convergence*")
    
    # Get available exchanges first
    try:
        exchanges_data = get_available_exchanges()
        
        if not exchanges_data:
            st.warning("No analysis data found in database. Run some batch analyses first.")
            return
        
        # Initialize session state for selections
        if 'selected_exchange' not in st.session_state:
            st.session_state.selected_exchange = 'All Exchanges'
        if 'selected_batch_id' not in st.session_state:
            st.session_state.selected_batch_id = None
        
        @st.fragment
        def exchange_batch_selector():
            # Exchange selection dropdown
            exchange_options = ['All Exchanges'] + list(exchanges_data.keys())
            selected_exchange = st.selectbox(
                "Select Exchange:",
                exchange_options,
                index=exchange_options.index(st.session_state.selected_exchange) if st.session_state.selected_exchange in exchange_options else 0,
                key="bulk_exchange_selector"
            )
            
            # Get batch jobs list for selected exchange
            batch_jobs = get_batch_jobs_list(selected_exchange if selected_exchange != 'All Exchanges' else None)
            
            if batch_jobs:
                # Batch job selection
                st.subheader("📋 Available Batch Jobs")
                
                # Create batch job options with details
                batch_options = ['Latest'] + [
                    f"{job['completed_at']} - {job['batch_name']} ({job['total_stocks']} stocks)"
                    for job in batch_jobs
                ]
                
                selected_batch_option = st.selectbox(
                    "Select Batch Job:",
                    batch_options,
                    index=0,
                    key="bulk_batch_selector"
                )
                
                # Determine which batch job to load
                selected_batch_id = None
                if selected_batch_option != 'Latest':
                    # Extract batch_id from selected option
                    batch_index = batch_options.index(selected_batch_option) - 1
                    selected_batch_id = batch_jobs[batch_index]['batch_id']
                
                # Store selections in session state
                st.session_state.selected_exchange = selected_exchange
                st.session_state.selected_batch_id = selected_batch_id
        
        exchange_batch_selector()
        
        # Get bulk analysis data for selected batch
        bulk_data = get_bulk_analysis_data(
            st.session_state.selected_exchange if st.session_state.selected_exchange != 'All Exchanges' else None,
            st.session_state.selected_batch_id
        )
        
        if not bulk_data:
            st.warning(f"No bulk analysis data found for {selected_exchange}")
            return
        
        # Show analysis run info
        if 'latest_run_info' in bulk_data:
            run_info = bulk_data['latest_run_info']
            st.info(f"📅 **Latest Analysis Run**: {run_info['date']} | **Batch ID**: {run_info['batch_id']} | **Stocks Analyzed**: {run_info['stock_count']}")
        
        # Display sections
        show_exchange_overview(bulk_data)
        show_bullish_convergence_analysis(bulk_data)
        show_top_performers(bulk_data)
        
    except Exception as e:
        st.error(f"Error loading bulk analysis data: {str(e)}")

def get_available_exchanges():
    """Get available exchanges from database"""
    try:
        response = requests.get("http://localhost:8000/api/history/bulk/exchanges")
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def get_bulk_analysis_data(exchange: str = None, batch_job_id: str = None):
    """Get bulk analysis data from database"""
    try:
        url = "http://localhost:8000/api/history/bulk/analysis"
        params = {}
        if exchange:
            params['exchange'] = exchange
        if batch_job_id:
            params['batch_job_id'] = batch_job_id
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def get_batch_jobs_list(exchange: str = None):
    """Get list of all batch jobs for an exchange"""
    try:
        url = "http://localhost:8000/api/history/bulk/jobs"
        if exchange:
            url += f"?exchange={exchange}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def show_exchange_overview(bulk_data):
    """Show exchange-level analysis overview"""
    
    st.subheader("🏛️ Exchange Overview")
    
    if 'exchange_summary' not in bulk_data:
        st.info("No exchange summary data available")
        return
    
    exchange_df = pd.DataFrame(bulk_data['exchange_summary'])
    
    # Exchange metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_stocks = exchange_df['total_stocks'].sum()
        st.metric("Total Analyzed", total_stocks)
    
    with col2:
        bullish_stocks = exchange_df['bullish_count'].sum()
        st.metric("Bullish Signals", bullish_stocks)
    
    with col3:
        convergence_rate = (exchange_df['convergent_count'].sum() / total_stocks * 100) if total_stocks > 0 else 0
        st.metric("Convergence Rate", f"{convergence_rate:.1f}%")
    
    with col4:
        avg_confidence = exchange_df['avg_confidence'].mean()
        st.metric("Avg Confidence", f"{avg_confidence:.1f}%")
    
    # Exchange breakdown chart
    fig = px.bar(
        exchange_df,
        x='exchange',
        y=['bullish_count', 'bearish_count', 'neutral_count'],
        title="Recommendation Distribution by Exchange",
        barmode='stack'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Exchange table
    st.dataframe(exchange_df, use_container_width=True)

def show_bullish_convergence_analysis(bulk_data):
    """Show bullish convergence analysis with analyst alignment"""
    
    st.subheader("🎯 Bullish Convergence Analysis (Analyst Aligned)")
    st.markdown("*Stocks where our methods agree with analysts on ≥20% upside*")
    
    if 'convergence_analysis' not in bulk_data:
        st.info("No convergence analysis data available")
        return
    
    convergence_df = pd.DataFrame(bulk_data['convergence_analysis'])
    
    if convergence_df.empty:
        st.warning("No bullish convergent stocks found. This means no stocks have both our analysis and analyst consensus showing ≥20% upside.")
        return
    
    @st.fragment
    def convergence_filters():
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            min_methods = st.slider("Minimum Converging Methods", 1, 6, 1)
        
        with col2:
            min_upside = st.slider("Minimum Upside %", 20, 100, 20)
        
        # Apply filters
        filtered_df = convergence_df[
            (convergence_df['converging_methods'] >= min_methods) &
            (convergence_df['our_upside'] >= min_upside)
        ]
        
        # Convergence metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Convergent Stocks", len(filtered_df))
        
        with col2:
            multi_method = len(filtered_df[filtered_df['converging_methods'] > 1])
            st.metric("Multi-Method", multi_method)
        
        with col3:
            avg_upside = filtered_df['our_upside'].mean() if len(filtered_df) > 0 else 0
            st.metric("Avg Our Upside", f"{avg_upside:.1f}%")
        
        with col4:
            avg_analyst = filtered_df['analyst_upside'].mean() if len(filtered_df) > 0 else 0
            st.metric("Avg Analyst Upside", f"{avg_analyst:.1f}%")
        
        # Convergence scatter plot
        if len(filtered_df) > 0:
            fig = px.scatter(
                filtered_df,
                x='our_upside',
                y='analyst_upside',
                color='converging_methods',
                size='analyst_count',
                hover_data=['ticker', 'methods_list'],
                title="Bullish Convergence: Our Upside vs Analyst Upside",
                labels={'our_upside': 'Our Upside %', 'analyst_upside': 'Analyst Upside %'}
            )
            # Add diagonal line (perfect agreement)
            fig.add_shape(type='line', x0=20, y0=20, x1=100, y1=100, 
                         line=dict(color='gray', dash='dash'))
            st.plotly_chart(fig, use_container_width=True)
            
            # Top convergent stocks table
            st.subheader("🏆 Top Convergent Opportunities")
            
            # Refresh button
            if st.button("🔄 Refresh Analysis", key="refresh_convergence"):
                st.rerun()
            
            @st.fragment
            def table_filters():
                # Additional filters for table
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    ticker_filter = st.text_input("Filter by Ticker", "", key="ticker_filter")
                with col2:
                    method_count_options = [1, 2, 3]
                    method_count_filter = st.multiselect(
                        "Method Count",
                        options=method_count_options,
                        default=method_count_options,
                        key="method_count_filter"
                    )
                with col3:
                    methods_list_filter = st.text_input("Filter by Methods", "", key="methods_list_filter", 
                                                       placeholder="e.g. dcf, technical")
                with col4:
                    our_upside_filter = st.number_input("Min Our Upside %", min_value=0, max_value=1000, value=0, key="our_upside_filter")
                with col5:
                    analyst_upside_filter = st.number_input("Min Analyst Upside %", min_value=0, max_value=1000, value=0, key="analyst_upside_filter")
                
                # Apply table filters
                table_df = filtered_df.copy()
                if ticker_filter:
                    table_df = table_df[table_df['ticker'].str.contains(ticker_filter.upper(), case=False, na=False)]
                if method_count_filter:
                    table_df = table_df[table_df['converging_methods'].isin(method_count_filter)]
                if methods_list_filter:
                    table_df = table_df[table_df['methods_list'].str.contains(methods_list_filter, case=False, na=False)]
                table_df = table_df[
                    (table_df['our_upside'] >= our_upside_filter) &
                    (table_df['analyst_upside'] >= analyst_upside_filter)
                ]
                
                display_df = table_df[['ticker', 'converging_methods', 'methods_list', 'our_upside', 
                                          'analyst_upside', 'analyst_count', 'current_price', 'analyst_target', 'quant_target']].copy()
                display_df.columns = ['Ticker', 'Methods', 'Methods List', 'Our Upside %', 
                                     'Analyst Upside %', 'Analysts', 'Current $', 'Analyst Target $', 'Quant Target $']
                
                st.info(f"Showing all {len(display_df)} stocks matching filters")
                st.dataframe(display_df, use_container_width=True)
            
            table_filters()
            
            # Method distribution
            st.subheader("📊 Method Distribution")
            method_counts = {}
            for methods_list in filtered_df['methods_list']:
                for method in methods_list.split(', '):
                    method_counts[method] = method_counts.get(method, 0) + 1
            
            if method_counts:
                method_df = pd.DataFrame(list(method_counts.items()), columns=['Method', 'Count'])
                fig_methods = px.bar(method_df, x='Method', y='Count', 
                                    title="Convergent Stocks by Analysis Method")
                st.plotly_chart(fig_methods, use_container_width=True)
        else:
            st.info("No stocks meet the current filter criteria")
    
    convergence_filters()

def show_top_performers(bulk_data):
    """Show top performers by analysis method"""
    
    st.subheader("🥇 Top Performers by Method")
    
    if 'method_performance' not in bulk_data:
        st.info("No method performance data available")
        return
    
    method_data = bulk_data['method_performance']
    
    # Create tabs for each method
    methods = list(method_data.keys())
    if methods:
        tabs = st.tabs(methods)
        
        for i, method in enumerate(methods):
            with tabs[i]:
                method_df = pd.DataFrame(method_data[method])
                
                if not method_df.empty:
                    # Method summary metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        bullish_rate = (method_df['recommendation'].isin(['Buy', 'Strong Buy']).sum() / len(method_df)) * 100
                        st.metric(f"{method} Bullish Rate", f"{bullish_rate:.1f}%")
                    
                    with col2:
                        avg_upside = method_df['upside_potential'].mean()
                        st.metric("Avg Upside", f"{avg_upside:.1f}%")
                    
                    with col3:
                        high_conf_count = (method_df['confidence'] >= 80).sum()
                        st.metric("High Confidence", high_conf_count)
                    
                    # Top picks for this method
                    top_picks = method_df.nlargest(5, 'upside_potential')
                    st.dataframe(
                        top_picks[['ticker', 'recommendation', 'upside_potential', 'confidence', 'target_price']],
                        use_container_width=True
                    )
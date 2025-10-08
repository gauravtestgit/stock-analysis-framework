import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import os

def show_bullish_convergence():
    """Show bullish convergence consolidated analysis page"""
    
    st.title("🚀 Bullish Convergence Analysis")
    st.markdown("---")
    
    # Directory input
    st.sidebar.header("📁 Data Source")
    
    # Find available directories with bullish convergence data
    available_dirs = find_available_directories()
    
    if available_dirs:
        selected_dir = st.sidebar.selectbox(
            "Select Analysis Directory:",
            options=available_dirs,
            help="Choose directory containing bullish_convergent_consolidated.csv"
        )
        base_dir = selected_dir
    else:
        base_dir = st.sidebar.text_input(
            "Base Directory:",
            value="../resources/stock_analyses/alignment/",
            help="Directory containing bullish_convergent_consolidated.csv"
        )
    
    # Load convergence data
    convergence_data = load_convergence_data(base_dir)
    if convergence_data is None:
        st.error(f"No bullish_convergent_consolidated.csv found in: {base_dir}")
        st.info("""
        **To generate bullish convergence data:**
        1. Run batch analysis first: `python src/share_insights_v1/tests/test_batch_analysis.py`
        2. Run method comparison: `python src/share_insights_v1/tests/test_batch_comparison.py`
        3. Run bullish convergence: `python src/share_insights_v1/tests/test_bullish_convergence.py`
        """)
        return
    
    df, file_path = convergence_data
    st.success(f"Loaded {len(df)} stocks from: {os.path.basename(file_path)}")
    
    # Overview metrics
    st.subheader("📊 Convergence Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stocks", len(df))
    with col2:
        multi_method = len(df[df['methods_count'] > 1])
        st.metric("Multi-Method", multi_method)
    with col3:
        avg_methods = df['methods_count'].mean()
        st.metric("Avg Methods", f"{avg_methods:.1f}")
    with col4:
        max_upside = df['analyst_upside'].max()
        st.metric("Max Analyst Upside", f"{max_upside:.0f}%")
    
    # Method distribution
    col1, col2 = st.columns(2)
    
    with col1:
        # Methods count distribution
        methods_dist = df['methods_count'].value_counts().sort_index()
        fig_methods = px.bar(
            x=methods_dist.index,
            y=methods_dist.values,
            title="Distribution by Number of Methods",
            labels={'x': 'Number of Methods', 'y': 'Stock Count'}
        )
        st.plotly_chart(fig_methods, use_container_width=True)
    
    with col2:
        # Method coverage
        method_coverage = {}
        for method in ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP']:
            count = len(df[df[method] != ''])
            method_coverage[method] = count
        
        fig_coverage = px.pie(
            values=list(method_coverage.values()),
            names=list(method_coverage.keys()),
            title="Method Coverage"
        )
        st.plotly_chart(fig_coverage, use_container_width=True)
    
    # Top performers
    st.subheader("🏆 Top Performers")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        min_methods = st.selectbox("Minimum Methods:", [1, 2, 3, 4], index=1)
    with col2:
        min_upside = st.slider("Min Analyst Upside (%):", 0, 200, 50)
    with col3:
        min_analysts = st.slider("Min Analyst Count:", 1, int(df['analyst_count'].max()), 1)
    
    # Apply filters
    filtered_df = df[
        (df['methods_count'] >= min_methods) &
        (df['analyst_upside'] >= min_upside) &
        (df['analyst_count'] >= min_analysts)
    ].sort_values(['methods_count', 'analyst_upside'], ascending=[False, False])
    
    st.write(f"Showing {len(filtered_df)} stocks matching filters")
    
    # Top stocks table with watchlist checkboxes
    if not filtered_df.empty:
        display_cols = ['ticker', 'methods_count', 'methods_list', 'analyst_upside', 'analyst_count']
        
        from watchlist_component import get_watchlist
        watchlist = get_watchlist()
        top_stocks = filtered_df[display_cols].head(20).copy()
        top_stocks['In Watchlist'] = top_stocks['ticker'].isin(watchlist)
        
        edited_top = st.data_editor(
            top_stocks,
            column_config={"In Watchlist": st.column_config.CheckboxColumn("📋 Watchlist")},
            use_container_width=True,
            key="top_stocks_watchlist_editor"
        )
        
        # Update watchlist based on changes
        from watchlist_component import init_watchlist
        init_watchlist()
        
        # Check for changes by comparing with original data
        if not edited_top.equals(top_stocks):
            for idx, row in edited_top.iterrows():
                ticker = row['ticker']
                in_watchlist = row['In Watchlist']
                if in_watchlist and ticker not in st.session_state.watchlist:
                    st.session_state.watchlist.append(ticker)
                elif not in_watchlist and ticker in st.session_state.watchlist:
                    st.session_state.watchlist.remove(ticker)
            st.rerun()
        
        # Scatter plot
        fig_scatter = px.scatter(
            filtered_df,
            x='methods_count',
            y='analyst_upside',
            size='analyst_count',
            hover_data=['ticker', 'methods_list'],
            title="Methods Count vs Analyst Upside",
            labels={'methods_count': 'Number of Methods', 'analyst_upside': 'Analyst Upside (%)'}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Method-specific analysis
    st.subheader("🔍 Method-Specific Analysis")
    
    selected_method = st.selectbox("Select Method:", ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP'])
    
    method_stocks = df[df[selected_method] != ''].copy()
    if not method_stocks.empty:
        method_stocks[f'{selected_method}_upside'] = pd.to_numeric(method_stocks[selected_method], errors='coerce')
        method_stocks = method_stocks.dropna(subset=[f'{selected_method}_upside'])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"{selected_method} Stocks", len(method_stocks))
            avg_upside = method_stocks[f'{selected_method}_upside'].mean()
            st.metric(f"Avg {selected_method} Upside", f"{avg_upside:.1f}%")
        
        with col2:
            # Top stocks for this method
            top_method_stocks = method_stocks.nlargest(10, f'{selected_method}_upside')
            st.write(f"**Top {selected_method} Opportunities:**")
            for _, row in top_method_stocks.iterrows():
                st.write(f"• {row['ticker']}: {row[f'{selected_method}_upside']:.1f}% (Analyst: {row['analyst_upside']:.1f}%)")
    
    # Detailed stock analysis
    st.subheader("📋 Stock Details")
    
    selected_ticker = st.selectbox("Select Stock for Details:", filtered_df['ticker'].tolist() if not filtered_df.empty else [])
    
    if selected_ticker:
        stock_data = df[df['ticker'] == selected_ticker].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{selected_ticker} Analysis:**")
            st.write(f"• Methods: {stock_data['methods_list']}")
            st.write(f"• Analyst Upside: {stock_data['analyst_upside']:.1f}%")
            st.write(f"• Analyst Count: {stock_data['analyst_count']}")
        
        with col2:
            # Method comparison for this stock
            methods_data = []
            for method in ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP']:
                if stock_data[method] != '':
                    upside = pd.to_numeric(stock_data[method], errors='coerce')
                    if not pd.isna(upside):
                        methods_data.append({'Method': method, 'Upside': upside})
            
            if methods_data:
                methods_df = pd.DataFrame(methods_data)
                fig_stock = px.bar(
                    methods_df,
                    x='Method',
                    y='Upside',
                    title=f"{selected_ticker} Method Comparison"
                )
                st.plotly_chart(fig_stock, use_container_width=True)
    
    # Full data table with watchlist checkboxes
    st.subheader("📊 All Data")
    
    from watchlist_component import get_watchlist
    watchlist = get_watchlist()
    all_data_display = filtered_df.copy()
    all_data_display['In Watchlist'] = all_data_display['ticker'].isin(watchlist)
    
    edited_all = st.data_editor(
        all_data_display,
        column_config={"In Watchlist": st.column_config.CheckboxColumn("📋 Watchlist")},
        use_container_width=True,
        key="all_data_watchlist_editor"
    )
    
    # Update watchlist based on changes
    from watchlist_component import init_watchlist
    init_watchlist()
    
    # Check for changes by comparing with original data
    if not edited_all.equals(all_data_display):
        for idx, row in edited_all.iterrows():
            ticker = row['ticker']
            in_watchlist = row['In Watchlist']
            if in_watchlist and ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(ticker)
            elif not in_watchlist and ticker in st.session_state.watchlist:
                st.session_state.watchlist.remove(ticker)
        st.rerun()

def find_available_directories():
    """Find directories containing bullish_convergent_consolidated.csv"""
    base_path = "../resources/stock_analyses"
    available_dirs = []
    
    try:
        # Check main alignment directory
        main_dir = f"{base_path}/alignment"
        if os.path.exists(f"{main_dir}/bullish_convergent_consolidated.csv"):
            available_dirs.append(main_dir)
        
        # Check subdirectories
        if os.path.exists(base_path):
            for item in os.listdir(base_path):
                item_path = os.path.join(base_path, item)
                if os.path.isdir(item_path) and item.startswith('alignment-'):
                    if os.path.exists(f"{item_path}/bullish_convergent_consolidated.csv"):
                        available_dirs.append(item_path)
    except Exception:
        pass
    
    return available_dirs

@st.cache_data
def load_convergence_data(base_dir):
    """Load bullish convergent consolidated data"""
    file_path = f"{base_dir.rstrip('/')}/bullish_convergent_consolidated.csv"
    
    if not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_csv(file_path, index_col=0)  # ticker is index
        df = df.reset_index()  # Make ticker a column
        return df, file_path
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

if __name__ == "__main__":
    show_bullish_convergence()
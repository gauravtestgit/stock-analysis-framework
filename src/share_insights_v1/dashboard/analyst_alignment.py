import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import glob
import os

def show_analyst_alignment():
    """Show analyst alignment analysis page"""
    
    st.title("🎯 Analyst Alignment Analysis")
    st.markdown("---")
    
    # Directory input with session state
    st.sidebar.header("📁 Data Source")
    
    # Initialize session state for base directory
    if 'analyst_alignment_base_dir' not in st.session_state:
        st.session_state.analyst_alignment_base_dir = "../resources/stock_analyses/alignment"
    
    base_dir = st.sidebar.text_input(
        "Base Directory:",
        value=st.session_state.analyst_alignment_base_dir,
        help="Directory containing method-specific CSV files",
        key="alignment_base_dir_input"
    )
    
    # Update session state when directory changes
    if base_dir != st.session_state.analyst_alignment_base_dir:
        st.session_state.analyst_alignment_base_dir = base_dir
    
    # Load alignment data
    alignment_data = load_alignment_data(base_dir)
    if alignment_data is None:
        st.error("No method-specific alignment files found. Run batch comparison analysis first.")
        return
    
    df, files_found = alignment_data
    st.success(f"Loaded {len(files_found)} method-specific files from: {base_dir}")
    
    # Method performance overview
    st.subheader("📊 Method Performance Summary")
    
    # Try to load report file for accurate alignment rates
    report_stats = load_report_stats(base_dir)
    
    # Calculate method statistics from file types
    method_stats = []
    for method in ['dcf', 'technical', 'comparable', 'startup']:
        method_data = df[df['method'] == method]
        if not method_data.empty:
            aligned_count = len(method_data[method_data['file_type'] == 'aligned'])
            divergent_count = len(method_data[method_data['file_type'] == 'divergent'])
            bullish_count = len(method_data[method_data['file_type'] == 'bullish_convergent'])
            total_in_files = aligned_count + divergent_count + bullish_count
            
            # Calculate alignment rate correctly: aligned / (aligned + divergent)
            # Bullish convergent are also aligned, so include them
            total_valid_comparisons = aligned_count + divergent_count
            alignment_rate = (aligned_count/total_valid_comparisons)*100 if total_valid_comparisons > 0 else 0
            total_comparisons = total_valid_comparisons
            
            method_stats.append({
                'Method': method.upper(),
                'Aligned': aligned_count,
                'Divergent': divergent_count,
                'Bullish Convergent': bullish_count,
                'Total': total_comparisons,
                'Alignment Rate': alignment_rate
            })
    
    if method_stats:
        stats_df = pd.DataFrame(method_stats)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        for i, (_, row) in enumerate(stats_df.iterrows()):
            with [col1, col2, col3, col4][i]:
                st.metric(
                    f"{row['Method']} Method",
                    f"{row['Alignment Rate']:.1f}%",
                    f"{row['Aligned']} aligned"
                )
        
        # Alignment rate chart
        fig_alignment = px.bar(
            stats_df, 
            x='Method', 
            y='Alignment Rate',
            title="Alignment Rate by Method",
            color='Alignment Rate',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_alignment, use_container_width=True)
        
        # Method comparison table
        st.subheader("📋 Detailed Method Statistics")
        st.dataframe(stats_df, use_container_width=True)
    
    # Bullish convergent analysis (moved to second position)
    st.subheader("🚀 Bullish Convergent Analysis")
    
    # Load consolidated bullish convergent data
    convergence_data = load_bullish_convergent_data(base_dir)
    if convergence_data is not None:
        conv_df, conv_file = convergence_data
        st.success(f"Loaded {len(conv_df)} bullish convergent stocks from consolidated file")
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Stocks", len(conv_df))
        with col2:
            multi_method = len(conv_df[conv_df['methods_count'] > 1])
            st.metric("Multi-Method", multi_method)
        with col3:
            avg_methods = conv_df['methods_count'].mean()
            st.metric("Avg Methods", f"{avg_methods:.1f}")
        with col4:
            max_upside = conv_df['analyst_upside'].max() if 'analyst_upside' in conv_df.columns else 0
            st.metric("Max Analyst Upside", f"{max_upside:.0f}%")
        
        # Filters for bullish convergent stocks
        st.write("**Filter Bullish Convergent Stocks:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ticker_search = st.text_input("🔍 Search Ticker:", key="conv_ticker_search")
        with col2:
            methods_search = st.text_input("🔍 Search Methods:", key="conv_methods_search", help="e.g. 'DCF,TECHNICAL' or 'STARTUP'")
        with col3:
            min_methods_conv = st.selectbox("Min Methods:", [1, 2, 3, 4], key="conv_min_methods")
        with col4:
            min_upside_conv = st.slider("Min Upside (%):", 0, 200, 0, key="conv_min_upside")
        
        # Apply filters
        filtered_conv = conv_df.copy()
        if ticker_search:
            filtered_conv = filtered_conv[filtered_conv['ticker'].str.contains(ticker_search, case=False, na=False)]
        if methods_search:
            filtered_conv = filtered_conv[filtered_conv['methods_list'].str.contains(methods_search, case=False, na=False)]
        filtered_conv = filtered_conv[
            (filtered_conv['methods_count'] >= min_methods_conv) &
            (filtered_conv['analyst_upside'] >= min_upside_conv)
        ]
        
        st.write(f"**Showing {len(filtered_conv)} of {len(conv_df)} stocks:**")
        display_cols = ['ticker', 'methods_count', 'methods_list', 'analyst_upside', 'analyst_count']
        available_cols = [col for col in display_cols if col in filtered_conv.columns]
        
        # Display table with sorting/filtering capabilities
        st.dataframe(filtered_conv[available_cols], use_container_width=True)
    else:
        st.info("No bullish convergent consolidated data found. Run bullish convergence analysis first.")
    
    # File type analysis
    st.subheader("📁 Analysis by File Type")
    
    col1, col2 = st.columns(2)
    with col1:
        method_filter = st.selectbox("Select Method:", ['dcf', 'technical', 'comparable', 'startup'])
    with col2:
        file_type_filter = st.selectbox("Select File Type:", ['aligned', 'divergent', 'bullish_convergent'])
    
    method_data = df[(df['method'] == method_filter) & (df['file_type'] == file_type_filter)]
    aligned_stocks = method_data.head(20)
    
    if not method_data.empty:
        # Filters for method-specific data
        col1, col2 = st.columns(2)
        with col1:
            ticker_search_method = st.text_input("🔍 Search Ticker:", key=f"{method_filter}_{file_type_filter}_search")
        with col2:
            min_upside_method = st.slider("Min Our Upside (%):", -100, 200, -100, key=f"{method_filter}_{file_type_filter}_upside")
        
        # Apply filters
        filtered_method = method_data.copy()
        if ticker_search_method:
            filtered_method = filtered_method[filtered_method['ticker'].str.contains(ticker_search_method, case=False, na=False)]
        filtered_method = filtered_method[filtered_method['our_upside'] >= min_upside_method]
        
        aligned_stocks = filtered_method.head(20)
        st.write(f"**Showing top 20 of {len(filtered_method)} filtered stocks:**")
        
        # Display table with sorting/filtering capabilities
        display_cols = ['ticker', 'our_upside', 'analyst_upside', 'deviation_score', 'alignment', 'analyst_count']
        st.dataframe(aligned_stocks[display_cols], use_container_width=True)
        
        # Scatter plot of alignment (use filtered data)
        fig_scatter = px.scatter(
            filtered_method,
            x='analyst_upside',
            y='our_upside',
            color='alignment',
            size='analyst_count',
            hover_data=['ticker'],
            title=f"{method_filter.upper()} Method: Our Upside vs Analyst Upside (Filtered)",
            labels={'analyst_upside': 'Analyst Upside (%)', 'our_upside': 'Our Upside (%)'}
        )
        # Add diagonal line for perfect alignment
        if not filtered_method.empty:
            fig_scatter.add_shape(
                type="line",
                x0=filtered_method['analyst_upside'].min(),
                y0=filtered_method['analyst_upside'].min(),
                x1=filtered_method['analyst_upside'].max(),
                y1=filtered_method['analyst_upside'].max(),
                line=dict(color="red", width=2, dash="dash")
            )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info(f"No stocks found for {method_filter.upper()} method with current filters")
    

    
    # Filters and detailed view
    st.subheader("🔍 Detailed Analysis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ticker_search_detailed = st.text_input("🔍 Search Ticker:", key="detailed_ticker_search")
    with col2:
        alignment_filter = st.multiselect(
            "Filter by Alignment:",
            df['alignment'].unique(),
            default=df['alignment'].unique()
        )
    with col3:
        min_analysts = st.slider("Minimum Analyst Count:", 1, int(df['analyst_count'].max()), 1)
    
    # Apply filters
    filtered_df = df[
        (df['alignment'].isin(alignment_filter)) &
        (df['analyst_count'] >= min_analysts)
    ]
    
    if ticker_search_detailed:
        filtered_df = filtered_df[filtered_df['ticker'].str.contains(ticker_search_detailed, case=False, na=False)]
    
    st.write(f"Showing {len(filtered_df)} stocks matching filters")
    
    # Full data table with sorting/filtering capabilities
    display_cols = ['ticker', 'method', 'our_upside', 'analyst_upside', 'deviation_score', 
                   'alignment', 'both_bullish', 'analyst_count']
    st.dataframe(filtered_df[display_cols], use_container_width=True)

@st.cache_data
def load_alignment_data(base_dir):
    """Load method-specific alignment files (aligned, divergent, bullish_convergent)"""
    
    all_data = []
    methods = ['dcf', 'technical', 'comparable', 'startup']
    file_types = ['aligned', 'divergent', 'bullish_convergent']
    
    files_found = []
    
    # Convert relative path to absolute path relative to dashboard location
    if not os.path.isabs(base_dir):
        # Get the directory where this dashboard file is located
        dashboard_dir = os.path.dirname(os.path.abspath(__file__))
        # Resolve relative path from dashboard directory
        base_dir = os.path.abspath(os.path.join(dashboard_dir, base_dir))
    
    # Debug: Show what directory we're looking in
    st.write(f"**Debug:** Looking for files in: {base_dir}")
    st.write(f"**Debug:** Directory exists: {os.path.exists(base_dir)}")
    
    for method in methods:
        for file_type in file_types:
            pattern = f"{base_dir.rstrip('/')}/{method}_{file_type}.csv"
            files = glob.glob(pattern)
            
            # Debug: Show what we're looking for
            expected_file = f"{base_dir.rstrip('/')}/{method}_{file_type}.csv"
            file_exists = os.path.exists(expected_file)
            st.write(f"**Debug:** Looking for {method}_{file_type}.csv - Exists: {file_exists}")
            
            if files:
                latest_file = max(files, key=os.path.getctime)
                try:
                    df = pd.read_csv(latest_file)
                    df['file_type'] = file_type
                    all_data.append(df)
                    files_found.append(os.path.basename(latest_file))
                except Exception as e:
                    st.warning(f"Could not load {latest_file}: {e}")
    
    if not all_data:
        return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    return combined_df, files_found

@st.cache_data
def load_report_stats(base_dir):
    """Load alignment statistics from report file"""
    import glob
    
    # Convert relative path to absolute path relative to dashboard location
    if not os.path.isabs(base_dir):
        dashboard_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(dashboard_dir, base_dir))
    
    # Find report file
    report_pattern = f"{base_dir.rstrip('/')}/*_report.txt"
    report_files = glob.glob(report_pattern)
    
    if not report_files:
        return None
    
    # Use most recent report
    report_file = max(report_files, key=os.path.getctime)
    
    try:
        with open(report_file, 'r') as f:
            content = f.read()
        
        # Parse method statistics
        stats = {}
        lines = content.split('\n')
        
        current_method = None
        for line in lines:
            line = line.strip()
            if line.endswith('METHOD:'):
                method_name = line.replace(' METHOD:', '').lower()
                current_method = method_name
                stats[current_method] = {}
            elif current_method and 'Total comparisons:' in line:
                stats[current_method]['total_comparisons'] = int(line.split(':')[1].strip())
            elif current_method and 'Alignment rate:' in line:
                rate_str = line.split(':')[1].strip().replace('%', '')
                stats[current_method]['alignment_rate'] = float(rate_str)
        
        return stats
    except Exception as e:
        st.warning(f"Could not parse report file: {e}")
        return None

@st.cache_data
def load_bullish_convergent_data(base_dir):
    """Load bullish convergent consolidated data"""
    # Convert relative path to absolute path relative to dashboard location
    if not os.path.isabs(base_dir):
        dashboard_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(dashboard_dir, base_dir))
    
    file_path = f"{base_dir.rstrip('/')}/bullish_convergent_consolidated.csv"
    
    if not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_csv(file_path, index_col=0)  # ticker is index
        df = df.reset_index()  # Make ticker a column
        return df, file_path
    except Exception as e:
        st.error(f"Error loading bullish convergent file: {e}")
        return None

if __name__ == "__main__":
    show_analyst_alignment()
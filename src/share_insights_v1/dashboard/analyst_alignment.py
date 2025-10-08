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
    
    # Calculate method statistics from file types
    method_stats = []
    for method in ['dcf', 'technical', 'comparable', 'startup']:
        method_data = df[df['method'] == method]
        if not method_data.empty:
            aligned_count = len(method_data[method_data['file_type'] == 'aligned'])
            divergent_count = len(method_data[method_data['file_type'] == 'divergent'])
            bullish_count = len(method_data[method_data['file_type'] == 'bullish_convergent'])
            total = aligned_count + divergent_count + bullish_count
            
            method_stats.append({
                'Method': method.upper(),
                'Aligned': aligned_count,
                'Divergent': divergent_count,
                'Bullish Convergent': bullish_count,
                'Total': total,
                'Alignment Rate': (aligned_count/total)*100 if total > 0 else 0
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
        
        # All bullish convergent stocks with watchlist checkboxes
        st.write("**All Bullish Convergent Stocks:**")
        display_cols = ['ticker', 'methods_count', 'methods_list', 'analyst_upside', 'analyst_count']
        available_cols = [col for col in display_cols if col in conv_df.columns]
        
        from watchlist_component import get_watchlist
        watchlist = get_watchlist()
        conv_df_display = conv_df[available_cols].copy()
        conv_df_display['In Watchlist'] = conv_df_display['ticker'].isin(watchlist)
        
        edited_conv = st.data_editor(
            conv_df_display,
            column_config={"In Watchlist": st.column_config.CheckboxColumn("📋 Watchlist")},
            use_container_width=True,
            key="conv_watchlist_editor"
        )
        
        # Update watchlist based on changes
        from watchlist_component import init_watchlist
        init_watchlist()
        
        # Check for changes by comparing with original data
        if not edited_conv.equals(conv_df_display):
            for idx, row in edited_conv.iterrows():
                ticker = row['ticker']
                in_watchlist = row['In Watchlist']
                if in_watchlist and ticker not in st.session_state.watchlist:
                    st.session_state.watchlist.append(ticker)
                elif not in_watchlist and ticker in st.session_state.watchlist:
                    st.session_state.watchlist.remove(ticker)
            st.rerun()
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
    
    if not aligned_stocks.empty:
        # Display top aligned stocks with watchlist checkboxes
        display_cols = ['ticker', 'our_upside', 'analyst_upside', 'deviation_score', 'alignment', 'analyst_count']
        
        from watchlist_component import get_watchlist
        watchlist = get_watchlist()
        aligned_display = aligned_stocks[display_cols].copy()
        aligned_display['In Watchlist'] = aligned_display['ticker'].isin(watchlist)
        
        edited_aligned = st.data_editor(
            aligned_display,
            column_config={"In Watchlist": st.column_config.CheckboxColumn("📋 Watchlist")},
            use_container_width=True,
            key="aligned_watchlist_editor"
        )
        
        # Update watchlist based on changes
        from watchlist_component import init_watchlist
        init_watchlist()
        
        # Check for changes by comparing with original data
        if not edited_aligned.equals(aligned_display):
            for idx, row in edited_aligned.iterrows():
                ticker = row['ticker']
                in_watchlist = row['In Watchlist']
                if in_watchlist and ticker not in st.session_state.watchlist:
                    st.session_state.watchlist.append(ticker)
                elif not in_watchlist and ticker in st.session_state.watchlist:
                    st.session_state.watchlist.remove(ticker)
            st.rerun()
        
        # Scatter plot of alignment
        fig_scatter = px.scatter(
            method_data,
            x='analyst_upside',
            y='our_upside',
            color='alignment',
            size='analyst_count',
            hover_data=['ticker'],
            title=f"{method_filter.upper()} Method: Our Upside vs Analyst Upside",
            labels={'analyst_upside': 'Analyst Upside (%)', 'our_upside': 'Our Upside (%)'}
        )
        # Add diagonal line for perfect alignment
        fig_scatter.add_shape(
            type="line",
            x0=method_data['analyst_upside'].min(),
            y0=method_data['analyst_upside'].min(),
            x1=method_data['analyst_upside'].max(),
            y1=method_data['analyst_upside'].max(),
            line=dict(color="red", width=2, dash="dash")
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info(f"No aligned stocks found for {method_filter.upper()} method")
    

    
    # Filters and detailed view
    st.subheader("🔍 Detailed Analysis")
    
    col1, col2 = st.columns(2)
    with col1:
        alignment_filter = st.multiselect(
            "Filter by Alignment:",
            df['alignment'].unique(),
            default=df['alignment'].unique()
        )
    
    with col2:
        min_analysts = st.slider("Minimum Analyst Count:", 1, int(df['analyst_count'].max()), 1)
    
    # Apply filters
    filtered_df = df[
        (df['alignment'].isin(alignment_filter)) &
        (df['analyst_count'] >= min_analysts)
    ]
    
    st.write(f"Showing {len(filtered_df)} stocks matching filters")
    
    # Full data table with watchlist checkboxes
    display_cols = ['ticker', 'method', 'our_upside', 'analyst_upside', 'deviation_score', 
                   'alignment', 'both_bullish', 'analyst_count']
    
    from watchlist_component import get_watchlist
    watchlist = get_watchlist()
    filtered_display = filtered_df[display_cols].copy()
    filtered_display['In Watchlist'] = filtered_display['ticker'].isin(watchlist)
    
    edited_filtered = st.data_editor(
        filtered_display,
        column_config={"In Watchlist": st.column_config.CheckboxColumn("📋 Watchlist")},
        use_container_width=True,
        key="filtered_watchlist_editor"
    )
    
    # Update watchlist based on changes
    from watchlist_component import init_watchlist
    init_watchlist()
    
    # Check for changes by comparing with original data
    if not edited_filtered.equals(filtered_display):
        for idx, row in edited_filtered.iterrows():
            ticker = row['ticker']
            in_watchlist = row['In Watchlist']
            if in_watchlist and ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(ticker)
            elif not in_watchlist and ticker in st.session_state.watchlist:
                st.session_state.watchlist.remove(ticker)
        st.rerun()

@st.cache_data
def load_alignment_data(base_dir):
    """Load method-specific alignment files (aligned, divergent, bullish_convergent)"""
    
    all_data = []
    methods = ['dcf', 'technical', 'comparable', 'startup']
    file_types = ['aligned', 'divergent', 'bullish_convergent']
    
    files_found = []
    
    for method in methods:
        for file_type in file_types:
            pattern = f"{base_dir.rstrip('/')}/{method}_{file_type}.csv"
            files = glob.glob(pattern)
            
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
def load_bullish_convergent_data(base_dir):
    """Load bullish convergent consolidated data"""
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
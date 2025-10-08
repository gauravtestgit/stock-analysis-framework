import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import glob
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_batch_results():
    """Load the latest batch analysis results"""
    analysis_dir = "../resources/stock_analyses/"
    csv_files = glob.glob(f"{analysis_dir}batch_analysis_*.csv")
    
    if not csv_files:
        return None
    
    # Get the latest file
    latest_file = max(csv_files, key=os.path.getctime)
    df = pd.read_csv(latest_file)
    
    # Parse quality score JSON
    if 'Quality_Score' in df.columns:
        df['Quality_Score_Parsed'] = df['Quality_Score'].apply(
            lambda x: json.loads(x.replace("'", '"')) if isinstance(x, str) else {}
        )
        df['Quality_Grade'] = df['Quality_Score_Parsed'].apply(lambda x: x.get('grade', 'N/A'))
        df['Quality_Numeric'] = df['Quality_Score_Parsed'].apply(lambda x: x.get('quality_score', 0))
    
    return df, latest_file

def main():
    st.title("📊 Stock Analysis Dashboard")
    st.markdown("---")
    
    # Load data
    data = load_batch_results()
    if data is None:
        st.error("No batch analysis results found. Run batch analysis first.")
        return
    
    df, file_path = data
    st.success(f"Loaded {len(df)} stocks from: {os.path.basename(file_path)}")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Recommendation filter
    recommendations = df['Final_Recommendation'].unique()
    selected_recs = st.sidebar.multiselect("Recommendations", recommendations, default=recommendations)
    
    # Sector filter
    sectors = df['Sector'].unique()
    selected_sectors = st.sidebar.multiselect("Sectors", sectors, default=sectors)
    
    # Quality grade filter
    if 'Quality_Grade' in df.columns:
        grades = df['Quality_Grade'].unique()
        selected_grades = st.sidebar.multiselect("Quality Grades", grades, default=grades)
        df_filtered = df[
            (df['Final_Recommendation'].isin(selected_recs)) &
            (df['Sector'].isin(selected_sectors)) &
            (df['Quality_Grade'].isin(selected_grades))
        ]
    else:
        df_filtered = df[
            (df['Final_Recommendation'].isin(selected_recs)) &
            (df['Sector'].isin(selected_sectors))
        ]
    
    # Main dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Stocks", len(df_filtered))
    with col2:
        buy_count = len(df_filtered[df_filtered['Final_Recommendation'] == 'Buy'])
        st.metric("Buy Recommendations", buy_count)
    with col3:
        avg_upside = ((df_filtered['DCF_Price'] / df_filtered['Current_Price'] - 1) * 100).mean()
        st.metric("Avg DCF Upside", f"{avg_upside:.1f}%")
    with col4:
        if 'Quality_Numeric' in df_filtered.columns:
            avg_quality = df_filtered['Quality_Numeric'].mean()
            st.metric("Avg Quality Score", f"{avg_quality:.0f}")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        # Recommendation distribution
        rec_counts = df_filtered['Final_Recommendation'].value_counts()
        fig_rec = px.pie(values=rec_counts.values, names=rec_counts.index, 
                        title="Recommendation Distribution")
        st.plotly_chart(fig_rec, use_container_width=True)
    
    with col2:
        # Sector distribution
        sector_counts = df_filtered['Sector'].value_counts().head(10)
        fig_sector = px.bar(x=sector_counts.values, y=sector_counts.index, 
                           orientation='h', title="Top Sectors")
        st.plotly_chart(fig_sector, use_container_width=True)
    
    # Price comparison chart
    st.subheader("💰 Price Analysis")
    
    # Calculate upside for each method
    df_filtered['DCF_Upside'] = (df_filtered['DCF_Price'] / df_filtered['Current_Price'] - 1) * 100
    df_filtered['Technical_Upside'] = (df_filtered['Technical_Price'] / df_filtered['Current_Price'] - 1) * 100
    df_filtered['Comparable_Upside'] = (df_filtered['Comparable_Price'] / df_filtered['Current_Price'] - 1) * 100
    df_filtered['AI_Upside'] = (df_filtered['AI_Insights_Price'] / df_filtered['Current_Price'] - 1) * 100
    
    # Scatter plot of upside vs quality
    if 'Quality_Numeric' in df_filtered.columns:
        fig_scatter = px.scatter(df_filtered, x='Quality_Numeric', y='DCF_Upside', 
                               color='Final_Recommendation', size='Current_Price',
                               hover_data=['Ticker', 'Sector'],
                               title="DCF Upside vs Quality Score")
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    # Detailed stock table
    st.subheader("📋 Detailed Analysis")
    
    # Stock selection for deep dive
    selected_ticker = st.selectbox("Select stock for detailed analysis:", 
                                  df_filtered['Ticker'].tolist())
    
    if selected_ticker:
        stock_data = df_filtered[df_filtered['Ticker'] == selected_ticker].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"📈 {selected_ticker} Overview")
            st.write(f"**Sector:** {stock_data['Sector']}")
            st.write(f"**Industry:** {stock_data['Industry']}")
            st.write(f"**Company Type:** {stock_data['Company_Type']}")
            st.write(f"**Current Price:** ${stock_data['Current_Price']:.2f}")
            st.write(f"**Final Recommendation:** {stock_data['Final_Recommendation']}")
            
            if 'Quality_Grade' in stock_data:
                st.write(f"**Quality Grade:** {stock_data['Quality_Grade']}")
        
        with col2:
            st.subheader("🎯 Price Targets")
            
            # Price comparison chart for selected stock
            methods = ['Current_Price', 'DCF_Price', 'Technical_Price', 'Comparable_Price', 'AI_Insights_Price', 'Analyst_Price']
            prices = [stock_data[method] for method in methods]
            method_names = ['Current', 'DCF', 'Technical', 'Comparable', 'AI Insights', 'Analyst']
            
            fig_prices = go.Figure(data=[
                go.Bar(x=method_names, y=prices, 
                      text=[f'${p:.2f}' for p in prices],
                      textposition='auto')
            ])
            fig_prices.update_layout(title=f"{selected_ticker} Price Targets", 
                                   yaxis_title="Price ($)")
            st.plotly_chart(fig_prices, use_container_width=True)
    
    # Full data table
    st.subheader("📊 All Stocks")
    
    # Display columns selection
    display_cols = ['Ticker', 'Final_Recommendation', 'Current_Price', 'DCF_Price', 
                   'Technical_Price', 'AI_Insights_Price', 'Analyst_Price', 'Sector']
    if 'Quality_Grade' in df_filtered.columns:
        display_cols.append('Quality_Grade')
    
    st.dataframe(df_filtered[display_cols], use_container_width=True)
    
    # Add to watchlist buttons for buy recommendations
    buy_stocks = df_filtered[df_filtered['Final_Recommendation'] == 'Buy']
    if not buy_stocks.empty:
        from watchlist_component import add_stock_to_watchlist_button
        st.write("**Quick Add Buy Recommendations to Watchlist:**")
        cols = st.columns(5)
        for i, ticker in enumerate(buy_stocks['Ticker'].head(10)):
            with cols[i % 5]:
                add_stock_to_watchlist_button(ticker)

if __name__ == "__main__":
    main()
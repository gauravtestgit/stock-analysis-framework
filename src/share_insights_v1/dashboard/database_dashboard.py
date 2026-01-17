import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import yfinance as yf
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.share_insights_v1.services.database.database_service import DatabaseService
from src.share_insights_v1.models.database import SessionLocal
from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation
from src.share_insights_v1.dashboard.components.disclaimer import show_disclaimer

class EnhancedDatabaseDashboard:
    def __init__(self):
        self.db_service = DatabaseService()
    
    def render_main_dashboard(self):
        """Render the main dashboard"""
        # Check authentication
        if not check_authentication():
            st.switch_page("run_login.py")
            return
        
        # Navigation bar
        render_navigation()
        
        st.title("📊 Stock Analysis Database Dashboard")
        show_disclaimer()
        st.markdown("*Database-driven analysis results from NASDAQ, NYSE, ASX, and NZX*")
        
        # Sidebar filters
        with st.sidebar:
            st.header("🔍 Navigation")
            
            # Navigation options
            nav_option = st.selectbox(
                "Choose View:",
                ["Database Dashboard", "Investment Thesis Generator"]
            )
        
        # Handle navigation outside sidebar
        if nav_option == "Investment Thesis Generator":
            from src.share_insights_v1.dashboard.pages.thesis_generation_full import show_thesis_generation
            show_thesis_generation()
            return
        
        # Continue with database dashboard
        with st.sidebar:
            st.header("🔍 Filters")
            
            # Get summary for filter options
            db = SessionLocal()
            try:
                summary = self.db_service.get_analysis_summary_stats(db)
            finally:
                db.close()
            
            # Exchange filter
            exchanges = ["All"] + list(summary.get('exchange_distribution', {}).keys())
            selected_exchange = st.selectbox("📈 Exchange", exchanges)
            exchange_filter = None if selected_exchange == "All" else selected_exchange
            
            # Recommendation filter
            recommendations = ["All"] + list(summary.get('recommendation_distribution', {}).keys())
            selected_recommendation = st.selectbox("💡 Recommendation", recommendations)
            
            # Price range filters
            min_price = st.number_input("💰 Min Target Price", min_value=0.0, value=0.0, step=1.0)
            max_price = st.number_input("💰 Max Target Price", min_value=0.0, value=1000.0, step=10.0)
            
            st.markdown("---")
            
            # Database info
            st.subheader("📊 Database Info")
            st.metric("Total Stocks", summary.get('total_stocks', 0))
            
            latest_date = summary.get('latest_analysis_date')
            if latest_date:
                st.metric("Latest Analysis", latest_date.strftime('%Y-%m-%d'))
        
        # Load and filter data
        db = SessionLocal()
        try:
            results = self.db_service.search_analysis_results(
                db,
                recommendation=selected_recommendation if selected_recommendation != "All" else None,
                exchange=exchange_filter,
                min_target_price=min_price if min_price > 0 else None,
                max_target_price=max_price if max_price < 1000 else None,
                limit=1000
            )
        finally:
            db.close()
        
        if not results:
            st.warning("No analysis data found matching your filters")
            return
        
        # Convert to DataFrame for easier handling
        df_data = []
        for result in results:
            # Extract data from raw_data JSON
            raw_data = result.raw_data or {}
            final_rec = raw_data.get('final_recommendation', {})
            
            # Calculate upside potential (skip for now to improve performance)
            upside_potential = 0
            # current_price = self.get_current_price(result.ticker)
            # if current_price and result.target_price and current_price > 0:
            #     upside_potential = ((result.target_price - current_price) / current_price) * 100
            
            # Determine exchange
            exchange = self.db_service._determine_exchange_from_ticker(result.ticker)
            
            df_data.append({
                'ticker': result.ticker,
                'exchange': exchange,
                'final_recommendation': result.recommendation,
                'target_price': result.target_price,
                'upside_potential': upside_potential,
                'confidence': result.confidence,
                'quality_grade': raw_data.get('company_type', 'N/A'),  # Using company_type as quality indicator
                'analysis_date': result.analysis_date
            })
        
        df = pd.DataFrame(df_data)
        
        # Summary metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📊 Filtered Results", len(df))
        
        with col2:
            strong_buy_count = len(df[df['final_recommendation'] == 'Strong Buy'])
            st.metric("🚀 Strong Buy", strong_buy_count)
        
        with col3:
            buy_count = len(df[df['final_recommendation'] == 'Buy'])
            st.metric("📈 Buy", buy_count)
        
        with col4:
            avg_upside = df['upside_potential'].mean() if not df.empty else 0
            st.metric("📊 Avg Upside", f"{avg_upside:.1f}%")
        
        with col5:
            latest_date = df['analysis_date'].max() if not df.empty else None
            if latest_date and hasattr(latest_date, 'strftime'):
                date_str = latest_date.strftime('%Y-%m-%d')
            else:
                date_str = "N/A"
            st.metric("📅 Latest Analysis", date_str)
        
        # Charts row
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Recommendation distribution
            rec_counts = df['final_recommendation'].value_counts()
            colors = {
                'Strong Buy': '#00ff00',
                'Buy': '#90ee90', 
                'Hold': '#ffff00',
                'Sell': '#ffa500',
                'Strong Sell': '#ff0000'
            }
            fig_pie = px.pie(
                values=rec_counts.values, 
                names=rec_counts.index,
                title="Recommendation Distribution",
                color=rec_counts.index,
                color_discrete_map=colors
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Exchange distribution
            if 'exchange' in df.columns:
                exchange_counts = df['exchange'].value_counts()
                fig_bar = px.bar(
                    x=exchange_counts.index, 
                    y=exchange_counts.values,
                    title="Stocks by Exchange",
                    color=exchange_counts.values,
                    color_continuous_scale="viridis"
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        with col3:
            # Upside distribution
            fig_hist = px.histogram(
                df, 
                x='upside_potential',
                title="Upside Potential Distribution",
                nbins=20,
                color_discrete_sequence=['#1f77b4']
            )
            fig_hist.update_layout(xaxis_title="Upside Potential (%)")
            st.plotly_chart(fig_hist, use_container_width=True)
        
        # Main data table
        st.subheader("📋 Analysis Results")
        
        # Prepare display data
        display_cols = [
            'ticker', 'exchange', 'final_recommendation', 'target_price', 
            'upside_potential', 'confidence', 'quality_grade', 'analysis_date'
        ]
        
        display_df = df[display_cols].copy()
        display_df['analysis_date'] = pd.to_datetime(display_df['analysis_date']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['target_price'] = display_df['target_price'].round(2)
        display_df['upside_potential'] = display_df['upside_potential'].round(1)
        
        # Rename columns for better display
        display_df.columns = [
            'Ticker', 'Exchange', 'Recommendation', 'Target Price', 
            'Upside %', 'Confidence', 'Quality', 'Analysis Date'
        ]
        
        # Color coding function
        def highlight_recommendations(row):
            colors = {
                'Strong Buy': 'background-color: #d4edda; color: #155724',
                'Buy': 'background-color: #d1ecf1; color: #0c5460',
                'Hold': 'background-color: #fff3cd; color: #856404',
                'Sell': 'background-color: #f8d7da; color: #721c24',
                'Strong Sell': 'background-color: #f5c6cb; color: #721c24'
            }
            
            rec = row['Recommendation']
            style = colors.get(rec, '')
            return [style if col == 'Recommendation' else '' for col in row.index]
        
        styled_df = display_df.style.apply(highlight_recommendations, axis=1)
        
        # Add sorting and pagination
        sort_by = st.selectbox(
            "Sort by:", 
            ['Upside %', 'Target Price', 'Analysis Date', 'Ticker'],
            index=0
        )
        
        sort_ascending = st.checkbox("Ascending", value=False)
        
        # Sort dataframe
        sort_col_map = {
            'Upside %': 'upside_potential',
            'Target Price': 'target_price', 
            'Analysis Date': 'analysis_date',
            'Ticker': 'ticker'
        }
        
        if sort_by in sort_col_map:
            df_sorted = df.sort_values(sort_col_map[sort_by], ascending=sort_ascending)
            display_df_sorted = display_df.loc[df_sorted.index]
            styled_df = display_df_sorted.style.apply(highlight_recommendations, axis=1)
        
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        # Individual stock analysis
        st.subheader("🔍 Individual Stock Analysis")
        
        if not df.empty:
            # Stock selection with search
            ticker_options = sorted(df['ticker'].unique())
            selected_ticker = st.selectbox(
                "Select Stock for Detailed View:", 
                ticker_options,
                help="Choose a stock to see historical price vs target analysis"
            )
            
            if selected_ticker:
                self.render_stock_detail(selected_ticker)
    
    def render_stock_detail(self, ticker):
        """Render detailed view for a specific stock"""
        st.markdown(f"### 📈 {ticker} - Historical Analysis")
        
        # Get historical analysis
        db = SessionLocal()
        try:
            hist_results = self.db_service.get_analysis_history(db, ticker, limit=10)
        finally:
            db.close()
        
        if not hist_results:
            st.warning(f"No historical analysis found for {ticker}")
            return
        
        # Get current stock info from latest analysis
        latest_analysis = hist_results[0]
        raw_data = latest_analysis.raw_data or {}
        final_rec = raw_data.get('final_recommendation', {})
        
        # Display current metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Recommendation", latest_analysis.recommendation)
        
        with col2:
            st.metric("Target Price", f"${latest_analysis.target_price:.2f}")
        
        with col3:
            current_price = self.get_current_price(ticker)
            if current_price and latest_analysis.target_price:
                upside = ((latest_analysis.target_price - current_price) / current_price) * 100
                st.metric("Upside Potential", f"{upside:.1f}%")
            else:
                st.metric("Upside Potential", "N/A")
        
        with col4:
            st.metric("Confidence", latest_analysis.confidence)
        
        # Get price data
        try:
            price_data = self.get_price_data(ticker, period="1y")
        except:
            price_data = pd.DataFrame()
        
        if not price_data.empty and len(hist_results) > 1:
            # Create price vs target chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(
                    f'{ticker} - Price vs Target Price History', 
                    'Recommendation Timeline'
                ),
                vertical_spacing=0.15,
                row_heights=[0.75, 0.25]
            )
            
            # Price chart
            fig.add_trace(
                go.Scatter(
                    x=price_data.index,
                    y=price_data['Close'],
                    name='Stock Price',
                    line=dict(color='#1f77b4', width=2),
                    hovertemplate='Date: %{x}<br>Price: $%{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Target prices from historical analysis
            dates = [result.analysis_date for result in hist_results]
            targets = [result.target_price for result in hist_results]
            
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=targets,
                    name='Target Price',
                    mode='markers+lines',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    marker=dict(size=8, color='#ff7f0e'),
                    hovertemplate='Date: %{x}<br>Target: $%{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # Recommendation timeline
            rec_colors = {
                'Strong Buy': '#00ff00',
                'Buy': '#90ee90', 
                'Hold': '#ffff00',
                'Sell': '#ffa500',
                'Strong Sell': '#ff0000'
            }
            
            for result in hist_results:
                color = rec_colors.get(result.recommendation, '#gray')
                fig.add_trace(
                    go.Scatter(
                        x=[result.analysis_date],
                        y=[1],
                        mode='markers',
                        marker=dict(size=15, color=color, line=dict(width=2, color='white')),
                        name=result.recommendation,
                        showlegend=False,
                        hovertemplate=f"Date: {result.analysis_date.strftime('%Y-%m-%d')}<br>Recommendation: {result.recommendation}<br>Confidence: {result.confidence}<br>Target: ${result.target_price:.2f}<extra></extra>"
                    ),
                    row=2, col=1
                )
            
            fig.update_layout(
                height=700,
                title=f"{ticker} - Comprehensive Analysis History",
                showlegend=True
            )
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="Price ($)", row=1, col=1)
            fig.update_yaxes(showticklabels=False, title_text="", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Analysis history table
        st.subheader("📋 Complete Analysis History")
        
        hist_display_data = []
        for result in hist_results:
            hist_display_data.append({
                'Analysis Date': result.analysis_date.strftime('%Y-%m-%d %H:%M'),
                'Recommendation': result.recommendation,
                'Target Price': f"${result.target_price:.2f}",
                'Confidence': result.confidence,
                'Analysis Type': result.analysis_type
            })
        
        hist_df = pd.DataFrame(hist_display_data)
        st.dataframe(hist_df, use_container_width=True)
    
    def get_price_data(self, ticker, period="1y"):
        """Get historical price data with error handling"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            if hist.empty:
                # Try without suffix for ASX stocks
                if ticker.endswith('.ax'):
                    alt_ticker = ticker[:-3]
                    stock = yf.Ticker(alt_ticker)
                    hist = stock.history(period=period)
            return hist
        except Exception as e:
            st.warning(f"Could not fetch price data for {ticker}: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, ticker):
        """Get current stock price with error handling"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            # Try without suffix for ASX stocks
            if ticker.endswith('.ax'):
                alt_ticker = ticker[:-3]
                stock = yf.Ticker(alt_ticker)
                hist = stock.history(period="1d")
                if not hist.empty:
                    return float(hist['Close'].iloc[-1])
        except:
            pass
        return None

def main():
    st.set_page_config(
        page_title="Stock Analysis Database",
        page_icon="📊",
        layout="wide"
    )
    
    dashboard = EnhancedDatabaseDashboard()
    dashboard.render_main_dashboard()

if __name__ == "__main__":
    main()
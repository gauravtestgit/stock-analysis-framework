import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict

class ExchangeMetrics:
    """Component for displaying exchange-specific metrics and charts"""
    
    @staticmethod
    def display_summary_metrics(data: Dict[str, pd.DataFrame]):
        """Display summary metrics across all exchanges"""
        col1, col2, col3, col4 = st.columns(4)
        
        total_stocks = sum(len(df) for df in data.values())
        total_buy_recs = sum(len(df[df['Final_Recommendation'].isin(['Buy', 'Strong Buy'])]) for df in data.values())
        
        # Calculate average upside across all exchanges
        all_data = pd.concat(data.values(), ignore_index=True)
        avg_upside = ((all_data['DCF_Price'] / all_data['Current_Price'] - 1) * 100).mean()
        
        # Count high quality stocks (A and B grades)
        high_quality = len(all_data[all_data['Quality_Grade'].isin(['A', 'B'])])
        
        with col1:
            st.metric("📊 Total Stocks", f"{total_stocks:,}")
        
        with col2:
            st.metric("🎯 Buy Recommendations", f"{total_buy_recs:,}")
        
        with col3:
            st.metric("📈 Avg DCF Upside", f"{avg_upside:.1f}%")
        
        with col4:
            st.metric("⭐ High Quality (A/B)", f"{high_quality:,}")
    
    @staticmethod
    def display_exchange_breakdown(data: Dict[str, pd.DataFrame]):
        """Display breakdown by exchange"""
        st.subheader("📊 Exchange Breakdown")
        
        exchange_stats = []
        for exchange, df in data.items():
            buy_count = len(df[df['Final_Recommendation'].isin(['Buy', 'Strong Buy'])])
            avg_price = df['Current_Price'].mean()
            high_quality = len(df[df['Quality_Grade'].isin(['A', 'B'])])
            
            exchange_stats.append({
                'Exchange': exchange,
                'Total Stocks': len(df),
                'Buy Recommendations': buy_count,
                'Buy %': f"{(buy_count/len(df)*100):.1f}%" if len(df) > 0 else "0%",
                'Avg Price': f"${avg_price:.2f}",
                'High Quality': high_quality,
                'Quality %': f"{(high_quality/len(df)*100):.1f}%" if len(df) > 0 else "0%"
            })
        
        stats_df = pd.DataFrame(exchange_stats)
        st.dataframe(stats_df, use_container_width=True)
    
    @staticmethod
    def display_recommendation_charts(data: Dict[str, pd.DataFrame]):
        """Display recommendation distribution charts"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Recommendation Distribution")
            
            # Combine all data for overall distribution
            all_data = pd.concat(data.values(), ignore_index=True)
            rec_counts = all_data['Final_Recommendation'].value_counts()
            
            fig_pie = px.pie(
                values=rec_counts.values,
                names=rec_counts.index,
                title="Overall Recommendation Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            st.subheader("🏭 Top Sectors")
            
            sector_counts = all_data['Sector'].value_counts().head(10)
            fig_bar = px.bar(
                x=sector_counts.values,
                y=sector_counts.index,
                orientation='h',
                title="Top 10 Sectors by Stock Count"
            )
            fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
    
    @staticmethod
    def display_quality_analysis(data: Dict[str, pd.DataFrame]):
        """Display quality grade analysis"""
        st.subheader("⭐ Quality Grade Analysis")
        
        all_data = pd.concat(data.values(), ignore_index=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Quality grade distribution
            quality_counts = all_data['Quality_Grade'].value_counts()
            fig_quality = px.bar(
                x=quality_counts.index,
                y=quality_counts.values,
                title="Quality Grade Distribution",
                labels={'x': 'Quality Grade', 'y': 'Count'}
            )
            st.plotly_chart(fig_quality, use_container_width=True)
        
        with col2:
            # Quality vs Recommendation
            quality_rec = pd.crosstab(all_data['Quality_Grade'], all_data['Final_Recommendation'])
            fig_heatmap = px.imshow(
                quality_rec.values,
                x=quality_rec.columns,
                y=quality_rec.index,
                title="Quality Grade vs Recommendation",
                aspect="auto"
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
    
    @staticmethod
    def display_price_analysis(data: Dict[str, pd.DataFrame]):
        """Display price analysis charts"""
        st.subheader("💰 Price Analysis")
        
        all_data = pd.concat(data.values(), ignore_index=True)
        
        # Calculate upside for different methods
        all_data['DCF_Upside'] = (all_data['DCF_Price'] / all_data['Current_Price'] - 1) * 100
        all_data['Technical_Upside'] = (all_data['Technical_Price'] / all_data['Current_Price'] - 1) * 100
        all_data['Analyst_Upside'] = (all_data['Analyst_Price'] / all_data['Current_Price'] - 1) * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Upside distribution
            fig_hist = px.histogram(
                all_data,
                x='DCF_Upside',
                nbins=50,
                title="DCF Upside Distribution",
                labels={'DCF_Upside': 'DCF Upside (%)', 'count': 'Number of Stocks'}
            )
            fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Price vs Quality scatter
            fig_scatter = px.scatter(
                all_data[all_data['Quality_Grade'].isin(['A', 'B', 'C', 'D'])],
                x='Current_Price',
                y='DCF_Upside',
                color='Quality_Grade',
                title="Price vs DCF Upside by Quality",
                labels={'Current_Price': 'Current Price ($)', 'DCF_Upside': 'DCF Upside (%)'}
            )
            fig_scatter.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_scatter, use_container_width=True)
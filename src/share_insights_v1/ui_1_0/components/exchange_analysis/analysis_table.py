import streamlit as st
import pandas as pd
from typing import Dict, List

class AnalysisTable:
    """Component for displaying analysis data in tabular format"""
    
    @staticmethod
    def display_data_table(data: Dict[str, pd.DataFrame], filtered_data: pd.DataFrame):
        """Display the main analysis data table"""
        st.subheader("📋 Analysis Results")
        
        if filtered_data.empty:
            st.warning("No data matches the current filters.")
            return
        
        # Display count
        st.write(f"Showing {len(filtered_data):,} stocks")
        
        # Column selection
        available_columns = [
            'Ticker', 'Exchange', 'Current_Price', 'DCF_Price', 'Technical_Price',
            'Comparable_Price', 'Analyst_Price', 'Final_Recommendation', 
            'Professional_Analyst_Recommendation', 'Analyst_Count',
            'Company_Type', 'Sector', 'Industry', 'Quality_Grade'
        ]
        
        # Filter available columns based on what exists in data
        existing_columns = [col for col in available_columns if col in filtered_data.columns]
        
        selected_columns = st.multiselect(
            "Select columns to display:",
            existing_columns,
            default=['Ticker', 'Exchange', 'Current_Price', 'Final_Recommendation', 
                    'Sector', 'Quality_Grade'],
            key="table_columns"
        )
        
        if not selected_columns:
            st.warning("Please select at least one column to display.")
            return
        
        # Display table
        display_df = filtered_data[selected_columns].copy()
        
        # Format price columns
        price_columns = ['Current_Price', 'DCF_Price', 'Technical_Price', 
                        'Comparable_Price', 'Analyst_Price']
        
        for col in price_columns:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"${x:.2f}" if pd.notnull(x) and x != 0 else "-")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600
        )
    
    @staticmethod
    def display_top_picks(filtered_data: pd.DataFrame):
        """Display top stock picks based on different criteria"""
        st.subheader("🌟 Top Picks")
        
        if filtered_data.empty:
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**🎯 Strong Buy Recommendations**")
            strong_buys = filtered_data[
                filtered_data['Final_Recommendation'] == 'Strong Buy'
            ].head(5)
            
            if not strong_buys.empty:
                for _, stock in strong_buys.iterrows():
                    st.write(f"• **{stock['Ticker']}** ({stock['Exchange']}) - ${stock['Current_Price']:.2f}")
            else:
                st.write("No Strong Buy recommendations found")
        
        with col2:
            st.write("**⭐ High Quality Stocks (Grade A)**")
            high_quality = filtered_data[
                filtered_data['Quality_Grade'] == 'A'
            ].head(5)
            
            if not high_quality.empty:
                for _, stock in high_quality.iterrows():
                    st.write(f"• **{stock['Ticker']}** ({stock['Exchange']}) - {stock['Sector']}")
            else:
                st.write("No Grade A stocks found")
        
        with col3:
            st.write("**📈 Highest DCF Upside**")
            # Calculate upside and filter out invalid values
            upside_data = filtered_data.copy()
            upside_data['DCF_Upside'] = (upside_data['DCF_Price'] / upside_data['Current_Price'] - 1) * 100
            
            # Filter for reasonable upside values (between -50% and 200%)
            reasonable_upside = upside_data[
                (upside_data['DCF_Upside'] >= -50) & 
                (upside_data['DCF_Upside'] <= 200) &
                (upside_data['DCF_Price'] > 0)
            ].nlargest(5, 'DCF_Upside')
            
            if not reasonable_upside.empty:
                for _, stock in reasonable_upside.iterrows():
                    st.write(f"• **{stock['Ticker']}** ({stock['Exchange']}) - {stock['DCF_Upside']:.1f}%")
            else:
                st.write("No valid DCF upside data found")
    
    @staticmethod
    def display_summary_stats(filtered_data: pd.DataFrame):
        """Display summary statistics for filtered data"""
        if filtered_data.empty:
            return
        
        st.subheader("📊 Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            buy_count = len(filtered_data[filtered_data['Final_Recommendation'].isin(['Buy', 'Strong Buy'])])
            st.metric("Buy Recommendations", f"{buy_count:,}")
        
        with col2:
            avg_price = filtered_data['Current_Price'].mean()
            st.metric("Average Price", f"${avg_price:.2f}")
        
        with col3:
            high_quality_count = len(filtered_data[filtered_data['Quality_Grade'].isin(['A', 'B'])])
            st.metric("High Quality (A/B)", f"{high_quality_count:,}")
        
        with col4:
            avg_analysts = filtered_data['Analyst_Count'].mean()
            st.metric("Avg Analyst Coverage", f"{avg_analysts:.1f}")
    
    @staticmethod
    def export_data(filtered_data: pd.DataFrame):
        """Provide data export functionality"""
        if filtered_data.empty:
            return
        
        st.subheader("📥 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV export
            csv = filtered_data.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"stock_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Show data info
            st.write(f"**Data Summary:**")
            st.write(f"• {len(filtered_data):,} stocks")
            st.write(f"• {filtered_data['Exchange'].nunique()} exchanges")
            st.write(f"• {filtered_data['Sector'].nunique()} sectors")
import streamlit as st
import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.share_insights_v1.services.database.database_service import DatabaseService
from src.share_insights_v1.models.database import SessionLocal
from src.share_insights_v1.dashboard.login_page import check_authentication, render_navigation

class StockManagementDashboard:
    def __init__(self):
        self.db_service = DatabaseService()
    
    def render_main_dashboard(self):
        """Render the stock management dashboard"""
        # Check authentication
        if not check_authentication():
            st.switch_page("run_login.py")
            return
        
        # Check admin role
        if st.session_state.get("user_role") != "admin":
            st.error("🚫 Access Denied: Admin role required")
            st.info("Please contact your administrator for access to stock management.")
            return
        
        # Navigation bar
        render_navigation()
        
        st.title("📊 Stock Information Management")
        st.markdown("*Manage stock symbols, security names, and exchange information*")
        
        # Tabs for different operations
        tab1, tab2, tab3 = st.tabs(["📋 View Stocks", "📤 Upload CSV", "➕ Add Stock"])
        
        with tab1:
            self.render_view_stocks()
        
        with tab2:
            self.render_upload_csv()
        
        with tab3:
            self.render_add_stock()
    
    def render_view_stocks(self):
        """Render the view stocks tab"""
        st.subheader("📋 Current Stock Information")
        
        # Load stocks from database
        db = SessionLocal()
        try:
            stocks = self.db_service.get_all_stocks(db)
        finally:
            db.close()
        
        if not stocks:
            st.warning("No stocks found in database. Upload a CSV file to add stocks.")
            return
        
        # Convert to DataFrame
        df_data = []
        for stock in stocks:
            df_data.append({
                'Symbol': stock.symbol,
                'Security Name': stock.security_name,
                'Exchange': stock.exchange,
                'Created': stock.created_at.strftime('%Y-%m-%d'),
                'Updated': stock.updated_at.strftime('%Y-%m-%d')
            })
        
        df = pd.DataFrame(df_data)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total Stocks", len(df))
        
        with col2:
            exchange_counts = df['Exchange'].value_counts()
            most_common = exchange_counts.index[0] if not exchange_counts.empty else "N/A"
            st.metric("🏆 Top Exchange", most_common)
        
        with col3:
            st.metric("🔄 Exchanges", len(df['Exchange'].unique()))
        
        with col4:
            latest_update = df['Updated'].max() if not df.empty else "N/A"
            st.metric("📅 Latest Update", latest_update)
        
        # Filters
        col1, col2 = st.columns(2)
        
        with col1:
            exchanges = ["All"] + sorted(df['Exchange'].unique().tolist())
            selected_exchange = st.selectbox("Filter by Exchange", exchanges)
        
        with col2:
            search_term = st.text_input("Search Symbol/Name", placeholder="Enter symbol or company name...")
        
        # Apply filters
        filtered_df = df.copy()
        
        if selected_exchange != "All":
            filtered_df = filtered_df[filtered_df['Exchange'] == selected_exchange]
        
        if search_term:
            mask = (
                filtered_df['Symbol'].str.contains(search_term, case=False, na=False) |
                filtered_df['Security Name'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[mask]
        
        # Display results
        st.dataframe(filtered_df, use_container_width=True, height=400)
        
        # Exchange distribution chart
        if not df.empty:
            st.subheader("📊 Exchange Distribution")
            exchange_counts = df['Exchange'].value_counts()
            st.bar_chart(exchange_counts)
    
    def render_upload_csv(self):
        """Render the CSV upload tab"""
        st.subheader("📤 Upload Stock Information CSV")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type="csv",
            help="CSV should have columns: Symbol, Security Name, and optionally Exchange"
        )
        
        if uploaded_file is not None:
            try:
                # Read CSV
                df = pd.read_csv(uploaded_file)
                
                # Display preview
                st.subheader("📋 File Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Validate columns
                required_cols = ['Symbol', 'Security Name']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    st.error(f"Missing required columns: {', '.join(missing_cols)}")
                    st.info("Required columns: Symbol, Security Name")
                    return
                
                # Exchange handling
                if 'Exchange' not in df.columns:
                    st.warning("No Exchange column found. Please specify the exchange:")
                    exchange_options = ['NASDAQ', 'NYSE', 'ASX', 'NZX', 'Other']
                    default_exchange = st.selectbox("Default Exchange", exchange_options)
                    df['Exchange'] = default_exchange
                
                # Clean data
                df = df.dropna(subset=['Symbol', 'Security Name'])
                df['Symbol'] = df['Symbol'].str.strip().str.upper()
                df['Security Name'] = df['Security Name'].str.strip()
                df['Exchange'] = df['Exchange'].str.strip().str.upper()
                
                # Show summary
                st.subheader("📊 Upload Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Records", len(df))
                
                with col2:
                    st.metric("Unique Symbols", df['Symbol'].nunique())
                
                with col3:
                    st.metric("Exchanges", df['Exchange'].nunique())
                
                # Upload button
                if st.button("🚀 Upload to Database", type="primary"):
                    with st.spinner("Uploading stocks to database..."):
                        # Prepare data
                        stocks_data = []
                        for _, row in df.iterrows():
                            stocks_data.append({
                                'symbol': row['Symbol'],
                                'security_name': row['Security Name'],
                                'exchange': row['Exchange']
                            })
                        
                        # Upload to database
                        db = SessionLocal()
                        try:
                            count = self.db_service.bulk_upsert_stocks(db, stocks_data)
                            st.success(f"✅ Successfully uploaded {count} stocks to database!")
                            st.info("💡 Refresh the 'View Stocks' tab to see updated data")
                        except Exception as e:
                            st.error(f"❌ Error uploading stocks: {str(e)}")
                        finally:
                            db.close()
                
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")
    
    def render_add_stock(self):
        """Render the add single stock tab"""
        st.subheader("➕ Add Single Stock")
        
        with st.form("add_stock_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                symbol = st.text_input("Stock Symbol", placeholder="e.g., AAPL", help="Stock ticker symbol")
                exchange = st.selectbox("Exchange", ['NASDAQ', 'NYSE', 'ASX', 'NZX', 'Other'])
            
            with col2:
                security_name = st.text_input("Security Name", placeholder="e.g., Apple Inc.", help="Full company name")
            
            submitted = st.form_submit_button("Add Stock", type="primary")
            
            if submitted:
                if not symbol or not security_name:
                    st.error("Please fill in all required fields")
                else:
                    # Clean inputs
                    symbol = symbol.strip().upper()
                    security_name = security_name.strip()
                    
                    # Add to database
                    db = SessionLocal()
                    try:
                        stock = self.db_service.upsert_stock(db, symbol, security_name, exchange)
                        st.success(f"✅ Successfully added {symbol} - {security_name}")
                    except Exception as e:
                        st.error(f"❌ Error adding stock: {str(e)}")
                    finally:
                        db.close()

def main():
    st.set_page_config(
        page_title="Stock Management",
        page_icon="📊",
        layout="wide"
    )
    
    dashboard = StockManagementDashboard()
    dashboard.render_main_dashboard()

if __name__ == "__main__":
    main()
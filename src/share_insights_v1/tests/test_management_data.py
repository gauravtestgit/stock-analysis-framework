#!/usr/bin/env python3

from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider

def test_management_data_retrieval():
    """Test management data retrieval from both providers"""
    
    print("Testing Management Data Retrieval...")
    
    # Initialize providers
    yahoo_provider = YahooFinanceProvider()
    sec_provider = SECEdgarProvider()
    
    # Test companies
    test_tickers = ["MSFT", "AAPL", "GOOGL"]
    
    for ticker in test_tickers:
        print(f"\n{'='*60}")
        print(f"Management Data Test: {ticker}")
        print(f"{'='*60}")
        
        # Test SEC EDGAR first (priority)
        print(f"\n--- SEC EDGAR Data ---")
        sec_data = sec_provider.get_management_data(ticker)
        
        if 'error' not in sec_data:
            print(f"[SUCCESS] SEC data retrieved for {ticker}")
            mgmt_metrics = sec_data.get('management_metrics', {})
            print(f"Proxy filings found: {mgmt_metrics.get('proxy_filings_found', 0)}")
            print(f"Latest proxy date: {mgmt_metrics.get('latest_proxy_date', 'N/A')}")
            print(f"Executive compensation disclosed: {mgmt_metrics.get('executive_compensation_disclosed', False)}")
        else:
            print(f"[ERROR] SEC EDGAR: {sec_data['error']}")
        
        # Test Yahoo Finance as fallback
        print(f"\n--- Yahoo Finance Data ---")
        yahoo_data = yahoo_provider.get_management_data(ticker)
        
        if 'error' not in yahoo_data:
            print(f"[SUCCESS] Yahoo data retrieved for {ticker}")
            mgmt_data = yahoo_data.get('management_data', {})
            officers = yahoo_data.get('officers_summary', [])
            
            print(f"Company officers found: {len(officers)}")
            print(f"Insider ownership: {mgmt_data.get('held_percent_insiders', 'N/A')}")
            print(f"Institutional ownership: {mgmt_data.get('held_percent_institutions', 'N/A')}")
            print(f"Compensation risk: {mgmt_data.get('compensation_risk', 'N/A')}")
            print(f"Overall governance risk: {mgmt_data.get('overall_risk', 'N/A')}")
            
            # Show top officers
            if officers:
                print(f"\nTop Officers:")
                for officer in officers[:3]:
                    name = officer.get('name', 'N/A')
                    title = officer.get('title', 'N/A')
                    total_pay = officer.get('total_pay')
                    pay_str = f"${total_pay:,.0f}" if total_pay else "N/A"
                    print(f"  {name} - {title} (Pay: {pay_str})")
        else:
            print(f"[ERROR] Yahoo Finance: {yahoo_data['error']}")

if __name__ == "__main__":
    test_management_data_retrieval()
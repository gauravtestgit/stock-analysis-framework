#!/usr/bin/env python3

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
from share_insights_v1.implementations.data_providers.yahoo_peer_provider import YahooPeerProvider
from share_insights_v1.implementations.analyzers.peer_comparison_analyzer import PeerComparisonAnalyzer

def test_peer_comparison():
    """Test peer comparison analysis"""
    
    print("Testing Peer Comparison Analysis...")
    
    # Initialize providers
    data_provider = YahooFinanceProvider()
    peer_provider = YahooPeerProvider()
    analyzer = PeerComparisonAnalyzer(peer_provider, data_provider)
    
    # Test stocks with different industries
    test_cases = [
        ("AAPL", "Technology", "Consumer Electronics"),
        ("MSFT", "Technology", "Software - Application"),
        ("TSLA", "Consumer Cyclical", "Auto Manufacturers")
    ]
    
    for ticker, sector, industry in test_cases:
        print(f"\n{'='*60}")
        print(f"Peer Analysis: {ticker} ({industry})")
        print(f"{'='*60}")
        
        try:
            comparison = analyzer.analyze_peer_comparison(ticker, sector, industry)
            
            if comparison:
                print(f"Target: {comparison.target_ticker}")
                print(f"Peers: {', '.join(comparison.peer_tickers)}")
                print(f"Valuation Summary: {comparison.valuation_summary}")
                
                # Show target metrics
                target = comparison.target_metrics
                print(f"\nTarget Metrics:")
                if target.pe_ratio:
                    print(f"  P/E Ratio: {target.pe_ratio:.1f}")
                if target.ev_ebitda:
                    print(f"  EV/EBITDA: {target.ev_ebitda:.1f}")
                if target.price_to_sales:
                    print(f"  P/S Ratio: {target.price_to_sales:.1f}")
                if target.roe:
                    print(f"  ROE: {target.roe:.1%}")
                if target.revenue_growth:
                    print(f"  Revenue Growth: {target.revenue_growth:.1%}")
                
                # Show relative position
                print(f"\nRelative Position vs Peers:")
                for metric, position in comparison.relative_position.items():
                    print(f"  {metric.replace('_', ' ').title()}: {position.value}")
                
                # Show insights
                if comparison.key_insights:
                    print(f"\nKey Insights:")
                    for insight in comparison.key_insights:
                        print(f"  • {insight}")
                
                # Show peer comparison
                print(f"\nPeer Metrics:")
                for peer in comparison.peer_metrics[:3]:  # Show top 3 peers
                    print(f"  {peer.ticker}:")
                    if peer.pe_ratio:
                        print(f"    P/E: {peer.pe_ratio:.1f}")
                    if peer.ev_ebitda:
                        print(f"    EV/EBITDA: {peer.ev_ebitda:.1f}")
                    if peer.roe:
                        print(f"    ROE: {peer.roe:.1%}")
            
            else:
                print(f"✗ Could not analyze peer comparison for {ticker}")
                
        except Exception as e:
            print(f"✗ Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_peer_comparison()
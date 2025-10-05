#!/usr/bin/env python3

import sys
import os

from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.classifier import CompanyClassifier
from ..config.config import FinanceConfig

def test_enhanced_comparable():
    """Test enhanced comparable analyzer with peer data"""
    
    print("Testing Enhanced Comparable Analysis...")
    
    # Initialize components
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    config = FinanceConfig()
    analyzer = ComparableAnalyzer(config, data_provider)
    
    # Test stocks
    test_tickers = ["AAPL", "MSFT", "TSLA"]
    
    for ticker in test_tickers:
        print(f"\n{'='*60}")
        print(f"Enhanced Comparable Analysis: {ticker}")
        print(f"{'='*60}")
        
        try:
            # Get data
            financial_data = data_provider.get_financial_data(ticker)
            company_info = data_provider.get_company_info(ticker)
            
            if not financial_data or not company_info:
                print(f"✗ Could not get data for {ticker}")
                continue
            
            # Classify company
            company_type = classifier.classify_company(financial_data, company_info)
            
            # Prepare analysis data
            analysis_data = {
                'financial_metrics': financial_data,
                'company_info': company_info,
                'company_type': company_type,
                'quality_grade': 'B'  # Mock grade
            }
            
            # Run analysis
            result = analyzer.analyze(ticker, analysis_data)
            
            if 'error' in result:
                print(f"✗ Error: {result['error']}")
                continue
            
            print(f"✓ Analysis completed for {ticker}")
            print(f"Sector: {result.get('sector', 'N/A')}")
            print(f"Industry: {result.get('industry', 'N/A')}")
            print(f"Predicted Price: ${result.get('predicted_price', 0):.2f}")
            print(f"Current Price: ${result.get('current_price', 0):.2f}")
            print(f"Upside/Downside: {result.get('upside_downside_pct', 0):.1f}%")
            print(f"Recommendation: {result.get('recommendation', 'N/A')}")
            
            # Show peer analysis if available
            if 'peer_tickers' in result:
                print(f"\nPeer Analysis:")
                print(f"Peers: {', '.join(result['peer_tickers'])}")
                
                # Show relative position
                if 'relative_position' in result:
                    print(f"Relative Position vs Peers:")
                    for metric, position in result['relative_position'].items():
                        print(f"  {metric.replace('_', ' ').title()}: {position}")
                
                # Show peer insights
                if 'peer_insights' in result:
                    print(f"Peer Insights:")
                    for insight in result['peer_insights']:
                        print(f"  • {insight}")
                
                # Show current vs peer averages
                if 'current_multiples' in result and 'peer_averages' in result:
                    current = result['current_multiples']
                    peer_avg = result['peer_averages']
                    
                    print(f"\nValuation Comparison:")
                    if current.get('pe_ratio') and peer_avg.get('pe_ratio'):
                        print(f"  P/E Ratio: {current['pe_ratio']:.1f} vs {peer_avg['pe_ratio']:.1f} (peer avg)")
                    if current.get('ps_ratio') and peer_avg.get('ps_ratio'):
                        print(f"  P/S Ratio: {current['ps_ratio']:.1f} vs {peer_avg['ps_ratio']:.1f} (peer avg)")
                    if current.get('ev_ebitda') and peer_avg.get('ev_ebitda'):
                        print(f"  EV/EBITDA: {current['ev_ebitda']:.1f} vs {peer_avg['ev_ebitda']:.1f} (peer avg)")
            
            else:
                print(f"\nNo peer data available for {ticker}")
                
        except Exception as e:
            print(f"✗ Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_enhanced_comparable()
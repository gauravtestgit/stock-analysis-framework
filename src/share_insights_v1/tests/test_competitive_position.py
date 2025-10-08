#!/usr/bin/env python3

from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.analyzers.competitive_position_analyzer import CompetitivePositionAnalyzer
from ..implementations.classifier import CompanyClassifier

def test_competitive_position_analysis():
    """Test competitive position analysis"""
    
    print("Testing Competitive Position Analysis...")
    
    # Initialize providers
    data_provider = YahooFinanceProvider()
    analyzer = CompetitivePositionAnalyzer(data_provider)
    
    # Test different company types across sectors
    test_cases = [
        ("MSFT", "Dominant Tech - Software Infrastructure"),
        ("AAPL", "Consumer Electronics - Manufacturing"),
        ("NFLX", "Entertainment - Streaming Platform"),
        ("JPM", "Financial Services - Diversified Bank"),
        ("JNJ", "Healthcare - Pharmaceuticals"),
        ("XOM", "Energy - Oil & Gas"),
        ("NEE", "Utilities - Electric Utility"),
        ("AMT", "Real Estate - REITs"),
        ("MCD", "Consumer Discretionary - Restaurants"),
        ("WMT", "Consumer Staples - Retail"),
        ("BA", "Industrials - Aerospace & Defense"),
        ("TSLA", "Automotive - Electric Vehicles"),
        ("UBER", "Technology - Ride Sharing Platform"),
        ("SNAP", "Communication - Social Media")
    ]
    
    for ticker, description in test_cases:
        print(f"\n{'='*60}")
        print(f"Competitive Position Analysis: {ticker} ({description})")
        print(f"{'='*60}")
        
        try:
            # Get data
            financial_data = data_provider.get_financial_metrics(ticker=ticker)
            company_info = {
                'sector': financial_data.get('sector', ''),
                'industry': financial_data.get('industry', ''),
            }
            company_classifier = CompanyClassifier()
            company_type = company_classifier.classify(ticker=ticker, metrics=financial_data)
            
            if not financial_data or not company_info:
                print(f"[ERROR] Could not get data for {ticker}")
                continue
            
            # Prepare analysis data
            analysis_data = {
                'financial_metrics': financial_data,
                'company_info': company_info,
                'company_type': company_type
            }
            
            print(f"Company Type: {company_type}")
            
            # Run analysis
            result = analyzer.analyze(ticker, analysis_data)
            
            if 'error' in result:
                print(f"[ERROR] Error: {result['error']}")
                continue
            
            print(f"[SUCCESS] Analysis completed for {ticker}")
            print(f"Overall Position Score: {result.get('overall_position_score', 0):.1f}/10")
            print(f"Competitive Strength: {result.get('competitive_strength', 'N/A')}")
            print(f"Market Share Estimate: {result.get('market_share_estimate', 0):.1%}")
            print(f"Position Trend: {result.get('position_trend', 'N/A')}")
            print(f"Recommendation: {result.get('recommendation', 'N/A')}")
            
            # Show key differentiators
            if result.get('key_differentiators'):
                print(f"\nKey Differentiators:")
                for diff in result['key_differentiators']:
                    print(f"  + {diff}")
            
            # Show competitive advantages
            if result.get('competitive_advantages'):
                print(f"\nCompetitive Advantages:")
                for adv in result['competitive_advantages']:
                    print(f"  + {adv}")
            
            # Show competitive threats
            if result.get('competitive_threats'):
                print(f"\nCompetitive Threats:")
                for threat in result['competitive_threats']:
                    print(f"  - {threat}")
            
            # Show strategic risks
            if result.get('strategic_risks'):
                print(f"\nStrategic Risks:")
                for risk in result['strategic_risks']:
                    print(f"  - {risk}")
            
        except Exception as e:
            print(f"[ERROR] Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_competitive_position_analysis()
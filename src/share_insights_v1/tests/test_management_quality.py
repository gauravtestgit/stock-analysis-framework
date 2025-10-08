#!/usr/bin/env python3

from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from ..implementations.analyzers.management_quality_analyzer import ManagementQualityAnalyzer
from ..implementations.classifier import CompanyClassifier

def test_management_quality_analysis():
    """Test management quality analysis"""
    
    print("Testing Management Quality Analysis...")
    
    # Initialize providers
    data_provider = YahooFinanceProvider()
    sec_provider = SECEdgarProvider()
    analyzer = ManagementQualityAnalyzer(data_provider, sec_provider)
    
    # Test companies
    test_cases = [
        ("MSFT", "Large Tech - Established Leadership"),
        ("AAPL", "Consumer Tech - Iconic Leadership"),
        ("TSLA", "Growth Tech - Visionary Leadership"),
        ("JPM", "Financial Services - Traditional Leadership"),
        ("JNJ", "Healthcare - Diversified Leadership")
    ]
    
    for ticker, description in test_cases:
        print(f"\n{'='*60}")
        print(f"Management Quality Analysis: {ticker} ({description})")
        print(f"{'='*60}")
        
        try:
            # Get financial data for context
            financial_data = data_provider.get_financial_metrics(ticker=ticker)
            company_info = {
                'sector': financial_data.get('sector', ''),
                'industry': financial_data.get('industry', ''),
            }
            company_classifier = CompanyClassifier()
            company_type = company_classifier.classify(ticker=ticker, metrics=financial_data)
            
            if not financial_data:
                print(f"[ERROR] Could not get financial data for {ticker}")
                continue
            
            # Prepare analysis data
            analysis_data = {
                'financial_metrics': financial_data,
                'company_info': company_info,
                'company_type': company_type
            }
            
            # Run analysis
            result = analyzer.analyze(ticker, analysis_data)
            
            if 'error' in result:
                print(f"[ERROR] Error: {result['error']}")
                continue
            
            print(f"[SUCCESS] Analysis completed for {ticker}")
            print(f"Overall Quality Score: {result.get('overall_quality_score', 0):.1f}/10")
            print(f"Management Quality: {result.get('management_quality', 'N/A')}")
            print(f"Governance Risk: {result.get('governance_risk', 'N/A')}")
            print(f"Executive Count: {result.get('executive_count', 0)}")
            
            insider_ownership = result.get('insider_ownership')
            if insider_ownership:
                print(f"Insider Ownership: {insider_ownership:.1%}")
            
            print(f"Recommendation: {result.get('recommendation', 'N/A')}")
            
            # Show strengths
            if result.get('strengths'):
                print(f"\nStrengths:")
                for strength in result['strengths']:
                    print(f"  + {strength}")
            
            # Show concerns
            if result.get('concerns'):
                print(f"\nConcerns:")
                for concern in result['concerns']:
                    print(f"  - {concern}")
            
            # Show key insights
            if result.get('key_insights'):
                print(f"\nKey Insights:")
                for insight in result['key_insights']:
                    print(f"  • {insight}")
            
        except Exception as e:
            print(f"[ERROR] Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_management_quality_analysis()
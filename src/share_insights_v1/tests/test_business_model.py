#!/usr/bin/env python3

import sys
import os



from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.classifier import CompanyClassifier

def test_business_model_analysis():
    """Test business model and revenue stream analysis"""
    
    print("Testing Business Model Analysis...")
    
    # Initialize providers
    data_provider = YahooFinanceProvider()
    sec_provider = SECEdgarProvider()
    analyzer = BusinessModelAnalyzer(data_provider, sec_provider)
    
    # Test different business model types
    test_cases = [
        ("MSFT", "B2B SaaS"),
        ("NFLX", "B2C Subscription"),
        ("AMZN", "Marketplace/Platform"),
        ("AAPL", "Manufacturing"),
        ("JPM", "Financial Services")
    ]
    
    for ticker, expected_model in test_cases:
        print(f"\n{'='*60}")
        print(f"Business Model Analysis: {ticker} (Expected: {expected_model})")
        print(f"{'='*60}")
        
        try:
            # Get data
            financial_data = data_provider.get_financial_metrics(ticker=ticker)
            company_info = {
            'sector': financial_data.get('sector', ''),
            'industry': financial_data.get('industry', ''),
        }
            

            
            company_classifier = CompanyClassifier()
            company_type = company_classifier.classify(ticker = ticker, metrics = financial_data)
            
            if not financial_data or not company_info:
                print(f"[ERROR] Could not get data for {ticker}")
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
            print(f"Business Model: {result.get('business_model_type', 'N/A')}")
            print(f"Primary Revenue Stream: {result.get('primary_revenue_stream', 'N/A')}")
            print(f"Revenue Quality: {result.get('revenue_quality', 'N/A')}")
            print(f"Scalability Score: {result.get('scalability_score', 0):.1f}/10")
            
            if result.get('recurring_percentage'):
                print(f"Recurring Revenue: {result['recurring_percentage']:.1%}")
            
            if result.get('growth_consistency'):
                print(f"Growth Consistency: {result['growth_consistency']:.2f} (lower is better)")
            
            print(f"Competitive Moat: {result.get('competitive_moat', 'N/A')}")
            print(f"Recommendation: {result.get('recommendation', 'N/A')}")
            
            # Show strengths and risks
            if result.get('strengths'):
                print(f"\nStrengths:")
                for strength in result['strengths']:
                    print(f"  + {strength}")
            
            if result.get('risks'):
                print(f"\nRisks:")
                for risk in result['risks']:
                    print(f"  - {risk}")
            
            # Test detailed analysis
            print(f"\n--- Detailed Business Model Report ---")
            detailed_report = analyzer.analyze_business_model(
                ticker, company_info, financial_data
            )
            
            if detailed_report:
                print(f"Revenue Stream Analysis:")
                rsa = detailed_report.revenue_stream_analysis
                print(f"  Primary Stream: {rsa.primary_stream.value}")
                if rsa.recurring_percentage:
                    print(f"  Recurring %: {rsa.recurring_percentage:.1%}")
                if rsa.growth_consistency:
                    print(f"  Growth Consistency: {rsa.growth_consistency:.2f}")
                
                print(f"Key Metrics:")
                for metric, value in detailed_report.key_metrics.items():
                    print(f"  {metric}: {value:.3f}")
                
        except Exception as e:
            print(f"[ERROR] Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_business_model_analysis()
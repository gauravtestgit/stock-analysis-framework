#!/usr/bin/env python3

import sys
import os

# Add src to path

from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from ..implementations.analyzers.financial_health_analyzer import FinancialHealthAnalyzer

def test_sec_financial_health():
    """Test SEC financial health analysis"""
    
    print("Testing SEC Financial Health Analysis...")
    
    # Initialize components
    sec_provider = SECEdgarProvider()
    analyzer = FinancialHealthAnalyzer(sec_provider)
    
    # Test stocks
    test_tickers = ["AAPL", "MSFT", "TSLA"]
    
    for ticker in test_tickers:
        print(f"\n{'='*50}")
        print(f"Analyzing {ticker}")
        print(f"{'='*50}")
        
        try:
            # Test IAnalyzer interface
            print("\n--- Testing IAnalyzer Interface ---")
            analysis_data = {'company_type': 'mature_profitable'}
            result = analyzer.analyze(ticker, analysis_data)
            
            if 'error' not in result:
                print(f"✓ IAnalyzer interface works for {ticker}")
                print(f"Method: {result.get('method', 'N/A')}")
                print(f"Overall Grade: {result.get('overall_grade', 'N/A')}")
                print(f"Recommendation: {result.get('recommendation', 'N/A')}")
                print(f"Cash Flow Score: {result.get('cash_flow_score', 'N/A')}")
                print(f"Debt Score: {result.get('debt_score', 'N/A')}")
                
                if result.get('strengths'):
                    print(f"Strengths: {', '.join(result['strengths'])}")
                if result.get('key_risks'):
                    print(f"Risks: {', '.join(result['key_risks'])}")
            else:
                print(f"✗ IAnalyzer interface error: {result['error']}")
            
            print("\n--- Testing Original Interface ---")
            
            # Test original detailed interface
            report = analyzer.analyze_financial_health(ticker)
            
            if report:
                print(f"✓ Original interface works for {ticker}")
                print(f"Filing Date: {report.filing_date}")
                print(f"Overall Grade: {report.overall_grade.value if report.overall_grade else 'N/A'}")
                
                # Cash flow metrics
                if report.cash_flow_metrics:
                    cf = report.cash_flow_metrics
                    print(f"\nCash Flow:")
                    if cf.operating_cash_flow:
                        print(f"  Operating CF: ${cf.operating_cash_flow:,.0f}")
                    if cf.free_cash_flow:
                        print(f"  Free CF: ${cf.free_cash_flow:,.0f}")
                    if cf.cash_conversion_ratio:
                        print(f"  Cash Conversion: {cf.cash_conversion_ratio:.2f}")
                
                # Debt metrics
                if report.debt_metrics:
                    debt = report.debt_metrics
                    print(f"\nDebt:")
                    if debt.total_debt:
                        print(f"  Total Debt: ${debt.total_debt:,.0f}")
                    if debt.debt_to_equity:
                        print(f"  D/E Ratio: {debt.debt_to_equity:.2f}")
                    if debt.interest_coverage:
                        print(f"  Interest Coverage: {debt.interest_coverage:.1f}x")
                
                # Revenue quality
                if report.revenue_quality and report.revenue_quality.revenue_growth_3yr:
                    print(f"\nRevenue Growth (3yr): {report.revenue_quality.revenue_growth_3yr:.1%}")
            
            else:
                print(f"✗ Original interface failed for {ticker}")
                
        except Exception as e:
            print(f"✗ Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_sec_financial_health()
#!/usr/bin/env python3

import sys
import os

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.append(project_root)

from src.share_insights_v1.implementations.data_providers.sec_edgar_provider import SECEdgarProvider
from src.share_insights_v1.implementations.analyzers.financial_health_analyzer import FinancialHealthAnalyzer

def test_financial_health_analysis():
    """Test financial health analysis with SEC data"""
    
    # Initialize providers
    sec_provider = SECEdgarProvider()
    health_analyzer = FinancialHealthAnalyzer(sec_provider)
    
    # Test with a well-known stock
    ticker = "AAPL"
    
    print(f"Analyzing financial health for {ticker}...")
    
    # Get financial health report
    health_report = health_analyzer.analyze_financial_health(ticker)
    
    if health_report:
        print(f"\n=== Financial Health Report for {ticker} ===")
        print(f"Filing Date: {health_report.filing_date}")
        print(f"Overall Grade: {health_report.overall_grade.value if health_report.overall_grade else 'N/A'}")
        
        if health_report.cash_flow_metrics:
            print(f"\nCash Flow Metrics:")
            print(f"  Operating Cash Flow: ${health_report.cash_flow_metrics.operating_cash_flow:,.0f}" if health_report.cash_flow_metrics.operating_cash_flow else "  Operating Cash Flow: N/A")
            print(f"  Free Cash Flow: ${health_report.cash_flow_metrics.free_cash_flow:,.0f}" if health_report.cash_flow_metrics.free_cash_flow else "  Free Cash Flow: N/A")
            print(f"  Cash Conversion Ratio: {health_report.cash_flow_metrics.cash_conversion_ratio:.2f}" if health_report.cash_flow_metrics.cash_conversion_ratio else "  Cash Conversion Ratio: N/A")
        
        if health_report.debt_metrics:
            print(f"\nDebt Metrics:")
            print(f"  Total Debt: ${health_report.debt_metrics.total_debt:,.0f}" if health_report.debt_metrics.total_debt else "  Total Debt: N/A")
            print(f"  Debt-to-Equity: {health_report.debt_metrics.debt_to_equity:.2f}" if health_report.debt_metrics.debt_to_equity else "  Debt-to-Equity: N/A")
            print(f"  Interest Coverage: {health_report.debt_metrics.interest_coverage:.1f}x" if health_report.debt_metrics.interest_coverage else "  Interest Coverage: N/A")
        
        if health_report.revenue_quality:
            print(f"\nRevenue Quality:")
            print(f"  3-Year Revenue Growth: {health_report.revenue_quality.revenue_growth_3yr:.1%}" if health_report.revenue_quality.revenue_growth_3yr else "  3-Year Revenue Growth: N/A")
        
        if health_report.strengths:
            print(f"\nStrengths:")
            for strength in health_report.strengths:
                print(f"  + {strength}")
        
        if health_report.key_risks:
            print(f"\nKey Risks:")
            for risk in health_report.key_risks:
                print(f"  - {risk}")
    
    else:
        print(f"Could not analyze financial health for {ticker}")

if __name__ == "__main__":
    test_financial_health_analysis()
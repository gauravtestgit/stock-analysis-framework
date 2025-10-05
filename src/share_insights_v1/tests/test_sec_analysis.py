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
    test_tickers = ["lxrx", "eqt", "ko"]
    
    for ticker in test_tickers:
        print(f"\n{'='*50}")
        print(f"Analyzing {ticker}")
        print(f"{'='*50}")
        
        try:
            # Get financial health report
            report = analyzer.analyze_financial_health(ticker)
            
            if report:
                print(f"✓ Successfully analyzed {ticker}")
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
                
                # Strengths and risks
                if report.strengths:
                    print(f"\nStrengths:")
                    for strength in report.strengths:
                        print(f"  + {strength}")
                
                if report.key_risks:
                    print(f"\nRisks:")
                    for risk in report.key_risks:
                        print(f"  - {risk}")
            
            else:
                print(f"✗ Could not analyze {ticker}")
                
        except Exception as e:
            print(f"✗ Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_sec_financial_health()
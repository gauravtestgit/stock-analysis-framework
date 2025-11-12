#!/usr/bin/env python3
"""Test CHRS DCF calculation fix"""

import os
import sys
sys.path.append('src')

from src.share_insights_v1.implementations.analyzers.dcf_analyzer import DCFAnalyzer
from src.share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
from src.share_insights_v1.implementations.calculators.quality_calculator import QualityScoreCalculator
from src.share_insights_v1.implementations.classifier import CompanyClassifier

def test_chrs_dcf():
    """Test CHRS DCF calculation"""
    ticker = "CHRS"
    
    # Get data
    yp = YahooFinanceProvider()
    metrics = yp.get_financial_metrics(ticker=ticker)
    
    # Get quality and classification
    qs = QualityScoreCalculator()
    quality = qs.calculate(metrics=metrics)
    
    cc = CompanyClassifier()
    company_type = cc.classify(ticker=ticker, metrics=metrics)
    
    print(f"Testing DCF for {ticker}")
    print(f"Company Type: {company_type}")
    print(f"Quality Grade: {quality.get('grade', 'Unknown')}")
    print(f"Current Price: ${metrics.get('current_price', 0):.2f}")
    print("=" * 50)
    
    # Prepare data for DCF analyzer
    data = {
        'financial_metrics': metrics,
        'company_info': {
            'sector': metrics.get('sector', ''),
            'industry': metrics.get('industry', '')
        },
        'quality_grade': quality.get('grade', 'C'),
        'company_type': company_type
    }
    
    # Run DCF analysis
    dcf_analyzer = DCFAnalyzer()
    
    try:
        result = dcf_analyzer.analyze(ticker, data)
        
        if 'error' in result:
            print(f"[ERROR] DCF Error: {result['error']}")
        else:
            print("[SUCCESS] DCF Analysis Successful:")
            print(f"  Predicted Price: ${result.get('predicted_price', 0):.2f}")
            print(f"  Current Price: ${result.get('current_price', 0):.2f}")
            print(f"  Upside/Downside: {result.get('upside_downside_pct', 0):+.1f}%")
            print(f"  Recommendation: {result.get('recommendation', 'Unknown')}")
            print(f"  Confidence: {result.get('confidence', 'Unknown')}")
            
            # Show DCF details if available
            dcf_calc = result.get('dcf_calculations', {})
            if dcf_calc:
                print(f"\n📊 DCF Details:")
                print(f"  Terminal Ratio: {dcf_calc.get('terminal_ratio', 0):.1%}")
                print(f"  FCF CAGR: {dcf_calc.get('fcf_cagr', 0):.1%}")
                print(f"  EBITDA CAGR: {dcf_calc.get('ebitda_cagr', 0):.1%}")
                if 'terminal_adjustment_factor' in dcf_calc:
                    print(f"  Terminal Adjustment: {dcf_calc['terminal_adjustment_factor']:.2f}x")
        
    except Exception as e:
        print(f"[EXCEPTION] Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.environ['DEBUG'] = 'true'
    test_chrs_dcf()
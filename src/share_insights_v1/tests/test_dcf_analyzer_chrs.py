#!/usr/bin/env python3
"""Test DCF analyzer directly with CHRS"""

import os
import sys
sys.path.append('src')

from src.share_insights_v1.implementations.analyzers.dcf_analyzer import DCFAnalyzer
from src.share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
from src.share_insights_v1.implementations.calculators.quality_calculator import QualityScoreCalculator
from src.share_insights_v1.implementations.classifier import CompanyClassifier

def test_dcf_analyzer():
    """Test DCF analyzer with CHRS"""
    ticker = "CHRS"
    
    # Get data like orchestrator does
    yp = YahooFinanceProvider()
    metrics = yp.get_financial_metrics(ticker=ticker)
    
    # Get quality and classification
    qs = QualityScoreCalculator()
    quality = qs.calculate(metrics=metrics)
    
    cc = CompanyClassifier()
    company_type = cc.classify(ticker=ticker, metrics=metrics)
    
    print(f"Testing DCF Analyzer for {ticker}")
    print(f"Company Type: {company_type}")
    print(f"Quality Grade: {quality.get('grade', 'Unknown')}")
    print("=" * 50)
    
    # Prepare data for DCF analyzer (like orchestrator does)
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
            print("[SUCCESS] DCF Analyzer Results:")
            print(f"  Predicted Price: ${result.get('predicted_price', 0):.2f}")
            print(f"  Current Price: ${result.get('current_price', 0):.2f}")
            print(f"  Upside/Downside: {result.get('upside_downside_pct', 0):+.1f}%")
            print(f"  Recommendation: {result.get('recommendation', 'Unknown')}")
            print(f"  Confidence: {result.get('confidence', 'Unknown')}")
            
            # Check if risk adjustment was applied
            dcf_calc = result.get('dcf_calculations', {})
            if 'risk_discount' in dcf_calc:
                print(f"  Risk Discount: {dcf_calc['risk_discount']:.0%}")
                print(f"  Original Price: ${dcf_calc.get('original_share_price', 0):.2f}")
            
            print(f"\n  Terminal Ratio: {dcf_calc.get('terminal_ratio', 0):.1%}")
            print(f"  PV FCF: ${dcf_calc.get('pv_fcf', 0):,.0f}")
        
    except Exception as e:
        print(f"[EXCEPTION] Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.environ['DEBUG'] = 'true'
    test_dcf_analyzer()
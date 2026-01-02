#!/usr/bin/env python3
"""Test orchestrator with CHRS to verify DCF path"""

import os
import sys
sys.path.append('src')

from src.share_insights_v1.services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from src.share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
from src.share_insights_v1.implementations.calculators.quality_calculator import QualityScoreCalculator
from src.share_insights_v1.implementations.classifier import CompanyClassifier
from src.share_insights_v1.implementations.analyzers.dcf_analyzer import DCFAnalyzer
from src.share_insights_v1.models.analysis_result import AnalysisType

def test_orchestrator_dcf():
    """Test orchestrator DCF path with CHRS"""
    ticker = "CHRS"
    
    # Setup orchestrator like dashboard does
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register DCF analyzer
    dcf_analyzer = DCFAnalyzer()
    orchestrator.register_analyzer(AnalysisType.DCF, dcf_analyzer)
    
    print(f"Testing Orchestrator DCF path for {ticker}")
    print("=" * 50)
    
    try:
        # Run full orchestrator analysis
        result = orchestrator.analyze_stock(ticker)
        
        if 'error' in result:
            print(f"[ERROR] Orchestrator Error: {result['error']}")
        else:
            print("[SUCCESS] Orchestrator Results:")
            print(f"  Company Type: {result.get('company_type', 'Unknown')}")
            print(f"  Quality Grade: {result.get('quality_score', {}).get('grade', 'Unknown')}")
            
            # Check DCF analysis specifically
            dcf_result = result.get('analyses', {}).get('dcf', {})
            if dcf_result:
                if 'error' in dcf_result:
                    print(f"  DCF Error: {dcf_result['error']}")
                else:
                    print(f"  DCF Price: ${dcf_result.get('predicted_price', 0):.2f}")
                    print(f"  Current Price: ${dcf_result.get('current_price', 0):.2f}")
                    print(f"  Upside: {dcf_result.get('upside_downside_pct', 0):+.1f}%")
                    print(f"  Recommendation: {dcf_result.get('recommendation', 'Unknown')}")
                    
                    # Check if risk adjustment was applied
                    dcf_calc = dcf_result.get('dcf_calculations', {})
                    if 'risk_discount' in dcf_calc:
                        print(f"  Risk Discount Applied: {dcf_calc['risk_discount']:.0%}")
                        print(f"  Original Price: ${dcf_calc.get('original_share_price', 0):.2f}")
                    else:
                        print(f"  No risk discount found in DCF calculations")
                        print(f"  Terminal Ratio: {dcf_calc.get('terminal_ratio', 0):.1%}")
            else:
                print("  No DCF analysis found in results")
                print(f"  Available analyses: {list(result.get('analyses', {}).keys())}")
        
    except Exception as e:
        print(f"[EXCEPTION] Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.environ['DEBUG'] = 'true'
    test_orchestrator_dcf()
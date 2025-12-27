#!/usr/bin/env python3
"""Test script for the enhanced industry analyzer"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.share_insights_v1.services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from src.share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
from src.share_insights_v1.implementations.classifier import CompanyTypeClassifier
from src.share_insights_v1.implementations.calculators.quality_calculator import QualityCalculator
from src.share_insights_v1.implementations.analyzers.industry_analysis_analyzer import IndustryAnalysisAnalyzer
from src.share_insights_v1.models.analysis_result import AnalysisType

def test_industry_analyzer():
    """Test the industry analyzer with a sample stock"""
    
    # Setup components
    data_provider = YahooFinanceProvider()
    classifier = CompanyTypeClassifier()
    quality_calculator = QualityCalculator()
    
    # Create orchestrator
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator, debug_mode=True)
    
    # Register industry analyzer
    industry_analyzer = IndustryAnalysisAnalyzer(data_provider)
    orchestrator.register_analyzer(AnalysisType.INDUSTRY_ANALYSIS, industry_analyzer)
    
    # Test with a well-known stock
    ticker = "AAPL"
    print(f"Testing industry analyzer for {ticker}...")
    
    try:
        # Run analysis
        results = orchestrator.analyze_stock(ticker)
        
        if 'error' in results:
            print(f"❌ Analysis failed: {results['error']}")
            return
        
        # Check if industry analysis was performed
        if 'industry_analysis' in results.get('analyses', {}):
            industry_result = results['analyses']['industry_analysis']
            
            print(f"✅ Industry analysis completed for {ticker}")
            print(f"Industry: {industry_result.get('industry', 'N/A')}")
            print(f"Sector: {industry_result.get('sector', 'N/A')}")
            
            # Display key metrics
            if 'porter_five_forces' in industry_result:
                forces = industry_result['porter_five_forces']
                print(f"\nPorter's Five Forces:")
                for force, data in forces.items():
                    if isinstance(data, dict) and 'score' in data:
                        print(f"  {force}: {data['score']}/10")
            
            if 'industry_score' in industry_result:
                print(f"\nOverall Industry Score: {industry_result['industry_score']}/10")
            
            if 'recommendation' in industry_result:
                print(f"Industry Recommendation: {industry_result['recommendation']}")
                
        else:
            print(f"❌ Industry analysis not found in results")
            print(f"Available analyses: {list(results.get('analyses', {}).keys())}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_industry_analyzer()
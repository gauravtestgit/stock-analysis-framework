from typing import Dict, Any
from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
from ..models.analysis_result import AnalysisType
import json

def test_simple_orchestrator():
    """Simple test with just technical analysis"""
    ticker = "aapl"
    print(f"\n=== Simple Orchestrator Test ({ticker}) ===")
    # Setup dependencies
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    
    # Create orchestrator
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register only technical analyzer
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
    
    # Run analysis
    results = orchestrator.analyze_stock(ticker=ticker)
    
    # Print key results
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return
    
    print(f"✅ Ticker: {results.get('ticker')}")
    print(f"✅ Company Type: {results.get('company_type')}")
    print(f"✅ Quality Grade: {results.get('quality_score', {}).get('grade')}")
    print(f"✅ Analyses: {list(results.get('analyses', {}).keys())}")
    
    # Check technical analysis results
    technical = results.get('analyses', {}).get('startup', {})
    if technical and 'error' not in technical:
        print(f"✅ Technical Analysis: {technical.get('recommendation', 'N/A')}")
        print(f"✅ Current Price: ${technical.get('current_price', 0):.2f}")
        print(f"✅ Trend: {technical.get('trend', 'N/A')}")
        print(json.dumps(technical,indent=2, default=str))
    else:
        print(f"❌ Technical Analysis Error: {technical.get('error', 'Unknown')}")
    
    return results

if __name__ == "__main__":
    test_simple_orchestrator()
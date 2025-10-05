import json
from typing import Dict, Any
from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
from ..models.analysis_result import AnalysisType

def setup_orchestrator():
    """Setup orchestrator with all analyzers"""
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register all analyzers
    orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
    orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
    orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
    
    return orchestrator

def test_company_type(ticker: str, company_name: str, expected_analyses: list):
    """Generic test function for any company type"""
    print(f"\n=== Testing {company_name} ({ticker}) ===")
    
    orchestrator = setup_orchestrator()
    results = orchestrator.analyze_stock(ticker)
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return results
    
    # Print results
    print(f"Company Type: {results.get('company_type')}")
    print(f"Quality Grade: {results.get('quality_score', {}).get('grade')}")
    print(f"Analyses Run: {list(results.get('analyses', {}).keys())}")
    
    # Verify expected analyses
    actual_analyses = list(results.get('analyses', {}).keys())
    print(f"Expected: {expected_analyses}")
    print(f"Actual: {actual_analyses}")
    
    # Check if match
    if set(actual_analyses) == set(expected_analyses):
        print("✅ Test PASSED")
    else:
        print("❌ Test FAILED")
    
    return results

def test_orchestrator_mature_company():
    """Test orchestrator with mature profitable company (AAPL)"""
    return test_company_type("AAPL", "Mature Company", ['technical', 'dcf', 'comparable'])

def test_orchestrator_financial_company():
    """Test orchestrator with financial company (JPM)"""
    return test_company_type("JPM", "Financial Company", ['technical', 'comparable'])

def test_orchestrator_etf():
    """Test orchestrator with ETF (QQQ)"""
    return test_company_type("QQQ", "ETF", ['technical'])

def test_orchestrator_growth_company():
    """Test orchestrator with growth company (TSLA)"""
    return test_company_type("TSLA", "Growth Company", ['technical', 'dcf', 'comparable'])

def test_orchestrator_reit():
    """Test orchestrator with REIT (AMT)"""
    return test_company_type("AMT", "REIT", ['technical', 'dcf', 'comparable'])

def test_orchestrator_commodity():
    """Test orchestrator with commodity company (XOM)"""
    return test_company_type("XOM", "Commodity Company", ['technical', 'dcf', 'comparable'])

def test_orchestrator_startup():
    """Test orchestrator with startup/loss-making company (RIVN)"""
    return test_company_type("RIVN", "Startup/Loss-Making", ['technical', 'startup'])

def test_orchestrator_startup_alt():
    """Test orchestrator with alternative startup/loss-making company (PLTR)"""
    return test_company_type("PLTR", "Startup/Loss-Making Alt", ['technical', 'startup'])

def test_orchestrator_cyclical():
    """Test orchestrator with cyclical company (CAT)"""
    return test_company_type("CAT", "Cyclical Company", ['technical', 'dcf', 'comparable'])

def test_all_orchestrator():
    """Run all orchestrator tests for different company types"""
    test_results = {}
    
    try:
        print("\n🚀 Running Comprehensive Orchestrator Tests")
        print("=" * 50)
        
        # Test all company types
        test_results['mature'] = test_orchestrator_mature_company()
        test_results['growth'] = test_orchestrator_growth_company()
        test_results['financial'] = test_orchestrator_financial_company()
        test_results['reit'] = test_orchestrator_reit()
        test_results['commodity'] = test_orchestrator_commodity()
        test_results['cyclical'] = test_orchestrator_cyclical()
        test_results['startup'] = test_orchestrator_startup()
        test_results['startup_alt'] = test_orchestrator_startup_alt()
        test_results['etf'] = test_orchestrator_etf()
        
        print("\n" + "=" * 50)
        print("📊 SUMMARY OF ALL TESTS")
        print("=" * 50)
        
        # Summary table
        for test_name, result in test_results.items():
            if 'error' in result:
                print(f"❌ {test_name.upper()}: ERROR - {result['error'][:50]}...")
            else:
                company_type = result.get('company_type', 'unknown')
                analyses = list(result.get('analyses', {}).keys())
                print(f"✅ {test_name.upper()}: {company_type} -> {analyses}")
        
        print("\n✅ All orchestrator tests completed")
        
        # Save detailed results
        with open('orchestrator_comprehensive_results.json', 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print("📄 Detailed results saved to orchestrator_comprehensive_results.json")
        
    except Exception as e:
        print(f"❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    return test_results

if __name__ == "__main__":
    test_all_orchestrator()
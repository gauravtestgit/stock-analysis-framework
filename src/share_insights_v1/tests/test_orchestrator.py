import json
import time
from typing import Dict, Any
from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..implementations.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.analyzers.competitive_position_analyzer import CompetitivePositionAnalyzer
from ..implementations.analyzers.management_quality_analyzer import ManagementQualityAnalyzer
from ..implementations.analyzers.financial_health_analyzer import FinancialHealthAnalyzer
from ..implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ..implementations.data_providers.sec_edgar_provider import SECEdgarProvider
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
    
    # Register quantitative analyzers
    orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
    orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
    orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
    
    # Register qualitative analyzers
    orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.COMPETITIVE_POSITION, CompetitivePositionAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.MANAGEMENT_QUALITY, ManagementQualityAnalyzer(data_provider))
    
    # Register SEC-based analyzer
    sec_provider = SECEdgarProvider()
    orchestrator.register_analyzer(AnalysisType.FINANCIAL_HEALTH, FinancialHealthAnalyzer(sec_provider))
    
    # Register analyst consensus analyzer
    orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(data_provider))
    
    return orchestrator

def test_company_type(ticker: str, company_name: str, expected_analyses: list):
    """Generic test function for any company type"""
    print(f"\n=== Testing {company_name} ({ticker}) ===")
    
    orchestrator = setup_orchestrator()
    test_start = time.time()
    results = orchestrator.analyze_stock(ticker)
    test_end = time.time()
    
    total_test_time = test_end - test_start
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return results
    
    # Print results
    print(f"Company Type: {results.get('company_type')}")
    print(f"Quality Grade: {results.get('quality_score', {}).get('grade')}")
    print(f"Analyses Run: {list(results.get('analyses', {}).keys())}")
    
    # Print timing information
    orchestrator_time = results.get('execution_time_seconds', 0)
    analyses_count = results.get('analyses_count', 0)
    print(f"⏱️  Orchestrator Time: {orchestrator_time}s")
    print(f"⏱️  Total Test Time: {total_test_time:.2f}s")
    print(f"📊 Analyses Count: {analyses_count}")
    if analyses_count > 0:
        print(f"⚡ Avg Time per Analysis: {orchestrator_time/analyses_count:.2f}s")
    
    # Verify expected analyses
    actual_analyses = list(results.get('analyses', {}).keys())
    print(f"Expected: {expected_analyses}")
    print(f"Actual: {actual_analyses}")
    
    # Check if match
    if set(actual_analyses) == set(expected_analyses):
        print("✅ Test PASSED")
    else:
        print("❌ Test FAILED")
    
    # Add timing to results
    results['test_timing'] = {
        'total_test_time': round(total_test_time, 2),
        'orchestrator_time': orchestrator_time,
        'analyses_count': analyses_count
    }
    
    return results

def test_orchestrator_mature_company():
    """Test orchestrator with mature profitable company (AAPL)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'dcf', 'comparable']
    return test_company_type("AAPL", "Mature Company", expected)

def test_orchestrator_financial_company():
    """Test orchestrator with financial company (JPM)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'comparable']
    return test_company_type("JPM", "Financial Company", expected)

def test_orchestrator_etf():
    """Test orchestrator with ETF (QQQ)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'analyst_consensus']
    return test_company_type("QQQ", "ETF", expected)

def test_orchestrator_growth_company():
    """Test orchestrator with growth company (TSLA)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'dcf', 'comparable']
    return test_company_type("TSLA", "Growth Company", expected)

def test_orchestrator_reit():
    """Test orchestrator with REIT (AMT)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'dcf', 'comparable']
    return test_company_type("AMT", "REIT", expected)

def test_orchestrator_commodity():
    """Test orchestrator with commodity company (XOM)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'dcf', 'comparable']
    return test_company_type("XOM", "Commodity Company", expected)

def test_orchestrator_startup():
    """Test orchestrator with startup/loss-making company (RIVN)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'startup']
    return test_company_type("SDOT", "Startup/Loss-Making", expected)

def test_orchestrator_startup_alt():
    """Test orchestrator with alternative startup/loss-making company (PLTR)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'startup']
    return test_company_type("PLTR", "Startup/Loss-Making Alt", expected)

def test_orchestrator_cyclical():
    """Test orchestrator with cyclical company (CAT)"""
    expected = ['technical', 'ai_insights', 'news_sentiment', 'business_model', 'competitive_position', 'management_quality', 'financial_health', 'analyst_consensus', 'dcf', 'comparable']
    return test_company_type("CAT", "Cyclical Company", expected)

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
        
        # Summary table with timing
        total_orchestrator_time = 0
        total_analyses = 0
        
        for test_name, result in test_results.items():
            if 'error' in result:
                print(f"❌ {test_name.upper()}: ERROR - {result['error'][:50]}...")
            else:
                company_type = result.get('company_type', 'unknown')
                analyses = list(result.get('analyses', {}).keys())
                timing = result.get('test_timing', {})
                orch_time = timing.get('orchestrator_time', 0)
                analyses_count = timing.get('analyses_count', 0)
                
                total_orchestrator_time += orch_time
                total_analyses += analyses_count
                
                print(f"✅ {test_name.upper()}: {company_type} -> {analyses_count} analyses in {orch_time}s")
        
        # Overall timing summary
        print("\n⏱️  TIMING SUMMARY:")
        print(f"Total Orchestrator Time: {total_orchestrator_time:.2f}s")
        print(f"Total Analyses Run: {total_analyses}")
        if total_analyses > 0:
            print(f"Average Time per Analysis: {total_orchestrator_time/total_analyses:.2f}s")
        print(f"Tests Run: {len(test_results)}")
        if len(test_results) > 0:
            print(f"Average Time per Stock: {total_orchestrator_time/len(test_results):.2f}s")
        
        print("\n✅ All orchestrator tests completed with timing analysis")
        
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
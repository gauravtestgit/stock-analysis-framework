#!/usr/bin/env python3

import json
from typing import Dict, Any
from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..services.storage.analysis_storage_service import AnalysisStorageService
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..implementations.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.analyzers.competitive_position_analyzer import CompetitivePositionAnalyzer
from ..implementations.analyzers.management_quality_analyzer import ManagementQualityAnalyzer
from ..implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
from ..models.analysis_result import AnalysisType

import traceback

def setup_comprehensive_orchestrator():
    """Setup orchestrator with ALL analyzers including new qualitative ones"""
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    
    # Initialize plugin system for LLM providers
    from ..implementations.llm_providers.plugin_manager import LLMPluginManager
    from ..implementations.llm_providers.llm_manager import LLMManager
    
    try:
        llm_manager = LLMManager(use_plugin_system=True)
        # Use enhanced set_primary_provider to switch to specific model
        llm_manager.set_primary_provider("groq", "llama-3.3-70b-versatile")
        primary = llm_manager.get_primary_provider()
        print("✅ Plugin system initialized successfully")
        print(f"🎯 Primary provider: {primary.get_provider_name()} using model: {primary.get_current_model()}")
    except Exception as e:
        llm_manager = LLMManager()  # Fallback to legacy
        print(f"⚠️  Plugin system failed ({e}), using legacy LLM manager")
    
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register quantitative analyzers
    orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
    orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
    orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
    
    # Register qualitative analyzers with plugin system support
    orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(data_provider, llm_manager))
    orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(data_provider, llm_manager))
    orchestrator.register_analyzer(AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(data_provider, llm_manager))
    orchestrator.register_analyzer(AnalysisType.COMPETITIVE_POSITION, CompetitivePositionAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.MANAGEMENT_QUALITY, ManagementQualityAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(data_provider))
    
    # Import and register industry analysis
    from ..implementations.analyzers.industry_analysis_analyzer import IndustryAnalysisAnalyzer
    orchestrator.register_analyzer(AnalysisType.INDUSTRY_ANALYSIS, IndustryAnalysisAnalyzer(data_provider))
    
    return orchestrator

def test_comprehensive_analysis(ticker: str, save_to_db: bool = False):
    """Test comprehensive analysis with all analyzers"""
    print(f"\n=== Comprehensive Analysis for {ticker} ===")
    
    orchestrator = setup_comprehensive_orchestrator()
    results = orchestrator.analyze_stock(ticker)
    
    # Store to database if requested
    if save_to_db and 'error' not in results:
        try:
            storage_service = AnalysisStorageService()
            storage_service.store_comprehensive_analysis(ticker, results)
            print(f"✅ Results stored to database for {ticker}")
        except Exception as e:
            print(f"❌ Database storage failed: {str(e)}")
    
    if 'error' in results:
        print(f"❌ Error: {results['error']}")
        return results
    
    # Print results summary
    print(f"Company Type: {results.get('company_type')}")
    print(f"Quality Grade: {results.get('quality_score', {}).get('grade')}")
    
    analyses = results.get('analyses', {})
    print(f"Total Analyses Run: {len(analyses)}")
    
    # Print each analysis result
    for analysis_name, analysis_result in analyses.items():
        if 'error' in analysis_result:
            print(f"❌ {analysis_name}: ERROR - {analysis_result['error']}")
        elif not analysis_result.get('applicable', True):
            print(f"⚠️  {analysis_name}: NOT APPLICABLE - {analysis_result.get('reason', '')}")
        else:
            recommendation = analysis_result.get('recommendation', 'N/A')
            confidence = analysis_result.get('confidence', 'N/A')
            print(f"✅ {analysis_name}: {recommendation} ({confidence} confidence)")
    
    # Print final recommendation if available
    final_rec = results.get('final_recommendation')
    if final_rec:
        print(f"\n🎯 FINAL RECOMMENDATION: {final_rec.recommendation.value if hasattr(final_rec.recommendation, 'value') else final_rec.recommendation}")
        print(f"   Confidence: {final_rec.confidence}")
        print(f"   Target Price: ${final_rec.target_price:.2f}")
        print(f"   Summary: {final_rec.summary}")
    
    return results

def test_all_comprehensive(save_to_db: bool = False):
    """Test comprehensive analysis on multiple tickers"""
    test_tickers = ['CRM']
    all_results = {}
    
    print("🚀 Running Comprehensive Analysis Tests")
    if save_to_db:
        print("💾 Database storage ENABLED")
    print("=" * 60)
    
    for ticker in test_tickers:
        try:
            result = test_comprehensive_analysis(ticker, save_to_db)
            all_results[ticker] = result
        except Exception as e:
            print(traceback.format_exc())
            print(f"❌ {ticker} failed: {str(e)}")
            all_results[ticker] = {'error': str(e)}
    
    # Save results
    with open('comprehensive_analysis_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to comprehensive_analysis_results.json")
    return all_results

if __name__ == "__main__":
    # Set save_to_db=True to enable database storage
    test_all_comprehensive(save_to_db=True)
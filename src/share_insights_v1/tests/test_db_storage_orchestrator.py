#!/usr/bin/env python3
"""Test database storage via orchestrator"""

import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..services.storage.analysis_storage_service import AnalysisStorageService
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.classifier import CompanyClassifier
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..implementations.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from ..implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
from ..implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ..models.analysis_result import AnalysisType
import json

def test_orchestrator_storage():
    """Test storing orchestrator results in database"""
    
    # Initialize dependencies
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    
    # Initialize services
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register analyzers
    orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
    orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
    orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
    orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(data_provider))
    
    storage = AnalysisStorageService()
    
    ticker = "AAPL"
    print(f"Running analysis for {ticker}...")
    
    # Run orchestrator analysis
    results = orchestrator.analyze_stock(ticker)
    
    print(f"Analysis completed. Found {results.get('analyses_count', 0)} analyses")
    
    # Handle final recommendation safely
    final_rec = results.get('final_recommendation', {})
    if hasattr(final_rec, 'recommendation'):
        rec_value = final_rec.recommendation.value if hasattr(final_rec.recommendation, 'value') else str(final_rec.recommendation)
    else:
        rec_value = final_rec.get('recommendation', 'N/A')
    print(f"Final recommendation: {rec_value}")
    
    # Store in database
    print("Storing results in database...")
    success = storage.store_comprehensive_analysis(ticker, results)
    
    if success:
        print("✓ Successfully stored in database")
        
        # Retrieve and verify
        print("Retrieving stored analysis...")
        retrieved = storage.get_latest_analysis(ticker)
        
        if retrieved:
            print(f"✓ Retrieved analysis for {retrieved['ticker']}")
            print(f"  Date: {retrieved['analysis_date']}")
            print(f"  Analyses count: {retrieved['analyses_count']}")
            final_rec = retrieved.get('final_recommendation', {})
            if isinstance(final_rec, dict):
                rec_value = final_rec.get('recommendation', 'N/A')
            else:
                rec_value = str(final_rec)
            print(f"  Final recommendation: {rec_value}")
            print(f"  Individual analyses: {list(retrieved['analyses'].keys())}")
        else:
            print("✗ Failed to retrieve analysis")
    else:
        print("✗ Failed to store in database")

if __name__ == "__main__":
    test_orchestrator_storage()
#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ..services.orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ..models.analysis_result import AnalysisType
from ..config.config import FinanceConfig
import json

def test_recommendation_service():
    """Test the recommendation service integration"""
    
    # Initialize components
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    config = FinanceConfig()
    
    # Create orchestrator
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register analyzers
    orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
    orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
    orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
    orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(data_provider=data_provider))
    
    # Test with different company types
    test_tickers = ['AAPL', 'TSLA', 'JPM']
    
    results = {}
    for ticker in test_tickers:
        print(f"\nTesting recommendation service for {ticker}...")
        result = orchestrator.analyze_stock(ticker)
        
        if 'error' not in result:
            # Extract recommendation info
            final_rec = result.get('final_recommendation', {})
            print(f"Final Recommendation: {final_rec.recommendation}")
            print(f"Confidence: {final_rec.confidence}")
            print(f"Target Price: ${final_rec.target_price:.2f}" if final_rec.target_price else "Target Price: N/A")
            print(f"Reasoning: {final_rec.summary}")
            
            results[ticker] = result
        else:
            print(f"Error: {result['error']}")
    
    # Save results
    with open('recommendation_service_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nRecommendation service test completed. Results saved to recommendation_service_results.json")

if __name__ == "__main__":
    test_recommendation_service()
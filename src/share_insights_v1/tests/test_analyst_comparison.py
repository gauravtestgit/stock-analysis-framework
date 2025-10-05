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
from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..models.analysis_result import AnalysisType
from ..config.config import FinanceConfig
import json

def test_analyst_comparison():
    """Test the analyst comparison service integration"""
    
    # Initialize components
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    quality_calculator = QualityScoreCalculator()
    config = FinanceConfig()
    
    # Create orchestrator
    orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
    
    # Register analyzers
    orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer(config))
    orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
    orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer(config))
    orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer(config))
    orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(data_provider))
    orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(data_provider=data_provider))
    
    # Test with stocks that have analyst coverage
    test_tickers = ['aaoi', 'ampx', 'eqt']
    
    results = {}
    for ticker in test_tickers:
        print(f"\nTesting analyst comparison for {ticker}...")
        result = orchestrator.analyze_stock(ticker)
        
        if 'error' not in result:
            # Extract comparison info
            comparison = result.get('analyst_comparison', {})
            if comparison:
                print(f"Found {len(comparison.get('comparisons', []))} method comparisons")
                
                # Print summary
                summary = comparison.get('summary', {})
                for method, stats in summary.items():
                    print(f"{method.upper()}: {stats['alignment_rate']:.1f}% aligned, avg deviation: {stats['avg_deviation']:.1f}%")
                
                # Print individual comparisons
                for comp in comparison.get('comparisons', []):
                    print(f"  {comp.method}: Our {comp.our_upside:+.1f}% vs Analysts {comp.analyst_upside:+.1f}% ({comp.alignment})")
            else:
                print("No analyst comparison data available")
            
            results[ticker] = result
        else:
            print(f"Error: {result['error']}")
    
    # Save results
    with open('./src/share_insights_v1/tests/outputs/analyst_comparison_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nAnalyst comparison test completed. Results saved to analyst_comparison_results.json")

if __name__ == "__main__":
    test_analyst_comparison()
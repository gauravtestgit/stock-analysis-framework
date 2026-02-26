#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def test_single_stock_analysis():
    """Test single stock analysis with database storage"""
    try:
        from src.share_insights_v1.services.orchestration.analysis_orchestrator import AnalysisOrchestrator
        from src.share_insights_v1.services.storage.analysis_storage_service import AnalysisStorageService
        from src.share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
        from src.share_insights_v1.implementations.classifier import CompanyClassifier
        from src.share_insights_v1.implementations.calculators.quality_calculator import QualityScoreCalculator
        from src.share_insights_v1.implementations.analyzers.dcf_analyzer import DCFAnalyzer
        from src.share_insights_v1.models.analysis_result import AnalysisType
        from src.share_insights_v1.config.config import FinanceConfig
        
        print("Setting up orchestrator...")
        data_provider = YahooFinanceProvider()
        classifier = CompanyClassifier()
        quality_calculator = QualityScoreCalculator()
        config = FinanceConfig()
        
        orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
        orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer(config))
        
        print("Running analysis for AAPL...")
        results = orchestrator.analyze_stock('AAPL')
        
        if 'error' in results:
            print(f"Analysis failed: {results['error']}")
            return None
        
        print("Storing to database...")
        storage_service = AnalysisStorageService()
        batch_analysis_id = storage_service.store_comprehensive_analysis('AAPL', results)
        
        print(f"SUCCESS: batch_analysis_id generated and stored: {batch_analysis_id}")
        return batch_analysis_id
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_single_stock_analysis()
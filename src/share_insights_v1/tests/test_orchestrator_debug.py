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

def debug_orchestrator_step_by_step():
    """Debug orchestrator step by step"""
    print("\n=== DEBUG: Step-by-Step Orchestrator Test (AAPL) ===")
    
    try:
        # Step 1: Setup dependencies
        print("Step 1: Setting up dependencies...")
        data_provider = YahooFinanceProvider()
        classifier = CompanyClassifier()
        quality_calculator = QualityScoreCalculator()
        print("✅ Dependencies created")
        
        # Step 2: Create orchestrator
        print("\nStep 2: Creating orchestrator...")
        orchestrator = AnalysisOrchestrator(data_provider, classifier, quality_calculator)
        print("✅ Orchestrator created")
        
        # Step 3: Register analyzers
        print("\nStep 3: Registering analyzers...")
        orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer())
        print("✅ DCF analyzer registered")
        orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
        print("✅ Technical analyzer registered")
        orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer())
        print("✅ Comparable analyzer registered")
        orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer())
        print("✅ Startup analyzer registered")
        
        print(f"Registered analyzers: {list(orchestrator.analyzers.keys())}")
        
        # Step 4: Test data retrieval
        print("\nStep 4: Testing data retrieval...")
        financial_metrics = data_provider.get_financial_metrics("AAPL")
        if 'error' in financial_metrics:
            print(f"❌ Financial data error: {financial_metrics['error']}")
            return
        print("✅ Financial metrics retrieved")
        
        price_data = data_provider.get_price_data("AAPL")
        if 'error' in price_data:
            print(f"❌ Price data error: {price_data['error']}")
            return
        print("✅ Price data retrieved")
        
        # Step 5: Test classification
        print("\nStep 5: Testing classification...")
        company_type = classifier.classify("AAPL", financial_metrics)
        print(f"✅ Company classified as: {company_type}")
        
        # Step 6: Test quality calculation
        print("\nStep 6: Testing quality calculation...")
        quality_result = quality_calculator.calculate({'financial_metrics': financial_metrics})
        quality_grade = quality_result.get('grade', 'C')
        print(f"✅ Quality grade: {quality_grade}")
        
        # Step 7: Check applicable analyses
        print("\nStep 7: Checking applicable analyses...")
        applicable = orchestrator.get_applicable_analyses(company_type)
        print(f"✅ Applicable analyses for {company_type}: {[a.value for a in applicable]}")
        
        # Step 8: Run full analysis
        print("\nStep 8: Running full analysis...")
        results = orchestrator.analyze_stock("AAPL")
        
        if 'error' in results:
            print(f"❌ Analysis error: {results['error']}")
            return
        
        print(f"✅ Analysis completed")
        print(f"Company Type: {results.get('company_type')}")
        print(f"Quality Grade: {results.get('quality_score', {}).get('grade')}")
        print(f"Analyses Run: {list(results.get('analyses', {}).keys())}")
        
        # Step 9: Check individual analysis results
        print("\nStep 9: Checking individual analysis results...")
        analyses = results.get('analyses', {})
        
        for analysis_name, analysis_result in analyses.items():
            if 'error' in analysis_result:
                print(f"❌ {analysis_name} error: {analysis_result['error']}")
            else:
                print(f"✅ {analysis_name} completed successfully")
        
        return results
        
    except Exception as e:
        print(f"❌ Debug failed at step: {str(e)}")
        import traceback
        traceback.print_exc()

def debug_company_type_logic():
    """Debug company type classification logic"""
    print("\n=== DEBUG: Company Type Logic ===")
    
    test_tickers = ["AAPL", "JPM", "QQQ", "TSLA"]
    
    data_provider = YahooFinanceProvider()
    classifier = CompanyClassifier()
    
    for ticker in test_tickers:
        try:
            print(f"\n--- {ticker} ---")
            financial_metrics = data_provider.get_financial_metrics(ticker)
            if 'error' in financial_metrics:
                print(f"❌ Data error: {financial_metrics['error']}")
                continue
                
            company_type = classifier.classify(ticker, financial_metrics)
            print(f"Company Type: {company_type}")
            
            # Check what analyses should run
            orchestrator = AnalysisOrchestrator(data_provider, classifier, QualityScoreCalculator())
            applicable = orchestrator.get_applicable_analyses(company_type)
            print(f"Should run: {[a.value for a in applicable]}")
            
        except Exception as e:
            print(f"❌ Error with {ticker}: {str(e)}")

if __name__ == "__main__":
    debug_orchestrator_step_by_step()
    debug_company_type_logic()
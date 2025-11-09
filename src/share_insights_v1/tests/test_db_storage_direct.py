#!/usr/bin/env python3
"""Test database storage directly"""

import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..services.storage.analysis_storage_service import AnalysisStorageService
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.classifier import CompanyClassifier

def test_direct_storage():
    """Test storing individual analyzer results directly"""
    
    # Initialize services
    dcf_analyzer = DCFAnalyzer()
    tech_analyzer = TechnicalAnalyzer()
    storage = AnalysisStorageService()
    yp = YahooFinanceProvider()
    qs = QualityScoreCalculator()
    classifier = CompanyClassifier()
    
    ticker = "MSFT"
    print(f"Running individual analyses for {ticker}...")
    
    # Get data for analyzers
    print("Fetching financial data...")
    metrics = yp.get_financial_metrics(ticker)
    quality = qs.calculate(metrics)
    company_type = classifier.classify(ticker, metrics)
    
    analyzer_input = {
        'company_info': {
            'sector': metrics.get('sector', ''),
            'industry': metrics.get('industry', ''),
        },
        'quality_grade': quality.get('grade', 'C'),
        'company_type': company_type,
        'financial_metrics': metrics
    }
    
    # Run DCF analysis
    print("Running DCF analysis...")
    dcf_result = dcf_analyzer.analyze(ticker, analyzer_input)
    
    if not dcf_result.get('error'):
        print(f"DCF: {dcf_result.get('recommendation')} @ ${dcf_result.get('predicted_price', 0):.2f}")
        
        # Store DCF result
        success = storage.store_single_analysis(
            ticker, "DCF",
            dcf_result.get('recommendation', 'N/A'),
            float(dcf_result.get('predicted_price', 0)),
            dcf_result.get('confidence', 'N/A'),
            dcf_result
        )
        print(f"DCF storage: {'✓' if success else '✗'}")
    else:
        print(f"DCF error: {dcf_result.get('error')}")
    
    # Run Technical analysis
    print("Running Technical analysis...")
    price_data = yp.get_price_data(ticker = ticker)
    analyzer_input = {
        'price_data': price_data        
    }
    tech_result = tech_analyzer.analyze(ticker, analyzer_input)
    
    if not tech_result.get('error'):
        print(f"Technical: {tech_result.get('recommendation')} @ ${tech_result.get('predicted_price', 0):.2f}")
        
        # Store Technical result
        success = storage.store_single_analysis(
            ticker, "TECHNICAL",
            tech_result.get('recommendation', 'N/A'),
            float(tech_result.get('predicted_price', 0)),
            tech_result.get('confidence', 'N/A'),
            tech_result
        )
        print(f"Technical storage: {'✓' if success else '✗'}")
    else:
        print(f"Technical error: {tech_result.get('error')}")
    
    # Verify storage by checking database
    print("\nVerifying stored analyses...")
    from ..models.database import SessionLocal
    from ..models.strategy_models import AnalysisHistory
    from sqlalchemy import desc
    
    db = SessionLocal()
    try:
        history = db.query(AnalysisHistory).filter(
            AnalysisHistory.ticker == ticker
        ).order_by(desc(AnalysisHistory.analysis_date)).limit(5).all()
        
        if history:
            print(f"Found {len(history)} stored analyses:")
            for analysis in history:
                print(f"  {analysis.analysis_type}: {analysis.recommendation} @ ${analysis.target_price:.2f} ({analysis.analysis_date})")
        else:
            print("No analyses found in database")
    finally:
        db.close()

if __name__ == "__main__":
    test_direct_storage()
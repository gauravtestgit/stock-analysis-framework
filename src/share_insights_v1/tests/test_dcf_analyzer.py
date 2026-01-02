import yfinance as yf
import pandas as pd
import os
import json
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
def test_dcf() :
    symbol = "nvda"
    stock = yf.Ticker(symbol)
    yp = YahooFinanceProvider()
    
    
    metrics = yp.get_financial_metrics(ticker = symbol)
    print(json.dumps(metrics, indent=2, default=str))
    qs = QualityScoreCalculator()
    quality = qs.calculate(metrics=metrics)
    print(json.dumps(quality, indent=2, default=str))
    company_classifier = CompanyClassifier()
    company_type = company_classifier.classify(ticker = symbol, metrics = metrics)
    print(f"company_type:{company_type}")
    
    analyzer_input = {
        'company_info' : {
            'sector': metrics.get('sector', ''),
            'industry': metrics.get('industry', ''),
        },        
        'quality_grade': quality.get('grade', 'C'),
        'company_type': company_type,
        'financial_metrics': metrics
    }

    dcf_analyzer = DCFAnalyzer() 
    dcf_analysis = dcf_analyzer.analyze(ticker = symbol, data = analyzer_input)
    
    print(json.dumps(dcf_analysis, indent=2, default=str))
if __name__ == "__main__":
    os.environ['DEBUG'] = 'true'
    test_dcf()
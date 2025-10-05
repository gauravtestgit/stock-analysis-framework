from typing import Dict, Any, List, Optional

import yfinance as yf
import pandas as pd
import os
import json
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.analyzers.startup_analyzer import StartupAnalyzer
from ..implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier
from ..interfaces.analyzer import IAnalyzer
from ..interfaces.data_provider import IDataProvider

def _get_dcf_input(symbol : str) -> Dict:

    yp = YahooFinanceProvider()
    metrics = yp.get_financial_metrics(ticker = symbol)
    print(json.dumps(metrics, indent=2, default=str))
    qs = QualityScoreCalculator()
    quality = qs.calculate(metrics=metrics)
    print(json.dumps(quality, indent=2, default=str))
    company_classifier = CompanyClassifier()
    company_type = company_classifier.classify(ticker = symbol, metrics = metrics)
    print(f"company_type:{company_type}")
    
    input = {
        'company_info' : {
            'sector': metrics.get('sector', ''),
            'industry': metrics.get('industry', ''),
        },        
        'quality_grade': quality.get('grade', 'C'),
        'company_type': company_type,
        'financial_metrics': metrics
    }

    return input
def _get_technical_input(symbol : str) -> Dict:
    
    stock = yf.Ticker(symbol)
    yp = YahooFinanceProvider()    
    
    price_data = yp.get_price_data(ticker = symbol)
    input = {
        'price_data': price_data        
    }
    return input

def _run_analyzer(analyzer : IAnalyzer, symbol: str,input : Dict) -> Dict:
    # analyzer_class = type(analyzer).__name__
    print(f"Analyzer: {type(analyzer).__name__}")
    return analyzer.analyze(ticker=symbol, data=input)

def test_all() :
    symbol = "aapl"
    analyzer_input = _get_dcf_input(symbol=symbol)
    dcf_analyzer = DCFAnalyzer()
    result = _run_analyzer(analyzer=dcf_analyzer, symbol=symbol, input=analyzer_input)
    
    print(json.dumps(result, indent=2, default=str))
    
    analyzer_input = _get_technical_input(symbol=symbol)
    technical_analyzer = TechnicalAnalyzer()
    result = _run_analyzer(analyzer=technical_analyzer, symbol=symbol, input=analyzer_input)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    test_all()
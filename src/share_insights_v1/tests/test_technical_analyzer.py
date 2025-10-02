import yfinance as yf
import pandas as pd
import os
import json
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier

def test_dcf() :
    symbol = "aapl"
    stock = yf.Ticker(symbol)
    yp = YahooFinanceProvider()    
    
    price_data = yp.get_price_data(ticker = symbol)
    print(json.dumps(price_data, indent=2, default=str))
        
    analyzer_input = {
        'price_data': price_data        
    }

    technical_analyzer = TechnicalAnalyzer()
    technical_analysis = technical_analyzer.analyze(ticker = symbol, data = analyzer_input)
    
    print(json.dumps(technical_analysis, indent=2, default=str))
if __name__ == "__main__":
    test_dcf()
import yfinance as yf
import pandas as pd
import os
import json
from ..implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ..implementations.calculators.quality_calculator import QualityScoreCalculator
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.classifier import CompanyClassifier

def test_provider_professional() :
    symbol = "aapl"
    stock = yf.Ticker(symbol)
    yp = YahooFinanceProvider()    
    
    professional_analyst_data = yp.get_professional_analyst_data(ticker = symbol)
    print(json.dumps(professional_analyst_data, indent=2, default=str))
        
    
if __name__ == "__main__":
    test_provider_professional()
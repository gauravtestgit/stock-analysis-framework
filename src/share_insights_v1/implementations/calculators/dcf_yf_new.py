"""
New DCF calculator using modular architecture
Backward compatible with existing dcf_yf.py interface
"""
from typing import Dict
from .dcf_calculator.dcf_engine import DCFEngine
from ...config.config import FinanceConfig

def get_share_price(ticker_symbol: str, config: FinanceConfig = None, 
                   sector: str = "", industry: str = "", 
                   company_type=None, quality_grade: str = "C") -> Dict:
    """
    Backward compatible interface for DCF calculation
    Now uses modular DCF engine with company type adjustments
    """
    engine = DCFEngine(config)
    return engine.calculate_dcf(ticker_symbol, sector, industry, company_type, quality_grade)

# Maintain backward compatibility for individual functions if needed
def get_stock_ticker_object(ticker):
    import yfinance as yf
    return yf.Ticker(ticker)

def get_risk_free_rate(ticker='^TNX'):
    import yfinance as yf
    stock = yf.Ticker(ticker)
    return stock.info['previousClose'] / 100
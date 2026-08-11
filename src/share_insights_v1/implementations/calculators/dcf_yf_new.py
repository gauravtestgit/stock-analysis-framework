"""
New DCF calculator using modular architecture
Backward compatible with existing dcf_yf.py interface
"""
from typing import Dict
from .dcf_calculator.dcf_engine import DCFEngine
from ...config.config import FinanceConfig

def get_share_price(ticker_symbol: str, config: FinanceConfig = None, ticker=None) -> Dict:
    """
    Clean interface for DCF calculation - matches original dcf_yf signature
    Config contains all adjusted parameters from analyzer.
    `ticker` (optional pre-built yf.Ticker) lets callers reuse one fetched ticker
    across multiple scenario calculations for the same symbol.
    """
    engine = DCFEngine(config)
    return engine.calculate_dcf(ticker_symbol, ticker=ticker)

# Maintain backward compatibility for individual functions if needed
def get_stock_ticker_object(ticker):
    import yfinance as yf
    return yf.Ticker(ticker)

def get_risk_free_rate(ticker='^TNX'):
    import yfinance as yf
    stock = yf.Ticker(ticker)
    return stock.info['previousClose'] / 100
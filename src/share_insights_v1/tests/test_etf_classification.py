import yfinance as yf
from financial_analyst.config import FinanceConfig
from enum import Enum

class CompanyType(Enum):
    MATURE_PROFITABLE = "mature_profitable"
    GROWTH_PROFITABLE = "growth_profitable"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"
    STARTUP_LOSS_MAKING = "startup_loss_making"
    REIT = "reit"
    FINANCIAL = "financial"
    COMMODITY = "commodity"

def classify_company_simple(ticker):
    """Simplified ETF classification test"""
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Check for ETFs first
    fund_family = info.get('fundFamily', '')
    category = info.get('category', '')
    quote_type = info.get('quoteType', '')
    long_name = info.get('longName', '')
    
    print(f"Ticker: {ticker}")
    print(f"Quote Type: {quote_type}")
    print(f"Long Name: {long_name}")
    print(f"Fund Family: {fund_family}")
    print(f"Category: {category}")
    
    # ETF Detection
    if (quote_type == 'ETF' or 
        'ETF' in long_name.upper() or 
        'FUND' in long_name.upper() or
        fund_family or
        category or
        ticker.endswith('ETF') or
        any(etf_indicator in ticker for etf_indicator in ['QQQ', 'SPY', 'IWM', 'VTI', 'VOO'])):
        return CompanyType.FINANCIAL
    else:
        return CompanyType.STARTUP_LOSS_MAKING

# Test with known ETFs
test_tickers = ['SQQQ', 'QQQ', 'SPY', 'AAPL']

for ticker in test_tickers:
    try:
        result = classify_company_simple(ticker)
        print(f"Classification: {result.value}")
        print("-" * 40)
    except Exception as e:
        print(f"Error with {ticker}: {e}")
        print("-" * 40)
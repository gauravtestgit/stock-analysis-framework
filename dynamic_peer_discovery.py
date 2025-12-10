"""
Dynamic Peer Discovery Methods for Comparable Analysis
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Any, Optional

def get_dynamic_peers_yfinance(ticker: str, max_peers: int = 5) -> List[str]:
    """
    Method 1: Use Yahoo Finance sector/industry data
    Limited but works with existing yfinance dependency
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        sector = info.get('sector', '')
        industry = info.get('industry', '')
        market_cap = info.get('marketCap', 0)
        
        # Predefined lists by sector (would need regular updates)
        sector_tickers = {
            'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'TSLA', 'NFLX', 'ADBE', 'CRM', 'ORCL'],
            'Healthcare': ['JNJ', 'PFE', 'UNH', 'MRK', 'ABBV', 'TMO', 'DHR', 'BMY', 'AMGN', 'GILD'],
            'Financial Services': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'USB', 'PNC', 'TFC', 'COF'],
            'Consumer Cyclical': ['AMZN', 'HD', 'MCD', 'NKE', 'SBUX', 'LOW', 'TJX', 'F', 'GM', 'MAR'],
            'Communication Services': ['GOOGL', 'META', 'NFLX', 'DIS', 'CMCSA', 'VZ', 'T', 'CHTR', 'TMUS', 'ATVI'],
            'Industrials': ['BA', 'CAT', 'GE', 'MMM', 'HON', 'UPS', 'RTX', 'LMT', 'DE', 'EMR'],
            'Consumer Staples': ['PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'KMB', 'GIS', 'K', 'CPB'],
            'Energy': ['XOM', 'CVX', 'COP', 'EOG', 'SLB', 'PSX', 'VLO', 'MPC', 'OXY', 'BKR'],
            'Utilities': ['NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'XEL', 'SRE', 'PEG', 'ED'],
            'Real Estate': ['AMT', 'PLD', 'CCI', 'EQIX', 'PSA', 'WELL', 'DLR', 'O', 'SBAC', 'EXR'],
            'Materials': ['LIN', 'APD', 'SHW', 'FCX', 'NEM', 'DOW', 'DD', 'PPG', 'ECL', 'IFF']
        }
        
        candidates = sector_tickers.get(sector, [])
        candidates = [t for t in candidates if t != ticker]
        
        # Filter by similar market cap (within 10x range)
        peers = []
        for candidate in candidates[:max_peers * 2]:  # Check more than needed
            try:
                candidate_stock = yf.Ticker(candidate)
                candidate_info = candidate_stock.info
                candidate_cap = candidate_info.get('marketCap', 0)
                
                if candidate_cap and market_cap:
                    ratio = max(candidate_cap, market_cap) / min(candidate_cap, market_cap)
                    if ratio <= 10:  # Within 10x market cap
                        peers.append(candidate)
                        if len(peers) >= max_peers:
                            break
            except:
                continue
        
        return peers[:max_peers]
        
    except Exception as e:
        print(f"Error in dynamic peer discovery: {e}")
        return []

def get_dynamic_peers_finviz(ticker: str, max_peers: int = 5) -> List[str]:
    """
    Method 2: Use Finviz screener (requires finviz package)
    More comprehensive but adds dependency
    """
    try:
        from finviz import get_stock, screener
        
        # Get target company info
        stock_info = get_stock(ticker)
        sector = stock_info['Sector']
        industry = stock_info['Industry']
        market_cap = stock_info['Market Cap']
        
        # Convert market cap to numeric for filtering
        def parse_market_cap(cap_str):
            if 'B' in cap_str:
                return float(cap_str.replace('B', '')) * 1e9
            elif 'M' in cap_str:
                return float(cap_str.replace('M', '')) * 1e6
            return 0
        
        target_cap = parse_market_cap(market_cap)
        
        # Screen for similar companies
        filters = [
            f'sec_{sector.lower().replace(" ", "")}',
            'cap_smallover'  # Market cap > $300M
        ]
        
        stock_list = screener.Screener(filters=filters, table='Performance')
        
        # Filter by market cap similarity and exclude target
        peers = []
        for stock in stock_list:
            if stock['Ticker'] == ticker:
                continue
                
            peer_cap = parse_market_cap(stock['Market Cap'])
            if peer_cap and target_cap:
                ratio = max(peer_cap, target_cap) / min(peer_cap, target_cap)
                if ratio <= 5:  # Within 5x market cap
                    peers.append(stock['Ticker'])
                    if len(peers) >= max_peers:
                        break
        
        return peers
        
    except ImportError:
        print("finviz package not installed. Use: pip install finviz")
        return []
    except Exception as e:
        print(f"Error in Finviz peer discovery: {e}")
        return []

def get_dynamic_peers_fmp(ticker: str, api_key: str, max_peers: int = 5) -> List[str]:
    """
    Method 3: Use Financial Modeling Prep API
    Most comprehensive but requires paid API
    """
    try:
        import requests
        
        # Get company profile
        profile_url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={api_key}"
        profile_response = requests.get(profile_url)
        profile_data = profile_response.json()[0]
        
        sector = profile_data['sector']
        industry = profile_data['industry']
        market_cap = profile_data['mktCap']
        
        # Screen for similar companies
        screener_url = f"https://financialmodelingprep.com/api/v3/stock-screener?sector={sector}&marketCapMoreThan={market_cap*0.2}&marketCapLowerThan={market_cap*5}&limit=50&apikey={api_key}"
        screener_response = requests.get(screener_url)
        candidates = screener_response.json()
        
        # Filter and rank by similarity
        peers = []
        for candidate in candidates:
            if candidate['symbol'] == ticker:
                continue
                
            # Additional filtering by industry, financial metrics, etc.
            if candidate.get('industry') == industry:
                peers.append(candidate['symbol'])
                if len(peers) >= max_peers:
                    break
        
        return peers
        
    except Exception as e:
        print(f"Error in FMP peer discovery: {e}")
        return []

def get_dynamic_peers_alpha_vantage(ticker: str, api_key: str, max_peers: int = 5) -> List[str]:
    """
    Method 4: Use Alpha Vantage API
    Good free tier option
    """
    try:
        import requests
        
        # Get company overview
        overview_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
        overview_response = requests.get(overview_url)
        overview_data = overview_response.json()
        
        sector = overview_data.get('Sector', '')
        industry = overview_data.get('Industry', '')
        market_cap = int(overview_data.get('MarketCapitalization', 0))
        
        # Would need to implement sector screening logic
        # Alpha Vantage doesn't have built-in screener, so you'd need to:
        # 1. Maintain a list of tickers by sector
        # 2. Query each one individually
        # 3. Filter by similarity
        
        return []  # Placeholder - would need full implementation
        
    except Exception as e:
        print(f"Error in Alpha Vantage peer discovery: {e}")
        return []

# Usage example
if __name__ == "__main__":
    ticker = "AAPL"
    
    # Method 1: Yahoo Finance (free, limited)
    peers_yf = get_dynamic_peers_yfinance(ticker)
    print(f"Yahoo Finance peers for {ticker}: {peers_yf}")
    
    # Method 2: Finviz (free, better)
    # peers_finviz = get_dynamic_peers_finviz(ticker)
    # print(f"Finviz peers for {ticker}: {peers_finviz}")
    
    # Method 3: FMP (paid, comprehensive)
    # peers_fmp = get_dynamic_peers_fmp(ticker, "your_api_key")
    # print(f"FMP peers for {ticker}: {peers_fmp}")
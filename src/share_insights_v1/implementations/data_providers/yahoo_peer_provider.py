import yfinance as yf
from typing import Dict, Any, List, Optional
from ...interfaces.peer_comparison_provider import PeerComparisonProvider
from ...models.peer_comparison import PeerMetrics

class YahooPeerProvider(PeerComparisonProvider):
    """Yahoo Finance peer comparison data provider"""
    
    def __init__(self):
        # Industry peer mappings for major sectors
        self.industry_peers = {
            'Consumer Electronics': ['AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN'],
            'Software - Application': ['MSFT', 'ORCL', 'CRM', 'ADBE', 'NOW'],
            'Semiconductors': ['NVDA', 'AMD', 'INTC', 'QCOM', 'AVGO'],
            'Biotechnology': ['GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX'],
            'Banks - Regional': ['JPM', 'BAC', 'WFC', 'C', 'USB'],
            'Auto Manufacturers': ['TSLA', 'F', 'GM', 'TM', 'HMC'],
            'Entertainment': ['NFLX', 'DIS', 'CMCSA', 'WBD', 'PARA'],
            'Drug Manufacturers - Specialty & Generic': ['PFE', 'JNJ', 'MRK', 'LLY', 'ABBV']
        }
    
    def get_industry_peers(self, ticker: str, sector: str, industry: str) -> List[str]:
        """Get list of peer companies in same industry"""
        
        peers = self.industry_peers.get(industry, [])
        
        # Remove the target ticker from peers
        if ticker in peers:
            peers = [p for p in peers if p != ticker]
        
        # If no specific industry mapping, use sector-based approach
        if not peers:
            peers = self._get_sector_peers(sector, ticker)
        
        return peers[:5]  # Limit to top 5 peers
    
    def get_peer_metrics(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get financial metrics for peer companies"""
        
        peer_data = {}
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                peer_data[ticker] = {
                    'pe_ratio': info.get('trailingPE'),
                    'ev_ebitda': info.get('enterpriseToEbitda'),
                    'price_to_sales': info.get('priceToSalesTrailing12Months'),
                    'price_to_book': info.get('priceToBook'),
                    'roe': info.get('returnOnEquity'),
                    'revenue_growth': info.get('revenueGrowth'),
                    'profit_margin': info.get('profitMargins'),
                    'market_cap': info.get('marketCap')
                }
                
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
                peer_data[ticker] = {}
        
        return peer_data
    
    def get_sector_averages(self, sector: str) -> Optional[Dict[str, float]]:
        """Get sector average metrics"""
        
        # Hardcoded sector averages (in practice, would fetch from data provider)
        sector_averages = {
            'Technology': {
                'pe_ratio': 25.0,
                'ev_ebitda': 18.0,
                'price_to_sales': 6.0,
                'price_to_book': 4.0,
                'roe': 0.18,
                'revenue_growth': 0.12,
                'profit_margin': 0.20
            },
            'Healthcare': {
                'pe_ratio': 22.0,
                'ev_ebitda': 15.0,
                'price_to_sales': 4.5,
                'price_to_book': 3.0,
                'roe': 0.15,
                'revenue_growth': 0.08,
                'profit_margin': 0.15
            },
            'Financial Services': {
                'pe_ratio': 12.0,
                'ev_ebitda': 10.0,
                'price_to_sales': 2.5,
                'price_to_book': 1.2,
                'roe': 0.12,
                'revenue_growth': 0.05,
                'profit_margin': 0.25
            },
            'Consumer Cyclical': {
                'pe_ratio': 18.0,
                'ev_ebitda': 12.0,
                'price_to_sales': 1.8,
                'price_to_book': 2.5,
                'roe': 0.14,
                'revenue_growth': 0.06,
                'profit_margin': 0.08
            }
        }
        
        return sector_averages.get(sector)
    
    def _get_sector_peers(self, sector: str, exclude_ticker: str) -> List[str]:
        """Get peers based on sector when industry mapping not available"""
        
        sector_stocks = {
            'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'ORCL', 'CRM', 'ADBE'],
            'Healthcare': ['JNJ', 'PFE', 'UNH', 'MRK', 'LLY', 'ABBV', 'TMO', 'DHR'],
            'Financial Services': ['JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'USB', 'PNC'],
            'Consumer Cyclical': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW']
        }
        
        peers = sector_stocks.get(sector, [])
        return [p for p in peers if p != exclude_ticker]
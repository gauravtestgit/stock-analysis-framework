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
    
    def get_industry_peers(self, ticker: str, sector: str, industry: str, market_cap: float = 0, market: str = '') -> List[str]:
        """Get list of peer companies in same industry.

        Prefers a live Yahoo screener query scoped to the target's own exchange
        (region) and, when known, its market-cap band - this is what makes
        peers correct for ASX/NZX/etc tickers (rather than defaulting to US
        names) and keeps micro/small-caps from being benchmarked against
        unrelated mega-caps. Falls back to the static table below only if the
        screener query errors out or returns nothing (e.g. thin coverage, API
        changes).
        """
        peers = self._screen_peers(ticker, sector, industry, market_cap, market)
        if peers:
            return peers

        return self._get_static_peers(ticker, sector, industry)

    def _resolve_region(self, ticker: str, market: str) -> str:
        """Determine the Yahoo screener 'region' value for the target.

        Prefers yfinance's own `info['market']` classification (e.g.
        'au_market' -> 'au'), which is correct for any exchange. Only falls
        back to guessing from the ticker suffix when that field wasn't
        supplied (e.g. older data provider, hand-built test fixtures) -
        `info.get('region')` itself is not usable here, it's been observed to
        return 'US' regardless of the company's actual listing.
        """
        if market and market.endswith('_market'):
            return market[:-len('_market')]

        if ticker.endswith('.AX'):
            return 'au'
        elif ticker.endswith('.NZ'):
            return 'nz'
        else:
            return 'us'

    def _screen_peers(self, ticker: str, sector: str, industry: str, market_cap: float, market: str) -> List[str]:
        """Live-query Yahoo's equity screener for same-region, same-industry peers"""
        ticker_upper = ticker.upper()
        region = self._resolve_region(ticker, market)
        # +/-5x band around the target's own market cap so peers are a
        # comparable size, not just the biggest names in the industry
        cap_band = (market_cap * 0.2, market_cap * 5) if market_cap and market_cap > 0 else None

        for classifier_field, classifier_value in (('industry', industry), ('sector', sector)):
            if not classifier_value:
                continue
            for use_cap_band in ([True, False] if cap_band else [False]):
                try:
                    filters = [
                        yf.EquityQuery('eq', ['region', region]),
                        yf.EquityQuery('eq', [classifier_field, classifier_value]),
                    ]
                    if use_cap_band:
                        filters.append(yf.EquityQuery('gt', ['intradaymarketcap', cap_band[0]]))
                        filters.append(yf.EquityQuery('lt', ['intradaymarketcap', cap_band[1]]))

                    query = yf.EquityQuery('and', filters)
                    # Fetch a wide candidate pool (not just top 5) - the screener sorts
                    # by raw market cap, so without this we'd always keep the biggest
                    # names in the band rather than the ones actually closest in size
                    # to the target
                    result = yf.screen(query, count=50, sortField='intradaymarketcap', sortAsc=False)
                    quotes = result.get('quotes', []) if result else []
                    candidates = [
                        (q.get('symbol'), q.get('marketCap'))
                        for q in quotes
                        if q.get('symbol') and q.get('symbol').upper() != ticker_upper
                    ]
                    if not candidates:
                        continue

                    if market_cap and market_cap > 0:
                        candidates.sort(key=lambda c: abs((c[1] or 0) - market_cap))

                    peers = [symbol for symbol, _ in candidates[:5]]
                    if peers:
                        return peers
                except Exception:
                    # Invalid classifier value for the screener, network error, etc -
                    # try the next fallback tier rather than failing the whole lookup
                    continue

        return []

    def _get_static_peers(self, ticker: str, sector: str, industry: str) -> List[str]:
        """Hardcoded peer table used only when the live screener finds nothing"""
        peers = self.industry_peers.get(industry, [])

        # Remove the target ticker from peers (case-insensitive - callers may pass lowercase tickers)
        ticker_upper = ticker.upper()
        peers = [p for p in peers if p.upper() != ticker_upper]

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
        return [p for p in peers if p.upper() != exclude_ticker.upper()]
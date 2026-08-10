from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class PeerComparisonProvider(ABC):
    """Interface for peer comparison data providers"""
    
    @abstractmethod
    def get_industry_peers(self, ticker: str, sector: str, industry: str, market_cap: float = 0, market: str = '') -> List[str]:
        """Get list of peer companies in same industry.

        market_cap (target company's own, if known) lets implementations narrow
        peers to a comparable size band rather than just industry/exchange.
        market is yfinance's `info['market']` value (e.g. 'us_market', 'au_market')
        and lets implementations scope peers to the target's own exchange/region.
        """
        pass
    
    @abstractmethod
    def get_peer_metrics(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get financial metrics for peer companies"""
        pass
    
    @abstractmethod
    def get_sector_averages(self, sector: str) -> Optional[Dict[str, float]]:
        """Get sector average metrics"""
        pass
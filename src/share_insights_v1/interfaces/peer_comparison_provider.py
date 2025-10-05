from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class PeerComparisonProvider(ABC):
    """Interface for peer comparison data providers"""
    
    @abstractmethod
    def get_industry_peers(self, ticker: str, sector: str, industry: str) -> List[str]:
        """Get list of peer companies in same industry"""
        pass
    
    @abstractmethod
    def get_peer_metrics(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get financial metrics for peer companies"""
        pass
    
    @abstractmethod
    def get_sector_averages(self, sector: str) -> Optional[Dict[str, float]]:
        """Get sector average metrics"""
        pass
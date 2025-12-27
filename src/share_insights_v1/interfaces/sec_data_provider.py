from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class SECDataProvider(ABC):
    """Interface for SEC filing data providers"""
    
    @abstractmethod
    def get_latest_10k(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest 10-K filing data"""
        pass
    
    @abstractmethod
    def get_latest_10q(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get latest 10-Q filing data"""
        pass
    
    @abstractmethod
    def get_filing_facts(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get company facts from SEC API"""
        pass
    
    @abstractmethod
    def get_segment_revenue_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get segment revenue data from SEC filings"""
        pass
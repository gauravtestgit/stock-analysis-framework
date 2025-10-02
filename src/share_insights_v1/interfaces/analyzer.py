from abc import ABC, abstractmethod
from typing import Dict, Any

class IAnalyzer(ABC):
    """Interface for financial analysis methods"""
    
    @abstractmethod
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform analysis and return results"""
        pass
    
    @abstractmethod
    def is_applicable(self, company_type: str) -> bool:
        """Check if this analyzer applies to the company type"""
        pass
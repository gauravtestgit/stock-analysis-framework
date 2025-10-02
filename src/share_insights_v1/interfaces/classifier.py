from abc import ABC, abstractmethod
from typing import Dict, Any

class ICompanyClassifier(ABC):
    """Interface for classifying companies"""
    
    @abstractmethod
    def classify(self, ticker: str, metrics: Dict[str, Any]) -> str:
        """Classify company type based on financial metrics"""
        pass
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IRecommendationEngine(ABC):
    """Interface for generating investment recommendations"""
    
    @abstractmethod
    def generate_recommendation(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate final recommendation from multiple analyses"""
        pass
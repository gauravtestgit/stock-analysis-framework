from abc import ABC, abstractmethod
from typing import Dict, Any

class ICalculator(ABC):
    """Interface for financial calculations"""
    
    @abstractmethod
    def calculate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform calculation and return result"""
        pass
"""Core interfaces for the financial analysis system"""

from .data_provider import IDataProvider
from .analyzer import IAnalyzer
from .calculator import ICalculator
from .recommendation import IRecommendationEngine
from .classifier import ICompanyClassifier

__all__ = [
    'IDataProvider',
    'IAnalyzer', 
    'ICalculator',
    'IRecommendationEngine',
    'ICompanyClassifier'
]
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class AnalysisType(Enum):
    """Types of analysis that can be performed"""
    DCF = "dcf"
    TECHNICAL = "technical"
    COMPARABLE = "comparable"
    STARTUP = "startup"
    AI_INSIGHTS = "ai_insights"
    NEWS_SENTIMENT = "news_sentiment"
    BUSINESS_MODEL = "business_model"
    COMPETITIVE_POSITION = "competitive_position"
    MANAGEMENT_QUALITY = "management_quality"
    FINANCIAL_HEALTH = "financial_health"
    ANALYST_CONSENSUS = "analyst_consensus"
    REVENUE_STREAM = "revenue_stream"  # New analyzer

@dataclass
class AnalysisResult:
    """Result of a single analysis"""
    analysis_type: AnalysisType
    ticker: str
    result: Dict[str, Any]
    error: Optional[str] = None
    execution_time: Optional[float] = None
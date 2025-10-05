from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class AnalysisType(Enum):
    DCF = "dcf"
    TECHNICAL = "technical"
    COMPARABLE = "comparable"
    STARTUP = "startup"
    ANALYST_CONSENSUS = "analyst_consensus"
    AI_INSIGHTS = "ai_insights"
    QUALITY = "quality"

@dataclass
class AnalysisResult:
    analysis_type: AnalysisType
    ticker: str
    result: Dict[str, Any]
    confidence: str = "Medium"
    error: Optional[str] = None
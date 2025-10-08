from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

class CompetitiveStrength(Enum):
    DOMINANT = "Dominant"
    STRONG = "Strong" 
    MODERATE = "Moderate"
    WEAK = "Weak"
    VULNERABLE = "Vulnerable"

class ThreatLevel(Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"

@dataclass
class CompetitiveAdvantage:
    advantage_type: str
    strength: CompetitiveStrength
    description: str
    sustainability: float  # 0-1 score

@dataclass
class CompetitiveThreat:
    threat_type: str
    level: ThreatLevel
    description: str
    timeline: str  # "Immediate", "Near-term", "Long-term"

@dataclass
class MarketPosition:
    market_share_estimate: Optional[float]
    market_rank_estimate: Optional[int]
    growth_vs_market: Optional[float]
    competitive_strength: CompetitiveStrength

@dataclass
class CompetitivePositionReport:
    ticker: str
    market_position: MarketPosition
    competitive_advantages: List[CompetitiveAdvantage]
    competitive_threats: List[CompetitiveThreat]
    overall_position_score: float  # 0-10
    position_trend: str  # "Strengthening", "Stable", "Weakening"
    key_differentiators: List[str]
    strategic_risks: List[str]
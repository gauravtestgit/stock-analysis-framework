from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional

class ManagementQuality(Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    AVERAGE = "Average"
    POOR = "Poor"
    CONCERNING = "Concerning"

class GovernanceRisk(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"

@dataclass
class ExecutiveProfile:
    name: str
    title: str
    total_compensation: Optional[float]
    age: Optional[int]

@dataclass
class GovernanceMetrics:
    compensation_risk: Optional[int]
    board_risk: Optional[int]
    audit_risk: Optional[int]
    overall_risk: Optional[int]
    insider_ownership_pct: Optional[float]
    institutional_ownership_pct: Optional[float]

@dataclass
class ManagementQualityReport:
    ticker: str
    overall_quality_score: float  # 0-10
    management_quality: ManagementQuality
    governance_risk: GovernanceRisk
    executive_profiles: List[ExecutiveProfile]
    governance_metrics: GovernanceMetrics
    strengths: List[str]
    concerns: List[str]
    key_insights: List[str]
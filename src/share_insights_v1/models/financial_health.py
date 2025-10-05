from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class FinancialHealthGrade(Enum):
    EXCELLENT = "A+"
    VERY_GOOD = "A"
    GOOD = "B+"
    FAIR = "B"
    POOR = "C"
    VERY_POOR = "D"

@dataclass
class CashFlowMetrics:
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    cash_conversion_ratio: Optional[float] = None  # OCF / Net Income
    capex_intensity: Optional[float] = None  # Capex / Revenue

@dataclass
class DebtMetrics:
    total_debt: Optional[float] = None
    net_debt: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    debt_maturity_profile: Optional[Dict[str, float]] = None

@dataclass
class RevenueQuality:
    revenue_growth_3yr: Optional[float] = None
    revenue_consistency: Optional[float] = None  # Std dev of quarterly growth
    recurring_revenue_pct: Optional[float] = None
    customer_concentration: Optional[float] = None  # Top 10 customers %

@dataclass
class FinancialHealthReport:
    ticker: str
    filing_date: Optional[str] = None
    cash_flow_metrics: Optional[CashFlowMetrics] = None
    debt_metrics: Optional[DebtMetrics] = None
    revenue_quality: Optional[RevenueQuality] = None
    overall_grade: Optional[FinancialHealthGrade] = None
    key_risks: Optional[list] = None
    strengths: Optional[list] = None
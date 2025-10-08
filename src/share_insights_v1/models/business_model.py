from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class RevenueStreamType(Enum):
    PRODUCT_SALES = "Product Sales"
    SUBSCRIPTION = "Subscription"
    LICENSING = "Licensing"
    SERVICES = "Services"
    ADVERTISING = "Advertising"
    TRANSACTION_FEES = "Transaction Fees"
    INTEREST_INCOME = "Interest Income"
    RENTAL_INCOME = "Rental Income"
    MIXED = "Mixed"

class BusinessModelType(Enum):
    B2B_SAAS = "B2B SaaS"
    B2C_SUBSCRIPTION = "B2C Subscription"
    MARKETPLACE = "Marketplace"
    TRADITIONAL_RETAIL = "Traditional Retail"
    MANUFACTURING = "Manufacturing"
    FINANCIAL_SERVICES = "Financial Services"
    ADVERTISING_BASED = "Advertising Based"
    ASSET_HEAVY = "Asset Heavy"
    PLATFORM = "Platform"

class RevenueQuality(Enum):
    EXCELLENT = "Excellent"  # High recurring, predictable
    GOOD = "Good"           # Some recurring, stable
    FAIR = "Fair"           # Mixed, moderate volatility
    POOR = "Poor"           # Cyclical, unpredictable

@dataclass
class RevenueStreamAnalysis:
    primary_stream: RevenueStreamType
    secondary_streams: List[RevenueStreamType]
    recurring_percentage: Optional[float] = None
    revenue_concentration: Optional[float] = None  # Geographic/customer concentration
    seasonality_factor: Optional[float] = None
    growth_consistency: Optional[float] = None

@dataclass
class BusinessModelReport:
    ticker: str
    business_model_type: BusinessModelType
    revenue_stream_analysis: RevenueStreamAnalysis
    revenue_quality: RevenueQuality
    key_metrics: Dict[str, float]
    strengths: List[str]
    risks: List[str]
    competitive_moat: str
    scalability_score: float  # 0-10 scale
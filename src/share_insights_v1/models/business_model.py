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
    BRANDED_STAPLES_FRANCHISE = "Branded Staples Franchise"
    PASS_THROUGH_OPERATOR = "Pass-Through Operator"

    # One member per remaining archetype.md archetype (see
    # src/share_insights_v1/archetypes/*.yaml), named after each archetype's
    # own `id` and valued from its own `name` - lets BusinessModelAnalyzer's
    # _ARCHETYPE_BUSINESS_MODEL_TYPES override the generic sector/industry
    # Type for any confidently-classified company, not just the original 2
    # archetypes. Confirmed this was missing for PRDO specifically: a 0.95-
    # confidence policy_funded_service classification still left Type as
    # the generic sector/industry-derived "B2C Subscription".
    ASSET_MANAGER_SERVICES = "Asset Manager / External Manager"
    BANK_DEPOSIT_LENDER = "Bank / Deposit Lender"
    CLINICAL_STAGE_BIOTECH = "Clinical-Stage Biotech"
    COMMODITY_PROCESSOR = "Commodity Processor"
    COMMODITY_PRODUCER = "Commodity Producer"
    CONSUMER_DISCRETIONARY_BRAND = "Consumer Discretionary Brand"
    CYCLICAL_TRANSPORT = "Cyclical Transport"
    DEFENSE_GOVERNMENT_CONTRACTOR = "Defense / Government Contractor"
    DIVERSIFIED_HOLDING = "Diversified Holding Company"
    DIVERSIFIED_PHARMA_MEDTECH = "Diversified Pharma / Medtech"
    FRANCHISOR = "Franchisor"
    INDUSTRIAL_CYCLICAL = "Industrial Cyclical Manufacturer"
    INSURER = "Insurer"
    MARKETPLACE_PLATFORM = "Marketplace Platform"
    MERCHANT_POWER_ENERGY = "Merchant Power & Energy"
    PAYMENTS_FINTECH = "Payments / Fintech"
    PLATFORM_MULTI_SEGMENT = "Ad-Funded Multi-Segment Platform"
    POLICY_FUNDED_SERVICE = "Policy-Funded Service"
    REAL_ESTATE_OWNER = "Real Estate Owner"
    REGULATED_UTILITY = "Regulated Utility"
    RESTAURANT_OPERATOR = "Restaurant Operator (Company-Operated)"
    RETAILER = "Retailer"
    SEMICONDUCTOR_HARDWARE = "Semiconductor / Hardware"
    SINGLE_ASSET_PHARMA = "Single-Asset Pharma"
    SOFTWARE_SAAS = "Software / SaaS"
    SPECIALTY_LENDER = "Specialty Lender"
    STAFFING_BUSINESS_SERVICES = "Staffing / Business Services"
    SUBSCRIPTION_MEDIA_ROYALTY = "Subscription Media / Royalty"
    TELECOM_OPERATOR = "Telecom Operator"

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
from enum import Enum
from dataclasses import dataclass

class CompanyType(Enum):
    MATURE_PROFITABLE = "mature_profitable"
    GROWTH_PROFITABLE = "growth_profitable"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"
    STARTUP_LOSS_MAKING = "startup_loss_making"
    REIT = "reit"
    FINANCIAL = "financial"
    COMMODITY = "commodity"
    ETF = "etf"

@dataclass
class Company:
    ticker: str
    name: str = ""
    company_type: CompanyType = None
    sector: str = ""
    industry: str = ""
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class RelativePosition(Enum):
    PREMIUM = "Premium"  # Above peer average
    DISCOUNT = "Discount"  # Below peer average
    INLINE = "Inline"  # Close to peer average

@dataclass
class PeerMetrics:
    ticker: str
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    price_to_book: Optional[float] = None
    roe: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    market_cap: Optional[float] = None

@dataclass
class PeerComparison:
    target_ticker: str
    peer_tickers: List[str]
    target_metrics: PeerMetrics
    peer_metrics: List[PeerMetrics]
    sector_averages: Dict[str, float]
    relative_position: Dict[str, RelativePosition]
    valuation_summary: str
    key_insights: List[str]
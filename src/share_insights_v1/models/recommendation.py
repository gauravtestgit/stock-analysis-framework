from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum

class RecommendationType(Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"
    SPECULATIVE_BUY = "Speculative Buy"
    MONITOR = "Monitor"

@dataclass
class Recommendation:
    ticker: str
    recommendation: RecommendationType
    confidence: str
    target_price: float = None
    upside_potential: float = None
    risk_level: str = "Medium"
    bullish_signals: List[str] = None
    bearish_signals: List[str] = None
    key_risks: List[str] = None
    summary: str = ""
    
    def __post_init__(self):
        if self.bullish_signals is None:
            self.bullish_signals = []
        if self.bearish_signals is None:
            self.bearish_signals = []
        if self.key_risks is None:
            self.key_risks = []
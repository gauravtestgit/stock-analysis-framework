from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

class SentimentScore(Enum):
    VERY_POSITIVE = "Very Positive"
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"
    VERY_NEGATIVE = "Very Negative"

class NewsCategory(Enum):
    EARNINGS = "Earnings"
    PRODUCT_LAUNCH = "Product Launch"
    MANAGEMENT_CHANGE = "Management Change"
    REGULATORY = "Regulatory"
    MARKET_EXPANSION = "Market Expansion"
    FINANCIAL_PERFORMANCE = "Financial Performance"
    STRATEGIC_PARTNERSHIP = "Strategic Partnership"
    GENERAL = "General"

@dataclass
class NewsItem:
    title: str
    summary: str
    category: NewsCategory
    sentiment_score: float  # -1 to 1
    confidence: float  # 0 to 1
    date: str
    source: str
    url: Optional[str] = None
    sentiment: Optional[str] = None

@dataclass
class SentimentTrend:
    period: str  # "7d", "30d", "90d"
    average_sentiment: float
    sentiment_direction: str  # "Improving", "Stable", "Declining"
    news_volume: int

@dataclass
class NewsSentimentReport:
    ticker: str
    overall_sentiment_score: float  # -1 to 1
    sentiment_rating: SentimentScore
    recent_news: List[NewsItem]
    sentiment_trends: List[SentimentTrend]
    key_developments: List[str]
    sentiment_drivers: List[str]
    risk_factors: List[str]
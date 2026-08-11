from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enum import Enum

class AnalysisRequest(BaseModel):
    ticker: str
    enabled_analyzers: Optional[List[str]] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    max_news_articles: Optional[int] = 5

class DCFScenarioRequest(BaseModel):
    """Overrides for a user-defined DCF scenario - only DCFAnalyzer runs, no other
    analyzers, no DB writes. Fields left as None fall back to the ticker's normal
    sector/quality-adjusted Base Case values."""
    max_cagr_threshold: Optional[float] = None
    default_terminal_growth: Optional[float] = None
    max_terminal_value_ratio: Optional[float] = None
    default_ev_ebitda_multiple: Optional[float] = None
    risk_free_rate_override: Optional[float] = None

class DCFScenarioResponse(BaseModel):
    ticker: str
    scenario: Dict[str, Any]

class AnalysisResponse(BaseModel):
    ticker: str
    company_type: str
    analyses: Dict[str, Any]
    financial_metrics: Optional[Dict[str, Any]] = None
    final_recommendation: Optional[Dict[str, Any]] = None
    status: str = "completed"
    batch_analysis_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"

class AnalyzerInfo(BaseModel):
    name: str
    enabled: bool
    applicable_to: List[str]

class ConfigResponse(BaseModel):
    analyzers: List[AnalyzerInfo]

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
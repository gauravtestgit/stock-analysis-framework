from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enum import Enum

class AnalysisRequest(BaseModel):
    ticker: str
    enabled_analyzers: Optional[List[str]] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    max_news_articles: Optional[int] = 5

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
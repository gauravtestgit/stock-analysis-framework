from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from enum import Enum

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class BatchAnalysisRequest(BaseModel):
    enabled_analyzers: Optional[List[str]] = None
    job_name: Optional[str] = None

class BatchJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_tickers: int
    completed_tickers: int
    failed_tickers: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    job_name: Optional[str] = None

class BatchResultsResponse(BaseModel):
    job_id: str
    status: JobStatus
    results: Dict[str, Any]
    summary: Dict[str, Any]
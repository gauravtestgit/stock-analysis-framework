from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.share_insights_v1.services.storage.historical_analysis_service import HistoricalAnalysisService

router = APIRouter()

@router.get("/history/{ticker}")
async def get_stock_history(ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get historical analysis data for a stock"""
    try:
        service = HistoricalAnalysisService()
        return service.get_stock_history(ticker.upper(), limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{ticker}/timeline")
async def get_recommendation_timeline(ticker: str) -> List[Dict[str, Any]]:
    """Get recommendation timeline for a stock"""
    try:
        service = HistoricalAnalysisService()
        return service.get_recommendation_timeline(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{ticker}/methods")
async def get_method_performance(ticker: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get analysis method performance for a stock"""
    try:
        service = HistoricalAnalysisService()
        return service.get_method_performance(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{ticker}/theses")
async def get_thesis_evolution(ticker: str) -> List[Dict[str, Any]]:
    """Get thesis evolution for a stock"""
    try:
        service = HistoricalAnalysisService()
        return service.get_thesis_evolution(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/bulk/analysis")
async def get_bulk_analysis(exchange: str = None, batch_job_id: str = None) -> Dict[str, Any]:
    """Get bulk analysis data for dashboard"""
    try:
        service = HistoricalAnalysisService()
        return service.get_bulk_analysis_data(exchange, batch_job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/bulk/exchanges")
async def get_available_exchanges() -> Dict[str, Any]:
    """Get available exchanges from database"""
    try:
        service = HistoricalAnalysisService()
        return service.get_available_exchanges()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/bulk/jobs")
async def get_batch_jobs(exchange: str = None) -> List[Dict[str, Any]]:
    """Get all batch jobs for an exchange"""
    try:
        service = HistoricalAnalysisService()
        return service.get_batch_jobs_by_exchange(exchange)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
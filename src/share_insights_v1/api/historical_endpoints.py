from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.database.database_service import DatabaseService

router = APIRouter()

@router.get("/api/history/{ticker}/timeline")
async def get_recommendation_timeline(ticker: str):
    """Get recommendation timeline for a ticker"""
    try:
        db_service = DatabaseService()
        analyses = db_service.get_analysis_history(ticker, limit=50)
        
        timeline = []
        for analysis in analyses:
            if analysis.get('final_recommendation'):
                rec = analysis['final_recommendation']
                timeline.append({
                    'date': analysis['created_at'].isoformat(),
                    'recommendation': rec.get('recommendation', 'N/A'),
                    'target_price': rec.get('target_price', 0),
                    'current_price': analysis.get('current_price', 0),
                    'confidence': rec.get('confidence', 'N/A')
                })
        
        return timeline
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history/{ticker}/methods")
async def get_method_performance(ticker: str):
    """Get method performance data for a ticker"""
    try:
        db_service = DatabaseService()
        analyses = db_service.get_analysis_history(ticker, limit=50)
        
        methods = {}
        for analysis in analyses:
            if analysis.get('analyses'):
                for method, data in analysis['analyses'].items():
                    if method not in methods:
                        methods[method] = []
                    
                    methods[method].append({
                        'date': analysis['created_at'].isoformat(),
                        'recommendation': data.get('recommendation', 'N/A'),
                        'target_price': data.get('predicted_price', 0),
                        'confidence': data.get('confidence', 'N/A')
                    })
        
        return methods
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history/{ticker}/theses")
async def get_thesis_evolution(ticker: str):
    """Get thesis evolution for a ticker"""
    try:
        from services.storage.thesis_storage_service import ThesisStorageService
        
        storage_service = ThesisStorageService()
        theses = storage_service.get_thesis_history(ticker, limit=20)
        
        thesis_data = []
        for thesis in theses:
            thesis_data.append({
                'date': thesis['created_at'].isoformat(),
                'thesis_type': thesis['thesis_type'],
                'llm_provider': thesis['llm_provider'],
                'llm_model': thesis['llm_model'],
                'content_preview': thesis['content'][:200] + '...',
                'batch_analysis_id': thesis.get('batch_analysis_id')
            })
        
        return thesis_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
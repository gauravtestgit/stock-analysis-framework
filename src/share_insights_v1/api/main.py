from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional, List
import logging

from .models import AnalysisRequest, AnalysisResponse, HealthResponse, ConfigResponse, ErrorResponse, AnalyzerInfo
from .batch_models import BatchJobResponse, BatchResultsResponse
from .service import AnalysisService
from .batch_service import BatchAnalysisService
from ..services.storage.thesis_storage_service import ThesisStorageService
from .historical_analysis import router as historical_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Stock Analysis API",
    description="Comprehensive stock analysis framework with multiple analyzers",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
analysis_service = AnalysisService(save_to_db=True)  # Default: save to database
batch_service = BatchAnalysisService()  # Uses flag in constructor
thesis_service = ThesisStorageService()

# Include routers
app.include_router(historical_router, prefix="/api", tags=["historical"])

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy")

@app.post("/analyze/{ticker}", response_model=AnalysisResponse)
async def analyze_stock(ticker: str, request: AnalysisRequest = None):
    """Analyze a single stock with comprehensive analysis"""
    try:
        # Use ticker from path, override request ticker if provided
        actual_ticker = ticker.upper()
        
        # Get enabled analyzers from request or use all
        enabled_analyzers = None
        if request and request.enabled_analyzers:
            enabled_analyzers = request.enabled_analyzers
        
        # Get LLM configuration from request
        llm_provider = None
        llm_model = None
        max_news_articles = 5  # Default value
        if request:
            llm_provider = request.llm_provider
            llm_model = request.llm_model
            if request.max_news_articles is not None:
                max_news_articles = request.max_news_articles
        
        logger.info(f"Starting analysis for {actual_ticker}")
        if llm_provider and llm_model:
            logger.info(f"Using LLM: {llm_provider} with {llm_model}")
        else:
            logger.info("No LLM configuration provided - using default")
        
        # Create service with custom max_news_articles if different from default
        if max_news_articles != 5:
            custom_service = AnalysisService(save_to_db=True, max_news_articles=max_news_articles)
            result = await custom_service.analyze_stock(actual_ticker, enabled_analyzers, llm_provider, llm_model)
        else:
            # Use default service
            result = await analysis_service.analyze_stock(actual_ticker, enabled_analyzers, llm_provider, llm_model)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return AnalysisResponse(
            ticker=actual_ticker,
            company_type=result.get('company_type', 'unknown'),
            analyses=result.get('analyses', {}),
            financial_metrics=result.get('financial_metrics'),
            final_recommendation=result.get('final_recommendation'),
            status="completed",
            batch_analysis_id=result.get('batch_analysis_id')
        )
        
    except Exception as e:
        logger.error(f"Analysis failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyzers", response_model=ConfigResponse)
async def get_analyzers():
    """Get list of available analyzers"""
    try:
        analyzers_info = analysis_service.get_available_analyzers()
        return ConfigResponse(analyzers=analyzers_info)
    except Exception as e:
        logger.error(f"Failed to get analyzers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/company/{ticker}/classify")
async def classify_company(ticker: str):
    """Get company type classification"""
    try:
        result = await analysis_service.classify_company(ticker.upper())
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    except Exception as e:
        logger.error(f"Classification failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/company/{ticker}/quality")
async def get_quality_score(ticker: str):
    """Get quality score only"""
    try:
        result = await analysis_service.get_quality_score(ticker.upper())
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        return result
    except Exception as e:
        logger.error(f"Quality score failed for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch/upload")
async def create_batch_analysis(
    file: UploadFile = File(...),
    enabled_analyzers: Optional[str] = Form(None),
    job_name: Optional[str] = Form(None)
):
    """Upload CSV file and create batch analysis job"""
    print(f"🚀 Batch upload endpoint called with file: {file.filename}")
    logger.info(f"Batch upload endpoint called with file: {file.filename}")
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Read CSV content
        csv_content = await file.read()
        csv_text = csv_content.decode('utf-8')
        
        # Parse enabled analyzers if provided
        analyzers_list = None
        if enabled_analyzers:
            analyzers_list = [a.strip() for a in enabled_analyzers.split(',')]
        print(f"Enabled Analyzers: {analyzers_list}")
        # Create batch job
        job_id = batch_service.create_batch_job(csv_text, analyzers_list, job_name)
        
        # Start processing
        started = await batch_service.start_batch_job(job_id)
        if not started:
            raise HTTPException(status_code=500, detail="Failed to start batch job")
        
        logger.info(f"Started batch job {job_id}")
        
        return {"job_id": job_id, "message": "Batch analysis started"}
        
    except Exception as e:
        logger.error(f"Batch analysis creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batch/{job_id}/status", response_model=BatchJobResponse)
async def get_batch_job_status(job_id: str):
    """Get status of a batch analysis job"""
    try:
        status = batch_service.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batch/{job_id}/results", response_model=BatchResultsResponse)
async def get_batch_job_results(job_id: str):
    """Get results of a completed batch analysis job"""
    try:
        results = batch_service.get_job_results(job_id)
        if not results:
            raise HTTPException(status_code=404, detail="Job not found")
        return results
    except Exception as e:
        logger.error(f"Failed to get job results for {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batch/jobs", response_model=List[BatchJobResponse])
async def list_batch_jobs():
    """List all batch analysis jobs"""
    try:
        return batch_service.list_jobs()
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thesis_history/{ticker}")
async def get_thesis_history(ticker: str, limit: int = 10):
    """Get thesis history for a ticker"""
    try:
        history = thesis_service.get_thesis_history(ticker.upper(), limit)
        return {"ticker": ticker.upper(), "history": history}
    except Exception as e:
        logger.error(f"Failed to get thesis history for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/watchlist")
async def analyze_watchlist(tickers: List[str], created_by: str = "dashboard"):
    """Analyze multiple stocks as a batch job"""
    try:
        result = await analysis_service.analyze_watchlist(tickers, created_by)
        return result
    except Exception as e:
        logger.error(f"Watchlist analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
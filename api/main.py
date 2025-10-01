from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

from src.financial_analyst.stock_analyzer import StockAnalyzer, FinanceConfig

app = FastAPI(title="Stock Analysis API", version="1.0.0")

class AnalysisRequest(BaseModel):
    ticker: str
    config: Optional[dict] = None

class BatchAnalysisRequest(BaseModel):
    tickers: List[str]
    config: Optional[dict] = None

@app.get("/")
async def root():
    print('root')
    return {"message": "Stock Analysis API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    print('health_check')
    return {"status": "healthy"}

@app.post("/analyze/batch")
async def analyze_batch(request: BatchAnalysisRequest):
    """Analyze multiple stocks"""
    print('analyze batch request')
    try:
        results = []
        print("==========Batch Request Start==========")
        print(request)
        print("==========Batch Request End==========")
        # Create config if provided
        finance_config = FinanceConfig()
        if request.config:
            for key, value in request.config.items():
                if hasattr(finance_config, key):
                    setattr(finance_config, key, value)
        
        for ticker in request.tickers:
            try:
                analyzer = StockAnalyzer(ticker.upper(), finance_config)
                analysis = analyzer.comprehensive_analysis()
                
                results.append({
                    "ticker": ticker.upper(),
                    "status": "success",
                    "analysis": analysis
                })
                
            except Exception as e:
                results.append({
                    "ticker": ticker.upper(),
                    "status": "error",
                    "error": str(e)
                })
        print(len(request.tickers))
        return {
            "status": "completed",
            "total_requested": len(request.tickers),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")

@app.post("/analyze/{ticker}")
async def analyze_stock(ticker: str, config: Optional[dict] = None):
    """Analyze a single stock"""
    print('analyze ticker')
    try:
        # Create config if provided
        finance_config = FinanceConfig()
        if config:
            for key, value in config.items():
                if hasattr(finance_config, key):
                    setattr(finance_config, key, value)
        
        # Run analysis
        analyzer = StockAnalyzer(ticker.upper(), finance_config)
        analysis = analyzer.comprehensive_analysis()
        
        return {
            "ticker": ticker.upper(),
            "status": "success",
            "analysis": analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/analyze")
async def analyze_stock_body(request: AnalysisRequest):
    """Analyze a single stock with request body"""
    print('analyze single request body')
    return await analyze_stock(request.ticker, request.config)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
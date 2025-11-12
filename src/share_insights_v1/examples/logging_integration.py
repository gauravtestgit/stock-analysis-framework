"""
Examples of how to integrate logging into existing components
"""

# Example 1: DCF Analyzer with logging
from ..implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ..utils.logging_decorators import log_analysis
from ..utils.logger import get_logger

class LoggedDCFAnalyzer(DCFAnalyzer):
    """DCF Analyzer with integrated logging"""
    
    @log_analysis("DCF")
    def analyze(self, ticker: str, data: dict) -> dict:
        logger = get_logger()
        
        # Log input data quality
        quality_grade = data.get('quality_grade', 'Unknown')
        company_type = data.get('company_type', 'Unknown')
        
        logger.info(
            f"DCF analysis input data",
            ticker=ticker,
            quality_grade=quality_grade,
            company_type=str(company_type),
            event_type="dcf_input"
        )
        
        try:
            result = super().analyze(ticker, data)
            
            # Log key results
            if 'predicted_price' in result:
                logger.info(
                    f"DCF valuation completed",
                    ticker=ticker,
                    predicted_price=result['predicted_price'],
                    current_price=result.get('current_price'),
                    upside_downside=result.get('upside_downside_pct'),
                    recommendation=result.get('recommendation'),
                    event_type="dcf_result"
                )
            
            return result
            
        except Exception as e:
            logger.error(
                f"DCF analysis failed",
                ticker=ticker,
                error_type=type(e).__name__,
                error_message=str(e),
                event_type="dcf_error"
            )
            raise

# Example 2: API Endpoint with logging
from fastapi import APIRouter
from ..utils.logging_decorators import log_api_endpoint
from ..utils.logger import log_api_request

router = APIRouter()

@router.post("/analyze/{ticker}")
@log_api_endpoint("/analyze/{ticker}")
async def analyze_stock_logged(ticker: str, user_id: str = None):
    """Stock analysis endpoint with logging"""
    logger = get_logger()
    
    # Log request details
    log_api_request(f"/analyze/{ticker}", "POST", user_id, {"ticker": ticker})
    
    try:
        # Your existing analysis logic here
        result = {"message": f"Analysis for {ticker} completed"}
        
        logger.info(
            f"Stock analysis successful",
            ticker=ticker,
            user_id=user_id,
            event_type="analysis_success"
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Stock analysis failed",
            ticker=ticker,
            user_id=user_id,
            error_message=str(e),
            event_type="analysis_failure"
        )
        raise

# Example 3: Batch Processing with logging
from ..utils.logging_decorators import log_batch_operation
from ..utils.logger import get_logger, log_batch_job

class LoggedBatchProcessor:
    """Batch processor with comprehensive logging"""
    
    @log_batch_operation("stock_batch_analysis")
    def process_stock_list(self, stock_list: list, job_id: str, user_id: str = None):
        logger = get_logger()
        
        logger.info(
            f"Starting batch processing",
            job_id=job_id,
            stock_count=len(stock_list),
            user_id=user_id,
            event_type="batch_start"
        )
        
        results = []
        failed_stocks = []
        
        for i, ticker in enumerate(stock_list):
            try:
                # Log progress every 10 stocks
                if i % 10 == 0:
                    progress = (i / len(stock_list)) * 100
                    logger.info(
                        f"Batch progress update",
                        job_id=job_id,
                        progress_percent=progress,
                        processed_count=i,
                        total_count=len(stock_list),
                        event_type="batch_progress"
                    )
                
                # Process individual stock
                result = self._analyze_single_stock(ticker)
                results.append(result)
                
            except Exception as e:
                failed_stocks.append(ticker)
                logger.warning(
                    f"Stock analysis failed in batch",
                    job_id=job_id,
                    ticker=ticker,
                    error_message=str(e),
                    event_type="batch_stock_error"
                )
        
        # Log final results
        logger.info(
            f"Batch processing completed",
            job_id=job_id,
            total_stocks=len(stock_list),
            successful_count=len(results),
            failed_count=len(failed_stocks),
            failed_stocks=failed_stocks,
            event_type="batch_summary"
        )
        
        return {
            'processed_count': len(results),
            'failed_count': len(failed_stocks),
            'results': results,
            'failed_stocks': failed_stocks
        }
    
    def _analyze_single_stock(self, ticker: str):
        """Analyze single stock (placeholder)"""
        # Your analysis logic here
        return {"ticker": ticker, "status": "completed"}
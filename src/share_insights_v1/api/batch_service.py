import asyncio
import uuid
import os
import io
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import json

from .batch_models import JobStatus, BatchJobResponse, BatchResultsResponse
from .service import AnalysisService

class BatchJob:
    """Represents a batch analysis job"""
    
    def __init__(self, job_id: str, tickers: List[str], enabled_analyzers: Optional[List[str]] = None, job_name: Optional[str] = None):
        self.job_id = job_id
        self.tickers = tickers
        self.enabled_analyzers = enabled_analyzers
        self.job_name = job_name
        self.status = JobStatus.PENDING
        self.total_tickers = len(tickers)
        self.completed_tickers = 0
        self.failed_tickers = 0
        self.results = {}
        self.errors = {}
        self.created_at = datetime.now().isoformat()
        self.started_at = None
        self.completed_at = None
        self.csv_output_path = None
        self.csv_file = None

class BatchAnalysisService:
    """Service for handling batch stock analysis"""
    
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.jobs: Dict[str, BatchJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=3)  # Limit concurrent analyses
    
    def create_batch_job(self, csv_content: str, enabled_analyzers: Optional[List[str]] = None, job_name: Optional[str] = None) -> str:
        """Create a new batch job from CSV content"""
        # Parse CSV to extract tickers
        tickers = self._parse_csv_tickers(csv_content)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job
        job = BatchJob(job_id, tickers, enabled_analyzers, job_name)
        self.jobs[job_id] = job
        
        return job_id
    
    def _parse_csv_tickers(self, csv_content: str) -> List[str]:
        """Parse CSV content to extract ticker symbols"""
        df = pd.read_csv(io.StringIO(csv_content))
        # Get first column (ticker symbols)
        tickers = df.iloc[:, 0].astype(str).str.strip().str.upper().tolist()
        return list(set(tickers))  # Remove duplicates
    
    async def start_batch_job(self, job_id: str) -> bool:
        """Start processing a batch job"""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        if job.status != JobStatus.PENDING:
            return False
        
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now().isoformat()
        
        # Initialize CSV file
        job.csv_output_path = self._initialize_csv_output(job)
        
        # Start processing in background
        asyncio.create_task(self._process_batch_job(job))
        
        return True
    
    async def _process_batch_job(self, job: BatchJob):
        """Process all tickers in a batch job"""
        try:
            # Process tickers in batches to avoid overwhelming the system
            batch_size = 5
            for i in range(0, len(job.tickers), batch_size):
                batch_tickers = job.tickers[i:i + batch_size]
                
                # Process batch concurrently
                tasks = [
                    self._analyze_single_ticker(job, ticker)
                    for ticker in batch_tickers
                ]
                
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Close CSV file
            self._close_csv_output(job)
            
            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now().isoformat()
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.errors['job_error'] = str(e)
            # Close CSV file on error
            self._close_csv_output(job)
    
    async def _analyze_single_ticker(self, job: BatchJob, ticker: str):
        """Analyze a single ticker within a batch job"""
        try:
            print(f"🔄 Analyzing {ticker}...")
            result = await self.analysis_service.analyze_stock(ticker, job.enabled_analyzers)
            
            if 'error' in result:
                print(f"❌ Error for {ticker}: {result['error']}")
                job.errors[ticker] = result['error']
                job.failed_tickers += 1
            else:
                print(f"✅ Success for {ticker}, calling _write_csv_row")
                job.results[ticker] = result
                job.completed_tickers += 1
                # Write to CSV immediately
                self._write_csv_row(job, ticker, result)
                
        except Exception as e:
            print(f"💥 Exception for {ticker}: {str(e)}")
            job.errors[ticker] = str(e)
            job.failed_tickers += 1
    
    def get_job_status(self, job_id: str) -> Optional[BatchJobResponse]:
        """Get status of a batch job"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return BatchJobResponse(
            job_id=job.job_id,
            status=job.status,
            total_tickers=job.total_tickers,
            completed_tickers=job.completed_tickers,
            failed_tickers=job.failed_tickers,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            job_name=job.job_name
        )
    
    def get_job_results(self, job_id: str) -> Optional[BatchResultsResponse]:
        """Get results of a completed batch job"""
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        
        # Generate summary
        summary = self._generate_batch_summary(job)
        
        # Convert numpy types to native Python types
        serializable_results = self._make_serializable(job.results)
        serializable_errors = self._make_serializable(job.errors)
        serializable_summary = self._make_serializable(summary)
        
        return BatchResultsResponse(
            job_id=job.job_id,
            status=job.status,
            results={
                'analyses': serializable_results,
                'errors': serializable_errors,
                'csv_output_path': job.csv_output_path
            },
            summary=serializable_summary
        )
    
    def _generate_batch_summary(self, job: BatchJob) -> Dict[str, Any]:
        """Generate summary statistics for batch job"""
        if not job.results:
            return {}
        
        # Count recommendations
        recommendations = {}
        company_types = {}
        
        for ticker, result in job.results.items():
            # Only process if result is a dict (successful analysis)
            if isinstance(result, dict):
                # Count final recommendations
                final_rec = result.get('final_recommendation', {})
                rec = final_rec.get('recommendation', 'Unknown')
                recommendations[rec] = recommendations.get(rec, 0) + 1
                
                # Count company types
                company_type = result.get('company_type', 'Unknown')
                company_types[company_type] = company_types.get(company_type, 0) + 1
        
        return {
            'total_analyzed': len(job.results),
            'total_failed': len(job.errors),
            'success_rate': len(job.results) / job.total_tickers * 100 if job.total_tickers > 0 else 0,
            'recommendations_breakdown': recommendations,
            'company_types_breakdown': company_types,
            'processing_time': self._calculate_processing_time(job)
        }
    
    def _calculate_processing_time(self, job: BatchJob) -> Optional[str]:
        """Calculate total processing time"""
        if not job.started_at or not job.completed_at:
            return None
        
        start = datetime.fromisoformat(job.started_at)
        end = datetime.fromisoformat(job.completed_at)
        duration = end - start
        
        return str(duration)
    
    def _make_serializable(self, obj):
        """Convert numpy types and other non-serializable types to native Python types"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_serializable(item) for item in obj)
        elif hasattr(obj, 'dtype'):  # Any numpy type
            if obj.dtype == bool:
                return bool(obj)
            elif np.issubdtype(obj.dtype, np.integer):
                return int(obj)
            elif np.issubdtype(obj.dtype, np.floating):
                return float(obj)
            else:
                return str(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif str(type(obj)).startswith("<class 'numpy."):
            # Catch any remaining numpy types
            try:
                return obj.item()  # Convert to Python scalar
            except:
                return str(obj)
        elif isinstance(obj, (int, float, str, bool)) or obj is None:
            return obj
        else:
            # Convert any other object to string
            return str(obj)
    
    def _initialize_csv_output(self, job: BatchJob) -> str:
        """Initialize CSV file for incremental writing"""
        output_dir = "src/share_insights_v1/resources/stock_analyses"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_analysis_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # Create CSV file with headers
        df_header = pd.DataFrame(columns=[
            'Ticker', 'Current_Price', 'DCF_Price', 'Comparable_Price', 'Technical_Price',
            'AI_Insights_Price', 'Analyst_Price', 'Final_Recommendation', 'Analyst_Recommendation',
            'Company_Type', 'Sector', 'Industry', 'Quality_Score'
        ])
        df_header.to_csv(filepath, index=False)
        
        return filepath
    
    def _write_csv_row(self, job: BatchJob, ticker: str, result: Dict[str, Any]):
        """Write a single row to CSV file immediately"""
        row_data = self._extract_csv_data(ticker, result)
        df_row = pd.DataFrame([row_data])
        df_row.to_csv(job.csv_output_path, mode='a', header=False, index=False)
        print(f"✅ Written CSV row for {ticker}")
    
    def _close_csv_output(self, job: BatchJob):
        """Close CSV output (no-op for pandas approach)"""
        print(f"📁 CSV completed: {job.csv_output_path}")
    
    def _extract_csv_data(self, ticker: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract CSV data from analysis result"""
        def get_value(data, path, default=None):
            try:
                for key in path:
                    data = data[key]
                return data if data is not None else default
            except (KeyError, TypeError):
                return default
        
        analyses = result.get('analyses', {})
        
        return {
            'Ticker': ticker,
            'Current_Price': get_value(result, ['financial_metrics', 'current_price'], 0),
            'DCF_Price': get_value(analyses, ['dcf', 'predicted_price'], 0),
            'Comparable_Price': get_value(analyses, ['comparable', 'predicted_price'], 0),
            'Technical_Price': get_value(analyses, ['technical', 'predicted_price'], 0),
            'AI_Insights_Price': get_value(analyses, ['ai_insights', 'predicted_price'], 0),
            'Analyst_Price': get_value(analyses, ['analyst_consensus', 'predicted_price'], 0),
            'Final_Recommendation': get_value(result, ['final_recommendation', 'recommendation'], 'Hold'),
            'Analyst_Recommendation': get_value(analyses, ['analyst_consensus', 'recommendation'], 'N/A'),
            'Company_Type': get_value(result, ['company_type'], 'Unknown'),
            'Sector': get_value(result, ['financial_metrics', 'sector'], 'N/A'),
            'Industry': get_value(result, ['financial_metrics', 'industry'], 'N/A'),
            'Quality_Score': get_value(result, ['quality_score'], 'D')
        }
    
    def list_jobs(self) -> List[BatchJobResponse]:
        """List all batch jobs"""
        return [
            BatchJobResponse(
                job_id=job.job_id,
                status=job.status,
                total_tickers=job.total_tickers,
                completed_tickers=job.completed_tickers,
                failed_tickers=job.failed_tickers,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                job_name=job.job_name
            )
            for job in self.jobs.values()
        ]

if __name__ == "__main__":
    import asyncio
    
    async def debug_batch_service():
        """Debug function to test batch service independently"""
        print("🚀 Starting batch service debug...")
        
        # Create service
        service = BatchAnalysisService()
        
        # Test CSV content
        csv_content = """Symbol,Security Name
AAPL,Apple Inc.
MSFT,Microsoft
NVDA, Nvidia
"""
        
        print("📄 Creating batch job...")
        job_id = service.create_batch_job(csv_content, job_name="Debug Test")
        print(f"✅ Created job: {job_id}")
        
        # Check initial status
        status = service.get_job_status(job_id)
        print(f"📊 Initial status: {status.status}")
        
        # Start job
        print("▶️ Starting batch job...")
        started = await service.start_batch_job(job_id)
        print(f"✅ Job started: {started}")
        
        # Monitor progress
        while True:
            status = service.get_job_status(job_id)
            print(f"📊 Status: {status.status}, Completed: {status.completed_tickers}/{status.total_tickers}")
            
            if status.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                break
            
            await asyncio.sleep(2)
        
        # Get results
        print("📋 Getting results...")
        results = service.get_job_results(job_id)
        if results:
            print(f"✅ Results: {len(results.results.get('analyses', {}))} analyses")
            print(f"📁 CSV file: {results.results.get('csv_output_path')}")
            
            # Print first result for debugging
            analyses = results.results.get('analyses', {})
            if analyses:
                first_ticker = list(analyses.keys())[0]
                first_result = analyses[first_ticker]
                print(f"🔍 First result ({first_ticker}):")
                print(f"  - Keys: {list(first_result.keys())}")
                print(f"  - Final rec: {first_result.get('final_recommendation', {}).get('recommendation')}")
        else:
            print("❌ No results found")
    
    # Run debug
    asyncio.run(debug_batch_service())
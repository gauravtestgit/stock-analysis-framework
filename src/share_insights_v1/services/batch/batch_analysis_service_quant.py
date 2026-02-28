import pandas as pd
import csv
import logging
import uuid
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from ..orchestration.analysis_orchestrator import AnalysisOrchestrator
from ..storage.analysis_storage_service import AnalysisStorageService
from ...implementations.data_providers.yahoo_provider import YahooFinanceProvider
from...implementations.classifier import CompanyClassifier
from ...implementations.calculators.quality_calculator import QualityScoreCalculator
from ...implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ...implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ...implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ...implementations.analyzers.startup_analyzer import StartupAnalyzer
from ...implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ...implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ...models.analysis_result import AnalysisType
from ...config.config import FinanceConfig
from datetime import datetime, timezone

class BatchAnalysisService:
    """Service to run batch analysis on multiple stocks from CSV"""
    
    def __init__(self, save_to_db: bool = False, enable_detailed_news_analysis: bool = True, max_workers: int = 4):
        self.data_provider = YahooFinanceProvider()
        self.classifier = CompanyClassifier()
        self.quality_calculator = QualityScoreCalculator()
        self.config = FinanceConfig()
        self.save_to_db = save_to_db
        self.storage_service = AnalysisStorageService() if save_to_db else None
        self.failure_log_path = None
        self.batch_job_id = None
        self.max_workers = max_workers
        self.csv_lock = threading.Lock()
        self.log_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.completed = 0
        self.failed = 0
        
        self.orchestrator = AnalysisOrchestrator(
            self.data_provider, self.classifier, self.quality_calculator
        )
        self.enable_detailed_news_analysis = enable_detailed_news_analysis
        self._register_analyzers()    


    def _register_analyzers(self):
        """Register all available analyzers"""
        # Initialize LLM manager for qualitative analyzers
        from ...implementations.llm_providers.llm_manager import LLMManager
        try:
            llm_manager = LLMManager(use_plugin_system=True)
        except Exception:
            llm_manager = LLMManager()  # Fallback to legacy
        
        # Register quantitative analyzers
        self.orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer(self.config))
        self.orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
        self.orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer(self.config))
        self.orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer(self.config))
        self.orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(self.data_provider))
        
        # # Register qualitative analyzers with LLM support
        # self.orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(data_provider=self.data_provider, llm_manager=llm_manager))
        
        # # Import and register news sentiment analyzer
        # from ...implementations.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
        # if self.enable_detailed_news_analysis:
        #     self.orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(self.data_provider, llm_manager))
        # else:
        #     self.orchestrator.register_analyzer(AnalysisType.NEWS_SENTIMENT, NewsSentimentAnalyzer(self.data_provider, enable_web_scraping=False))
        
        # # Import and register additional qualitative analyzers
        # from ...implementations.analyzers.business_model_analyzer import BusinessModelAnalyzer
        # from ...implementations.analyzers.competitive_position_analyzer import CompetitivePositionAnalyzer
        # from ...implementations.analyzers.management_quality_analyzer import ManagementQualityAnalyzer
        
        # self.orchestrator.register_analyzer(AnalysisType.BUSINESS_MODEL, BusinessModelAnalyzer(self.data_provider, llm_manager))
        # self.orchestrator.register_analyzer(AnalysisType.COMPETITIVE_POSITION, CompetitivePositionAnalyzer(self.data_provider))
        # self.orchestrator.register_analyzer(AnalysisType.MANAGEMENT_QUALITY, ManagementQualityAnalyzer(self.data_provider))
        
        # # Import and register SEC-based analyzer
        # from ...implementations.analyzers.financial_health_analyzer import FinancialHealthAnalyzer
        # from ...implementations.data_providers.sec_edgar_provider import SECEdgarProvider
        # sec_provider = SECEdgarProvider()
        # self.orchestrator.register_analyzer(AnalysisType.FINANCIAL_HEALTH, FinancialHealthAnalyzer(sec_provider))
        
        # # Import and register industry analysis
        # from ...implementations.analyzers.industry_analysis_analyzer import IndustryAnalysisAnalyzer
        # self.orchestrator.register_analyzer(AnalysisType.INDUSTRY_ANALYSIS, IndustryAnalysisAnalyzer(self.data_provider))
    
    def _process_single_stock(self, ticker: str) -> tuple:
        """Process a single stock (thread worker)"""
        try:
            analysis_result = self.orchestrator.analyze_stock(ticker)
            
            if 'error' not in analysis_result:
                csv_row = self._extract_csv_data(ticker, analysis_result)
                
                if self.save_to_db and self.storage_service:
                    try:
                        batch_analysis_id = self.storage_service.store_comprehensive_analysis(
                            ticker, analysis_result, batch_job_id=self.batch_job_id
                        )
                        return ('success', ticker, csv_row)
                    except Exception as db_error:
                        with self.log_lock:
                            self._log_failure(ticker, "DB_STORAGE_ERROR", str(db_error))
                        return ('failed', ticker, csv_row)
                else:
                    return ('success', ticker, csv_row)
            else:
                csv_row = self._create_error_row(ticker, analysis_result['error'])
                with self.log_lock:
                    self._log_failure(ticker, "ANALYSIS_ERROR", analysis_result['error'])
                return ('failed', ticker, csv_row)
                
        except Exception as e:
            csv_row = self._create_error_row(ticker, str(e))
            with self.log_lock:
                self._log_failure(ticker, "EXCEPTION", str(e))
            return ('failed', ticker, csv_row)
    
    def process_csv(self, input_csv_path: str, output_csv_path: str, max_stocks: int = None, exchange: str = None, created_by: str = "system"):
        """Process stocks from CSV using multiple threads"""
        
        df = pd.read_csv(input_csv_path, keep_default_na=False, na_values=[''])
        
        if max_stocks:
            df = df.head(max_stocks)
        
        total_stocks = len(df)
        print(f"Processing {total_stocks} stocks with {self.max_workers} threads...")
        
        if self.save_to_db and self.storage_service:
            self.batch_job_id = self._create_batch_job(
                name=f"{exchange or 'Mixed'} Analysis {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                exchange=exchange or "Mixed",
                total_stocks=total_stocks,
                input_file=input_csv_path,
                output_file=output_csv_path,
                created_by=created_by
            )
            print(f"Batch job created: {self.batch_job_id}")
        
        self._initialize_csv(output_csv_path)
        self._initialize_failure_log(output_csv_path)
        
        time_start = datetime.now()
        self.completed = 0
        self.failed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for idx, row in df.iterrows():
                symbol = row['Symbol']
                if pd.isna(symbol) or not isinstance(symbol, str) or not symbol.strip():
                    print(f"Skipping invalid symbol at row {idx}: {symbol}")
                    continue
                futures[executor.submit(self._process_single_stock, symbol.strip().upper())] = idx
            
            for future in as_completed(futures):
                status, ticker, csv_row = future.result()
                
                with self.csv_lock:
                    self._append_to_csv(csv_row, output_csv_path)
                
                with self.progress_lock:
                    if status == 'success':
                        self.completed += 1
                    else:
                        self.failed += 1
                    
                    count = self.completed + self.failed
                    if count >= 2:
                        time_diff = datetime.now() - time_start
                        time_per_stock = time_diff / count
                        time_remaining = time_per_stock * (total_stocks - count)
                        print(f"Processed {ticker} ({count}/{total_stocks}). ETA: {time_remaining}", end='\r', flush=True)
                    else:
                        print(f"Processed {ticker} ({count}/{total_stocks})...", end='\r', flush=True)
                    
                    if self.save_to_db and self.batch_job_id:
                        self._update_batch_job_progress(self.completed, self.failed)
        
        if self.save_to_db and self.batch_job_id:
            self._complete_batch_job()
        
        print(f"\nResults saved to {output_csv_path}")
        if self.failure_log_path:
            print(f"Failure log saved to {self.failure_log_path}")
    
    def _extract_csv_data(self, ticker: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data for CSV output"""
        
        financial_metrics = analysis_result.get('financial_metrics', {})
        analyses = analysis_result.get('analyses', {})
        final_rec = analysis_result.get('final_recommendation', {})
        
        current_price = financial_metrics.get('current_price', 0)
        dcf_price = analyses.get('dcf', {}).get('predicted_price', 0)
        technical_price = analyses.get('technical', {}).get('predicted_price', 0)
        comparable_price = analyses.get('comparable', {}).get('predicted_price', 0)
        startup_price = analyses.get('startup', {}).get('predicted_price', 0)
        analyst_price = analyses.get('analyst_consensus', {}).get('predicted_price', 0)
        analyst_count = analyses.get('analyst_consensus', {}).get('num_analysts', 0)
                
        # dcf_rec = analyses.get('dcf', {}).get('recommendation', '')
        # technical_rec = analyses.get('technical', {}).get('recommendation', '')
        # comparable_rec = analyses.get('comparable', {}).get('recommendation', '')
        # startup_rec = analyses.get('startup', {}).get('recommendation', '')
        # ai_rec = analyses.get('ai_insights', {}).get('recommendation', '')
        analyst_rec = analyses.get('analyst_consensus', {}).get('recommendation', '')


        if hasattr(final_rec, 'recommendation'):
            final_recommendation = final_rec.recommendation.value if hasattr(final_rec.recommendation, 'value') else str(final_rec.recommendation)
        else:
            final_recommendation = str(final_rec.get('recommendation_type', ''))
        
        return {
            'Ticker': ticker,
            'Current_Price': f"${current_price:.2f}" if current_price else "$0.00",
            'DCF_Price': f"${dcf_price:.2f}" if dcf_price else "$0.00",
            'Technical_Price': f"${technical_price:.2f}" if technical_price else "$0.00",
            'Comparable_Price': f"${comparable_price:.2f}" if comparable_price else "$0.00",
            'Startup_Price': f"${startup_price:.2f}" if startup_price else "$0.00",
            'Analyst_Price': f"${analyst_price:.2f}" if analyst_price else "$0.00",
            'Professional_Analyst_Recommendation': analyst_rec,
            'Analyst_Count': analyst_count or 0,
            'Final_Recommendation': final_recommendation,
            'Company_Type': analysis_result.get('company_type', ''),
            'Sector': financial_metrics.get('sector', ''),
            'Industry': financial_metrics.get('industry', ''),
            'Quality_Grade': analysis_result.get('quality_score', {}).get('grade', ''),
            'Error': ''
        }
    
    def _create_error_row(self, ticker: str, error: str) -> Dict[str, Any]:
        """Create error row for failed analysis"""
        return {
            'Ticker': ticker,
            'Current_Price': "$0.00",
            'DCF_Price': "$0.00",
            'Technical_Price': "$0.00",
            'Comparable_Price': "$0.00",
            'Startup_Price': "$0.00",
            'Analyst_Price': "$0.00",
            'Professional_Analyst_Recommendation': 'Error',
            'Analyst_Count': 0,
            'Final_Recommendation': 'Error',
            'Company_Type': '',
            'Sector': '',
            'Industry': '',
            'Quality_Grade': '',
            'Error': error
        }
    
    def _initialize_csv(self, output_path: str):
        """Initialize CSV file with headers"""
        fieldnames = [
            'Ticker', 'Current_Price', 'DCF_Price', 'Technical_Price', 'Comparable_Price',
            'Startup_Price', 'Analyst_Price', 'Professional_Analyst_Recommendation', 
            'Analyst_Count','Final_Recommendation',
            'Company_Type', 'Sector', 'Industry', 'Quality_Grade', 'Error'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    
    def _append_to_csv(self, row: Dict[str, Any], output_path: str):
        """Append single row to CSV file"""
        fieldnames = [
            'Ticker', 'Current_Price', 'DCF_Price', 'Technical_Price', 'Comparable_Price',
            'Startup_Price', 'Analyst_Price', 'Professional_Analyst_Recommendation','Analyst_Count', 'Final_Recommendation',
            'Company_Type', 'Sector', 'Industry', 'Quality_Grade', 'Error'
        ]
        
        with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(row)
    
    def _initialize_failure_log(self, output_csv_path: str):
        """Initialize failure log file"""
        base_name = output_csv_path.replace('.csv', '')
        self.failure_log_path = f"{base_name}_failures.txt"
        
        with open(self.failure_log_path, 'w', encoding='utf-8') as f:
            f.write(f"BATCH ANALYSIS FAILURE LOG\n")
            f.write(f"Started: {datetime.now()}\n")
            f.write(f"Output CSV: {output_csv_path}\n")
            f.write(f"Database Storage: {'Enabled' if self.save_to_db else 'Disabled'}\n")
            f.write("=" * 80 + "\n\n")
    
    def _log_failure(self, ticker: str, error_type: str, error_message: str):
        """Log failure to text file"""
        if not self.failure_log_path:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.failure_log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {ticker} - {error_type}\n")
            f.write(f"Error: {error_message}\n")
            f.write("-" * 40 + "\n\n")
    
    def _create_batch_job(self, name: str, exchange: str, total_stocks: int, input_file: str, output_file: str, created_by: str) -> uuid.UUID:
        """Create a new batch job in database"""
        from ...models.database import SessionLocal
        from ...models.strategy_models import BatchJob
        
        db = SessionLocal()
        try:
            batch_job = BatchJob(
                name=name,
                exchange=exchange,
                status="running",
                total_stocks=total_stocks,
                completed_stocks=0,
                failed_stocks=0,
                input_file=input_file,
                output_file=output_file,
                created_by=created_by
            )
            db.add(batch_job)
            db.commit()
            db.refresh(batch_job)
            return batch_job.id
        finally:
            db.close()
    
    def _update_batch_job_progress(self, completed: int, failed: int):
        """Update batch job progress"""
        from ...models.database import SessionLocal
        from ...models.strategy_models import BatchJob
        
        db = SessionLocal()
        try:
            batch_job = db.query(BatchJob).filter(BatchJob.id == self.batch_job_id).first()
            if batch_job:
                batch_job.completed_stocks = completed
                batch_job.failed_stocks = failed
                db.commit()
        finally:
            db.close()
    
    def _complete_batch_job(self):
        """Mark batch job as completed"""
        from ...models.database import SessionLocal
        from ...models.strategy_models import BatchJob
        
        db = SessionLocal()
        try:
            batch_job = db.query(BatchJob).filter(BatchJob.id == self.batch_job_id).first()
            if batch_job:
                batch_job.status = "completed"
                batch_job.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
import pandas as pd
import csv
from typing import Dict, Any, List
from ..orchestration.analysis_orchestrator import AnalysisOrchestrator
from ...implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ...implementations.classifier import CompanyClassifier
from ...implementations.calculators.quality_calculator import QualityScoreCalculator
from ...implementations.analyzers.dcf_analyzer import DCFAnalyzer
from ...implementations.analyzers.technical_analyzer import TechnicalAnalyzer
from ...implementations.analyzers.comparable_analyzer import ComparableAnalyzer
from ...implementations.analyzers.startup_analyzer import StartupAnalyzer
from ...implementations.analyzers.analyst_consensus_analyzer import AnalystConsensusAnalyzer
from ...implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ...models.analysis_result import AnalysisType
from ...config.config import FinanceConfig
from datetime import datetime

class BatchAnalysisService:
    """Service to run batch analysis on multiple stocks from CSV"""
    
    def __init__(self):
        self.data_provider = YahooFinanceProvider()
        self.classifier = CompanyClassifier()
        self.quality_calculator = QualityScoreCalculator()
        self.config = FinanceConfig()
        
        self.orchestrator = AnalysisOrchestrator(
            self.data_provider, self.classifier, self.quality_calculator
        )
        
        self._register_analyzers()
    
    def _register_analyzers(self):
        """Register all available analyzers"""
        self.orchestrator.register_analyzer(AnalysisType.DCF, DCFAnalyzer(self.config))
        self.orchestrator.register_analyzer(AnalysisType.TECHNICAL, TechnicalAnalyzer())
        self.orchestrator.register_analyzer(AnalysisType.COMPARABLE, ComparableAnalyzer(self.config))
        self.orchestrator.register_analyzer(AnalysisType.STARTUP, StartupAnalyzer(self.config))
        self.orchestrator.register_analyzer(AnalysisType.ANALYST_CONSENSUS, AnalystConsensusAnalyzer(self.data_provider))
        # self.orchestrator.register_analyzer(AnalysisType.AI_INSIGHTS, AIInsightsAnalyzer(data_provider=self.data_provider))
    
    def process_csv(self, input_csv_path: str, output_csv_path: str, max_stocks: int = None):
        """Process stocks from CSV and save results to CSV"""
        
        df = pd.read_csv(input_csv_path)
        
        if max_stocks:
            df = df.head(max_stocks)
        
        total_stocks = len(df)
        print(f"Processing {total_stocks} stocks...")
        
        # Initialize CSV file with headers
        self._initialize_csv(output_csv_path)
        
        time_start = datetime.now()
        count = 0
        
        for idx, row in df.iterrows():
            
            count += 1
            try:

                ticker = row['Symbol'].strip().upper()
                if count >= 2:
                    time_diff = datetime.now() - time_start
                    time_per_stock = time_diff / (count - 1)
                    time_remaining = time_per_stock * (total_stocks - count)
                    print(f"Processing {ticker} ({idx+1}/{total_stocks}). ETA: {time_remaining}", end='\r', flush=True)
                else:
                    print(f"Processing {ticker} ({idx+1}/{total_stocks})...", end='\r', flush=True)
            
            
                
                analysis_result = self.orchestrator.analyze_stock(ticker)
                
                if 'error' not in analysis_result:
                    csv_row = self._extract_csv_data(ticker, analysis_result)
                else:
                    csv_row = self._create_error_row(ticker, analysis_result['error'])
                    
            except Exception as e:
                csv_row = self._create_error_row('error',str(e))
            
            # Write immediately to CSV
            self._append_to_csv(csv_row, output_csv_path)
        
        print(f"\nResults saved to {output_csv_path}")
    
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
            'Startup_Price', 'Analyst_Price', 'Professional_Analyst_Recommendation', 'Final_Recommendation',
            'Company_Type', 'Sector', 'Industry', 'Quality_Grade', 'Error'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    
    def _append_to_csv(self, row: Dict[str, Any], output_path: str):
        """Append single row to CSV file"""
        fieldnames = [
            'Ticker', 'Current_Price', 'DCF_Price', 'Technical_Price', 'Comparable_Price',
            'Startup_Price', 'Analyst_Price', 'Professional_Analyst_Recommendation', 'Final_Recommendation',
            'Company_Type', 'Sector', 'Industry', 'Quality_Grade', 'Error'
        ]
        
        with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writerow(row)
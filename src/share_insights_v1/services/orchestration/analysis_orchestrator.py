from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...interfaces.classifier import ICompanyClassifier
from ...interfaces.calculator import ICalculator
from ...models.company import CompanyType, Company
from ...models.analysis_result import AnalysisResult, AnalysisType
from ..recommendation.recommendation_service import RecommendationService
from ..comparison.analyst_comparison_service import AnalystComparisonService

class AnalysisOrchestrator:
    """Orchestrates multiple analyzers based on company type"""
    
    def __init__(self, data_provider: IDataProvider, classifier: ICompanyClassifier, quality_calculator: ICalculator):
        self.data_provider = data_provider
        self.classifier = classifier
        self.quality_calculator = quality_calculator
        self.recommendation_service = RecommendationService()
        self.comparison_service = AnalystComparisonService(data_provider)
        self.analyzers: Dict[AnalysisType, IAnalyzer] = {}
    
    def register_analyzer(self, analysis_type: AnalysisType, analyzer: IAnalyzer):
        """Register an analyzer for a specific analysis type"""
        self.analyzers[analysis_type] = analyzer
    
    def analyze_stock(self, ticker: str) -> Dict[str, Any]:
        """Run comprehensive analysis for a stock"""
        start_time = time.time()
        try:
            # Get financial data
            financial_metrics = self.data_provider.get_financial_metrics(ticker)
            price_data = self.data_provider.get_price_data(ticker)
            
            if 'error' in financial_metrics:
                return {'error': f"Failed to get financial data: {financial_metrics['error']}"}
            
            # Classify company
            company_type_raw = self.classifier.classify(ticker, financial_metrics)
            # Ensure we have the string value for comparisons
            company_type = company_type_raw.value if hasattr(company_type_raw, 'value') else company_type_raw
            
            # Calculate quality score first (needed for other analyses)
            # quality_result = self.quality_calculator.calculate({'financial_metrics': financial_metrics})
            quality_result = self.quality_calculator.calculate(financial_metrics)
            quality_grade = quality_result.get('grade', 'C')
            
            # Prepare analysis data with quality grade
            analysis_data = {
                'financial_metrics': financial_metrics,
                'price_data': price_data,
                'company_info': {
                    'sector': financial_metrics.get('sector', ''),
                    'industry': financial_metrics.get('industry', ''),
                },
                'company_type': company_type,
                'current_price': financial_metrics.get('current_price', 0),
                'quality_grade': quality_grade
            }
            
            # Determine which analyses to run (only registered ones that are applicable)
            applicable_analyses = self._get_applicable_analyses_for_type(company_type)
            analyses_to_run = [analysis_type for analysis_type in applicable_analyses if analysis_type in self.analyzers]
            
            # Run registered analyses in parallel
            results = {
                'ticker': ticker,
                'company_type': company_type,
                'financial_metrics': financial_metrics,
                'quality_score': quality_result,
                'analyses': {}
            }
            
            # Execute analyses in parallel
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Submit only registered analyses
                future_to_analysis = {
                    executor.submit(self._run_analysis, analysis_type, ticker, analysis_data): analysis_type
                    for analysis_type in analyses_to_run
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_analysis):
                    analysis_type = future_to_analysis[future]
                    try:
                        result = future.result()
                        results['analyses'][analysis_type.value] = result
                    except Exception as e:
                        results['analyses'][analysis_type.value] = {
                            'error': f"{analysis_type.value} analysis failed: {str(e)}",
                            'analysis_type': analysis_type.value
                        }
            
            # Generate consolidated recommendation if we have analyses
            if results['analyses']:
                company = Company(
                    ticker=ticker,
                    name=financial_metrics.get('long_name', ticker),
                    company_type=CompanyType(company_type)
                )
                final_recommendation = self.recommendation_service.generate_recommendation(company, results['analyses'])
                results['final_recommendation'] = final_recommendation
                
                # Compare against professional analysts
                analyst_comparisons = self.comparison_service.compare_analysis_results(ticker, results)
                if analyst_comparisons:
                    results['analyst_comparison'] = {
                        'comparisons': analyst_comparisons,
                        'summary': self.comparison_service.generate_comparison_summary(analyst_comparisons)
                    }
            
            # Add execution timing
            execution_time = time.time() - start_time
            results['execution_time_seconds'] = round(execution_time, 2)
            results['analyses_count'] = len(results['analyses'])
            
            return results
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'error': f"Analysis orchestration failed: {str(e)}",
                'execution_time_seconds': round(execution_time, 2)
            }
    
    def _run_analysis(self, analysis_type: AnalysisType, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific analysis and handle errors"""
        try:
            analyzer = self.analyzers[analysis_type]
            
            # Check if analyzer is applicable
            company_type = data.get('company_type', CompanyType.MATURE_PROFITABLE.value)
            if hasattr(analyzer, 'is_applicable') and not analyzer.is_applicable(company_type):
                return {'applicable': False, 'reason': f'{analysis_type.value} not applicable to {company_type}'}
            
            # Run analysis
            result = analyzer.analyze(ticker, data)
            result['analysis_type'] = analysis_type.value
            return result
            
        except Exception as e:
            return {
                'error': f"{analysis_type.value} analysis failed: {str(e)}",
                'analysis_type': analysis_type.value
            }
    
    def _get_applicable_analyses_for_type(self, company_type: str) -> List[AnalysisType]:
        """Get list of applicable analysis types for a company type"""
        # Always applicable analyses
        applicable = [
            AnalysisType.TECHNICAL,
            AnalysisType.AI_INSIGHTS,
            AnalysisType.NEWS_SENTIMENT,
            AnalysisType.BUSINESS_MODEL,
            AnalysisType.COMPETITIVE_POSITION,
            AnalysisType.MANAGEMENT_QUALITY,
            AnalysisType.FINANCIAL_HEALTH,
            AnalysisType.ANALYST_CONSENSUS
        ]
        
        # Type-specific analyses
        if company_type == CompanyType.STARTUP_LOSS_MAKING.value:
            applicable.append(AnalysisType.STARTUP)
        elif company_type in [
            CompanyType.MATURE_PROFITABLE.value,
            CompanyType.GROWTH_PROFITABLE.value,
            CompanyType.TURNAROUND.value,
            CompanyType.CYCLICAL.value,
            CompanyType.COMMODITY.value,
            CompanyType.REIT.value
        ]:
            applicable.extend([AnalysisType.DCF, AnalysisType.COMPARABLE])
        elif company_type == CompanyType.FINANCIAL.value:
            applicable.append(AnalysisType.COMPARABLE)
        
        return applicable
    
    def get_applicable_analyses(self, company_type: str) -> List[AnalysisType]:
        """Public method to get applicable analyses (for external use)"""
        return self._get_applicable_analyses_for_type(company_type)
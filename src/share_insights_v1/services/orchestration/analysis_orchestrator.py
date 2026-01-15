from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import time
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...interfaces.classifier import ICompanyClassifier
from ...interfaces.calculator import ICalculator
from ...models.company import CompanyType, Company
from ...models.analysis_result import AnalysisResult, AnalysisType
from ..recommendation.recommendation_service import RecommendationService
from ..comparison.analyst_comparison_service import AnalystComparisonService
from ...utils.debug_printer import debug_print
from datetime import datetime

class AnalysisOrchestrator:
    """Orchestrates multiple analyzers based on company type"""
    
    def __init__(self, data_provider: IDataProvider, classifier: ICompanyClassifier, quality_calculator: ICalculator, debug_mode: bool = False):
        self.data_provider = data_provider
        self.classifier = classifier
        self.quality_calculator = quality_calculator
        self.recommendation_service = RecommendationService()
        self.comparison_service = AnalystComparisonService(data_provider)
        self.analyzers: Dict[AnalysisType, IAnalyzer] = {}
        self.debug_mode = debug_mode
        self.time_calculations = {}
    
    def register_analyzer(self, analysis_type: AnalysisType, analyzer: IAnalyzer):
        """Register an analyzer for a specific analysis type"""
        self.analyzers[analysis_type] = analyzer
    
    def analyze_stock(self, ticker: str) -> Dict[str, Any]:
        """Run comprehensive analysis for a stock"""
        overall_start_time = datetime.now()
        try:
            # Get financial data
            start_time = datetime.now()
            financial_metrics = self.data_provider.get_financial_metrics(ticker)
            end_time = datetime.now()
            time_taken = (end_time - start_time).total_seconds()
            # debug_print(f"[Analysis_Orchestrator]: {ticker}: Time Taken for Financial Metrics: {time_taken}")
            self.time_calculations['financial_metrics'] = time_taken

            start_time = datetime.now()
            price_data = self.data_provider.get_price_data(ticker)
            end_time = datetime.now()
            time_taken = (end_time - start_time).total_seconds()
            # debug_print(f"[Analysis_Orchestrator]: {ticker}: Time Taken for Price Data: {time_taken}")
            self.time_calculations['price_data'] = time_taken

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
            
            # Separate industry analysis from other analyses (needs other results as input)
            industry_analysis_type = AnalysisType.INDUSTRY_ANALYSIS
            other_analyses = [a for a in analyses_to_run if a != industry_analysis_type]
            
            # Execute other analyses in parallel first
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Submit non-industry analyses
                future_to_analysis = {
                    executor.submit(self._run_analysis, analysis_type, ticker, analysis_data): analysis_type
                    for analysis_type in other_analyses
                }
                
                # Collect results as they complete (with timeout)
                try:
                    for future in as_completed(future_to_analysis, timeout=60):  # Increased overall timeout
                        analysis_type = future_to_analysis[future]
                        try:
                            result = future.result(timeout=30)  # Increased per-analyzer timeout
                            if result and not result.get('error'):
                                # Inject current_price into successful results
                                result['current_price'] = financial_metrics.get('current_price')
                                results['analyses'][analysis_type.value] = result
                                # print(f"✅ {analysis_type.value} completed successfully for {ticker}")
                            else:
                                results['analyses'][analysis_type.value] = result
                                # print(f"⚠️ {analysis_type.value} completed with issues for {ticker}: {result.get('error', 'Unknown issue')}")
                                # print(f"⚠️ {analysis_type.value} completed with issues for {ticker}: {result.get('error', 'Unknown issue')}")
                        except TimeoutError:
                            print(f"⏰ TIMEOUT: {analysis_type.value} timed out after 30s for {ticker}")
                            results['analyses'][analysis_type.value] = {
                                'error': f"{analysis_type.value} analysis timed out",
                                'analysis_type': analysis_type.value,
                                'applicable': False
                            }
                        except Exception as e:
                            print(f"❌ ERROR: {analysis_type.value} analysis failed for {ticker}: {str(e)}")
                            results['analyses'][analysis_type.value] = {
                                'error': f"{analysis_type.value} analysis failed: {str(e)}",
                                'analysis_type': analysis_type.value,
                                'applicable': False
                            }
                except TimeoutError:
                    print(f"⏰ TIMEOUT: Overall analysis timed out after 60s for {ticker}")
                    # Handle any remaining futures that didn't complete
                    for future, analysis_type in future_to_analysis.items():
                        if not future.done():
                            print(f"⏰ TIMEOUT: {analysis_type.value} did not complete for {ticker}")
                            results['analyses'][analysis_type.value] = {
                                'error': f"{analysis_type.value} analysis timed out",
                                'analysis_type': analysis_type.value,
                                'applicable': False
                            }
            
            # Now run industry analysis with other results as input
            if industry_analysis_type in analyses_to_run:
                # Add other analysis results to analysis_data for industry analyzer
                enhanced_analysis_data = analysis_data.copy()
                enhanced_analysis_data.update(results['analyses'])
                
                try:
                    industry_result = self._run_analysis(industry_analysis_type, ticker, enhanced_analysis_data)
                    if industry_result and not industry_result.get('error'):
                        industry_result['current_price'] = financial_metrics.get('current_price')
                        results['analyses'][industry_analysis_type.value] = industry_result
                except Exception as e:
                    print(f"❌ ERROR: {industry_analysis_type.value} analysis failed for {ticker}: {str(e)}")
                    results['analyses'][industry_analysis_type.value] = {
                        'error': f"{industry_analysis_type.value} analysis failed: {str(e)}",
                        'analysis_type': industry_analysis_type.value,
                        'applicable': False
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
            execution_time = (datetime.now() - start_time).total_seconds()
            results['execution_time_seconds'] = round(execution_time, 2)
            results['analyses_count'] = len(results['analyses'])
            debug_print(f"[Analysis_Orchestrator]: {ticker}: Time Taken for Overall Analysis: {execution_time}")
            debug_print(f"[Analysis_Orchestrator]: Key Transaction Times:\n")
            
            for transactions in self.time_calculations.keys():
                debug_print(f"[Analysis_Orchestrator]: {transactions}: {self.time_calculations[transactions]}")
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
                # print(f"INFO: {analysis_type.value} not applicable to {company_type} for {ticker}")
                return {'applicable': False, 'reason': f'{analysis_type.value} not applicable to {company_type}'}
            
            # Run analysis
            # print(f"🔄 Starting {analysis_type.value} for {ticker}")
            start_time = datetime.now()
            result = analyzer.analyze(ticker, data)
            end_time = datetime.now()
            total_time = (end_time - start_time).total_seconds()
            # debug_print(f"[Analysis_Orchestrator]: {ticker}: Time Taken for {analysis_type.value}: {total_time}")
            self.time_calculations[analysis_type.value] = total_time
            # # Check if result is valid
            # if not result or ('error' in result and result.get('applicable', True)):
            #     print(f"⚠️ WARNING: {analysis_type.value} returned invalid result for {ticker}: {result}")
            # else:
            #     print(f"✅ {analysis_type.value} analysis completed for {ticker}")
            
            result['analysis_type'] = analysis_type.value
            return result
            
        except Exception as e:
            print(f"ERROR in _run_analysis: {analysis_type.value} failed for {ticker}: {str(e)}")
            import traceback
            traceback.print_exc()
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
            AnalysisType.ANALYST_CONSENSUS,
            AnalysisType.REVENUE_STREAM,
            AnalysisType.INDUSTRY_ANALYSIS
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
        elif company_type == CompanyType.ETF.value:
            # ETFs get technical analysis and analyst consensus for price targets
            # No DCF/Comparable as ETFs don't have traditional financials
            pass  # Already have technical, analyst_consensus in always applicable
        
        return applicable
    
    def get_applicable_analyses(self, company_type: str) -> List[AnalysisType]:
        """Public method to get applicable analyses (for external use)"""
        return self._get_applicable_analyses_for_type(company_type)
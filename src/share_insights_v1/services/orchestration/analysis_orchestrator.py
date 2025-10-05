from typing import Dict, Any, List
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
            
            # Run applicable analyses
            results = {
                'ticker': ticker,
                'company_type': company_type,
                'financial_metrics': financial_metrics,
                'quality_score': quality_result,
                'analyses': {}
            }
            
            # Always run technical analysis (applies to all types)
            if AnalysisType.TECHNICAL in self.analyzers:
                technical_result = self._run_analysis(
                    AnalysisType.TECHNICAL, ticker, analysis_data
                )
                results['analyses']['technical'] = technical_result
            
            # Always run AI insights analysis (applies to all types)
            if AnalysisType.AI_INSIGHTS in self.analyzers:
                ai_result = self._run_analysis(
                    AnalysisType.AI_INSIGHTS, ticker, analysis_data
                )
                results['analyses']['ai_insights'] = ai_result
            
            # Run analyst consensus for all company types
            # if company_type != CompanyType.STARTUP_LOSS_MAKING.value and AnalysisType.ANALYST_CONSENSUS in self.analyzers:
            if AnalysisType.ANALYST_CONSENSUS in self.analyzers:
                analyst_result = self._run_analysis(
                    AnalysisType.ANALYST_CONSENSUS, ticker, analysis_data
                )
                results['analyses']['analyst_consensus'] = analyst_result
            
            # Run type-specific analyses (company_type is a string from classifier)
            if company_type == CompanyType.STARTUP_LOSS_MAKING.value:
                if AnalysisType.STARTUP in self.analyzers:
                    startup_result = self._run_analysis(
                        AnalysisType.STARTUP, ticker, analysis_data
                    )
                    results['analyses']['startup'] = startup_result
            
            elif company_type in [
                CompanyType.MATURE_PROFITABLE.value,
                CompanyType.GROWTH_PROFITABLE.value,
                CompanyType.TURNAROUND.value,
                CompanyType.CYCLICAL.value,
                CompanyType.COMMODITY.value,
                CompanyType.REIT.value
            ]:
                # Run DCF analysis (excludes financial companies)
                if AnalysisType.DCF in self.analyzers:
                    dcf_result = self._run_analysis(
                        AnalysisType.DCF, ticker, analysis_data
                    )
                    results['analyses']['dcf'] = dcf_result
                
                # Run comparable analysis
                if AnalysisType.COMPARABLE in self.analyzers:
                    comparable_result = self._run_analysis(
                        AnalysisType.COMPARABLE, ticker, analysis_data
                    )
                    results['analyses']['comparable'] = comparable_result
            
            elif company_type == CompanyType.FINANCIAL.value:
                # Financial companies: Only comparable analysis (DCF not applicable)
                if AnalysisType.COMPARABLE in self.analyzers:
                    comparable_result = self._run_analysis(
                        AnalysisType.COMPARABLE, ticker, analysis_data
                    )
                    results['analyses']['comparable'] = comparable_result
            
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
            
            return results
            
        except Exception as e:
            return {'error': f"Analysis orchestration failed: {str(e)}"}
    
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
    
    def get_applicable_analyses(self, company_type: str) -> List[AnalysisType]:
        """Get list of applicable analysis types for a company type"""
        applicable = [AnalysisType.TECHNICAL]  # Always applicable
        
        # Add analyst consensus for most company types
        if company_type != CompanyType.STARTUP_LOSS_MAKING.value:
            applicable.append(AnalysisType.ANALYST_CONSENSUS)
        
        # Add AI insights for all company types
        applicable.append(AnalysisType.AI_INSIGHTS)
        
        if company_type == CompanyType.STARTUP_LOSS_MAKING.value:
            applicable.append(AnalysisType.STARTUP)
        elif company_type != CompanyType.ETF.value and company_type != CompanyType.FINANCIAL.value:
            applicable.extend([AnalysisType.DCF, AnalysisType.COMPARABLE])
        elif company_type != CompanyType.ETF.value:
            applicable.append(AnalysisType.COMPARABLE)  # Comparable only for financial companies
        
        return applicable
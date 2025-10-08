from typing import Dict, Any, Optional
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.sec_data_provider import SECDataProvider
from ...models.financial_health import (
    FinancialHealthReport, CashFlowMetrics, DebtMetrics, 
    RevenueQuality, FinancialHealthGrade
)
from ...models.company import CompanyType

class FinancialHealthAnalyzer(IAnalyzer):
    """Analyzer for financial health from SEC filings"""
    
    def __init__(self, sec_provider: SECDataProvider):
        self.sec_provider = sec_provider
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze financial health using IAnalyzer interface"""
        try:
            health_report = self.analyze_financial_health(ticker)
            
            if not health_report:
                return {'error': 'Could not analyze financial health'}
            
            # Convert to standardized format
            return {
                'method': 'Financial Health Analysis',
                'applicable': True,
                'overall_grade': health_report.overall_grade.value if health_report.overall_grade else 'N/A',
                'filing_date': health_report.filing_date,
                'cash_flow_score': self._score_cash_flow(health_report.cash_flow_metrics),
                'debt_score': self._score_debt(health_report.debt_metrics),
                'revenue_score': self._score_revenue(health_report.revenue_quality),
                'key_risks': health_report.key_risks or [],
                'strengths': health_report.strengths or [],
                'confidence': 'High',
                'recommendation': self._generate_recommendation(health_report.overall_grade)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def is_applicable(self, company_type: str) -> bool:
        """Financial health analysis applies to most company types"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types
    
    def analyze_financial_health(self, ticker: str) -> Optional[FinancialHealthReport]:
        """Analyze financial health from SEC filings"""
        
        # Get company facts
        facts = self.sec_provider.get_filing_facts(ticker)
        if not facts:
            return None
        
        # Extract key metrics
        cash_flow_metrics = self._extract_cash_flow_metrics(facts)
        debt_metrics = self._extract_debt_metrics(facts)
        revenue_quality = self._extract_revenue_quality(facts)
        
        # Calculate overall grade
        overall_grade = self._calculate_overall_grade(cash_flow_metrics, debt_metrics, revenue_quality)
        
        # Identify risks and strengths
        key_risks, strengths = self._identify_risks_and_strengths(cash_flow_metrics, debt_metrics, revenue_quality)
        
        return FinancialHealthReport(
            ticker=ticker,
            filing_date=self._get_latest_filing_date(facts),
            cash_flow_metrics=cash_flow_metrics,
            debt_metrics=debt_metrics,
            revenue_quality=revenue_quality,
            overall_grade=overall_grade,
            key_risks=key_risks,
            strengths=strengths
        )
    
    def _extract_cash_flow_metrics(self, facts: Dict[str, Any]) -> CashFlowMetrics:
        """Extract cash flow metrics from SEC facts"""
        
        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        
        # Get latest annual values
        ocf = self._get_latest_annual_value(us_gaap.get('OperatingCashFlowsContinuingOperations', {}))
        if not ocf:
            ocf = self._get_latest_annual_value(us_gaap.get('NetCashProvidedByUsedInOperatingActivities', {}))
        
        capex = self._get_latest_annual_value(us_gaap.get('PaymentsToAcquirePropertyPlantAndEquipment', {}))
        net_income = self._get_latest_annual_value(us_gaap.get('NetIncomeLoss', {}))
        revenues = self._get_latest_annual_value(us_gaap.get('Revenues', {}))
        
        # Calculate derived metrics
        free_cash_flow = None
        if ocf and capex:
            free_cash_flow = ocf - abs(capex)
        
        cash_conversion_ratio = None
        if ocf and net_income and net_income != 0:
            cash_conversion_ratio = ocf / net_income
        
        capex_intensity = None
        if capex and revenues and revenues != 0:
            capex_intensity = abs(capex) / revenues
        
        return CashFlowMetrics(
            operating_cash_flow=ocf,
            free_cash_flow=free_cash_flow,
            cash_conversion_ratio=cash_conversion_ratio,
            capex_intensity=capex_intensity
        )
    
    def _extract_debt_metrics(self, facts: Dict[str, Any]) -> DebtMetrics:
        """Extract debt metrics from SEC facts"""
        
        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        
        # Get debt values
        total_debt = self._get_latest_annual_value(us_gaap.get('DebtCurrent', {}))
        long_term_debt = self._get_latest_annual_value(us_gaap.get('LongTermDebt', {}))
        
        if total_debt and long_term_debt:
            total_debt += long_term_debt
        elif long_term_debt and not total_debt:
            total_debt = long_term_debt
        
        cash = self._get_latest_annual_value(us_gaap.get('CashAndCashEquivalentsAtCarryingValue', {}))
        equity = self._get_latest_annual_value(us_gaap.get('StockholdersEquity', {}))
        interest_expense = self._get_latest_annual_value(us_gaap.get('InterestExpense', {}))
        ebit = self._get_latest_annual_value(us_gaap.get('OperatingIncomeLoss', {}))
        
        # Calculate derived metrics
        net_debt = None
        if total_debt and cash:
            net_debt = total_debt - cash
        
        debt_to_equity = None
        if total_debt and equity and equity != 0:
            debt_to_equity = total_debt / equity
        
        interest_coverage = None
        if ebit and interest_expense and interest_expense != 0:
            interest_coverage = ebit / interest_expense
        
        return DebtMetrics(
            total_debt=total_debt,
            net_debt=net_debt,
            debt_to_equity=debt_to_equity,
            interest_coverage=interest_coverage
        )
    
    def _extract_revenue_quality(self, facts: Dict[str, Any]) -> RevenueQuality:
        """Extract revenue quality metrics from SEC facts"""
        
        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        
        # Get revenue history for trend analysis
        revenues_data = us_gaap.get('Revenues', {}).get('units', {}).get('USD', [])
        
        # Calculate 3-year revenue growth
        revenue_growth_3yr = self._calculate_revenue_growth(revenues_data)
        
        return RevenueQuality(
            revenue_growth_3yr=revenue_growth_3yr
        )
    
    def _get_latest_annual_value(self, metric_data: Dict[str, Any]) -> Optional[float]:
        """Get latest annual value from SEC metric data"""
        
        units = metric_data.get('units', {}).get('USD', [])
        if not units:
            return None
        
        # Filter for annual filings (10-K)
        annual_values = [
            item for item in units 
            if item.get('form') == '10-K' and item.get('val') is not None
        ]
        
        if not annual_values:
            return None
        
        # Sort by end date and get latest
        annual_values.sort(key=lambda x: x.get('end', ''), reverse=True)
        return annual_values[0].get('val')
    
    def _calculate_revenue_growth(self, revenues_data: list) -> Optional[float]:
        """Calculate 3-year revenue CAGR"""
        
        annual_revenues = [
            item for item in revenues_data 
            if item.get('form') == '10-K' and item.get('val') is not None
        ]
        
        if len(annual_revenues) < 4:  # Need at least 4 years for 3-year growth
            return None
        
        annual_revenues.sort(key=lambda x: x.get('end', ''))
        
        current_revenue = annual_revenues[-1]['val']
        three_years_ago = annual_revenues[-4]['val']
        
        if three_years_ago <= 0:
            return None
        
        # Calculate CAGR
        return ((current_revenue / three_years_ago) ** (1/3)) - 1
    
    def _calculate_overall_grade(self, cash_flow: CashFlowMetrics, debt: DebtMetrics, revenue: RevenueQuality) -> FinancialHealthGrade:
        """Calculate overall financial health grade"""
        
        score = 0
        factors = 0
        
        # Cash flow scoring
        if cash_flow.cash_conversion_ratio:
            if cash_flow.cash_conversion_ratio > 1.2:
                score += 2
            elif cash_flow.cash_conversion_ratio > 0.8:
                score += 1
            factors += 1
        
        # Debt scoring
        if debt.debt_to_equity:
            if debt.debt_to_equity < 0.3:
                score += 2
            elif debt.debt_to_equity < 0.6:
                score += 1
            factors += 1
        
        if debt.interest_coverage:
            if debt.interest_coverage > 5:
                score += 2
            elif debt.interest_coverage > 2:
                score += 1
            factors += 1
        
        # Revenue growth scoring
        if revenue.revenue_growth_3yr:
            if revenue.revenue_growth_3yr > 0.15:
                score += 2
            elif revenue.revenue_growth_3yr > 0.05:
                score += 1
            factors += 1
        
        if factors == 0:
            return FinancialHealthGrade.POOR
        
        avg_score = score / factors
        
        if avg_score >= 1.8:
            return FinancialHealthGrade.EXCELLENT
        elif avg_score >= 1.5:
            return FinancialHealthGrade.VERY_GOOD
        elif avg_score >= 1.2:
            return FinancialHealthGrade.GOOD
        elif avg_score >= 0.8:
            return FinancialHealthGrade.FAIR
        elif avg_score >= 0.4:
            return FinancialHealthGrade.POOR
        else:
            return FinancialHealthGrade.VERY_POOR
    
    def _identify_risks_and_strengths(self, cash_flow: CashFlowMetrics, debt: DebtMetrics, revenue: RevenueQuality) -> tuple:
        """Identify key risks and strengths"""
        
        risks = []
        strengths = []
        
        # Cash flow analysis
        if cash_flow.cash_conversion_ratio and cash_flow.cash_conversion_ratio < 0.5:
            risks.append("Poor cash conversion - earnings quality concerns")
        elif cash_flow.cash_conversion_ratio and cash_flow.cash_conversion_ratio > 1.2:
            strengths.append("Strong cash conversion from earnings")
        
        # Debt analysis
        if debt.debt_to_equity and debt.debt_to_equity > 1.0:
            risks.append("High debt-to-equity ratio")
        elif debt.debt_to_equity and debt.debt_to_equity < 0.3:
            strengths.append("Conservative debt levels")
        
        if debt.interest_coverage and debt.interest_coverage < 2:
            risks.append("Low interest coverage - refinancing risk")
        elif debt.interest_coverage and debt.interest_coverage > 5:
            strengths.append("Strong interest coverage")
        
        # Revenue analysis
        if revenue.revenue_growth_3yr and revenue.revenue_growth_3yr < -0.05:
            risks.append("Declining revenue trend")
        elif revenue.revenue_growth_3yr and revenue.revenue_growth_3yr > 0.15:
            strengths.append("Strong revenue growth")
        
        return risks, strengths
    
    def _get_latest_filing_date(self, facts: Dict[str, Any]) -> Optional[str]:
        """Get latest filing date from facts"""
        
        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        
        # Look for any metric with recent data
        for metric_data in us_gaap.values():
            units = metric_data.get('units', {}).get('USD', [])
            if units:
                latest = max(units, key=lambda x: x.get('filed', ''))
                return latest.get('filed')
        
        return None
    
    def _score_cash_flow(self, cash_flow: Optional[CashFlowMetrics]) -> str:
        """Score cash flow metrics"""
        if not cash_flow or not cash_flow.cash_conversion_ratio:
            return 'Unknown'
        
        if cash_flow.cash_conversion_ratio > 1.2:
            return 'Excellent'
        elif cash_flow.cash_conversion_ratio > 0.8:
            return 'Good'
        else:
            return 'Poor'
    
    def _score_debt(self, debt: Optional[DebtMetrics]) -> str:
        """Score debt metrics"""
        if not debt or not debt.debt_to_equity:
            return 'Unknown'
        
        if debt.debt_to_equity < 0.3:
            return 'Excellent'
        elif debt.debt_to_equity < 0.6:
            return 'Good'
        else:
            return 'Poor'
    
    def _score_revenue(self, revenue: Optional[RevenueQuality]) -> str:
        """Score revenue quality"""
        if not revenue or not revenue.revenue_growth_3yr:
            return 'Unknown'
        
        if revenue.revenue_growth_3yr > 0.15:
            return 'Excellent'
        elif revenue.revenue_growth_3yr > 0.05:
            return 'Good'
        else:
            return 'Poor'
    
    def _generate_recommendation(self, grade: Optional[FinancialHealthGrade]) -> str:
        """Generate recommendation based on overall grade"""
        if not grade:
            return 'Hold'
        
        if grade in [FinancialHealthGrade.EXCELLENT, FinancialHealthGrade.VERY_GOOD]:
            return 'Buy'
        elif grade == FinancialHealthGrade.GOOD:
            return 'Hold'
        else:
            return 'Sell'
from typing import Dict, Any
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
from ...config.config import FinanceConfig

class ComparableAnalyzer(IAnalyzer):
    """Comparable company analysis using industry multiples"""
    
    def __init__(self):
        self.config = FinanceConfig()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comparable company analysis"""
        try:
            metrics = data.get('financial_metrics', {})
            company_info = data.get('company_info', {})
            
            # Financial metrics
            total_revenue = metrics.get('total_revenue', 0)
            net_income = metrics.get('net_income', 0)
            shares_outstanding = metrics.get('shares_outstanding', 0)
            current_price = metrics.get('current_price', 0)
            
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            quality_grade = data.get('quality_grade', 'C')
            company_type = data.get('company_type', CompanyType.MATURE_PROFITABLE)
            
            # Get industry-specific multiples from config
            params = self.config.get_adjusted_parameters(
                sector, industry, company_type, quality_grade
            )
            
            # Extract target multiples
            target_multiples = {
                'pe': params.get('pe_multiple', 18),
                'ps': params.get('ps_multiple', 2.5),
                'pb': params.get('pb_multiple', 2.0),
                'ev_ebitda': params.get('ev_ebitda_multiple', 12)
            }
            
            # Calculate fair values using different multiples
            fair_values = {}
            
            # P/E valuation
            if net_income > 0 and shares_outstanding > 0:
                eps = net_income / shares_outstanding
                fair_values['pe_fair_value'] = eps * target_multiples['pe']
            
            # P/S valuation
            if total_revenue > 0 and shares_outstanding > 0:
                revenue_per_share = total_revenue / shares_outstanding
                fair_values['ps_fair_value'] = revenue_per_share * target_multiples['ps']
            
            # Calculate average fair value
            valid_values = [v for v in fair_values.values() if v > 0]
            avg_fair_value = sum(valid_values) / len(valid_values) if valid_values else 0
            
            # Calculate upside/downside
            upside_downside = 0
            if current_price > 0 and avg_fair_value > 0:
                upside_downside = ((avg_fair_value - current_price) / current_price) * 100
            
            # Generate recommendation
            recommendation = self._generate_recommendation(upside_downside)
            
            return {
                'method': 'Comparable Analysis',
                'applicable': True,
                'target_multiples': target_multiples,
                'fair_values': fair_values,
                'average_fair_value': avg_fair_value,
                'current_price': current_price,
                'upside_downside_pct': upside_downside,
                'recommendation': recommendation,
                'confidence': 'Medium',
                'sector': sector,
                'industry': industry,
                'parameters_used': {
                    'pe_multiple': f"{target_multiples['pe']:.1f}x",
                    'ps_multiple': f"{target_multiples['ps']:.1f}x",
                    'quality_adjustment': quality_grade
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_recommendation(self, upside_downside: float) -> str:
        """Generate recommendation based on upside/downside"""
        if upside_downside > 25:
            return "Strong Buy"
        elif upside_downside > 10:
            return "Buy"
        elif upside_downside < -25:
            return "Strong Sell"
        elif upside_downside < -10:
            return "Sell"
        else:
            return "Hold"
    
    def is_applicable(self, company_type: str) -> bool:
        """Comparable analysis applies to most company types except ETFs"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types
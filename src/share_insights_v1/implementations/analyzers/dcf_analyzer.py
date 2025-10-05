from typing import Dict, Any, Optional
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
from ..calculators import dcf_yf
from ...config.config import FinanceConfig

class DCFAnalyzer(IAnalyzer):
    """DCF valuation analyzer implementation using original dcf_yf logic"""
    
    def __init__(self, config : Optional[FinanceConfig] = None):
        self.config = config if config is not None else FinanceConfig()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform DCF analysis using original dcf_yf functions"""
        try:
            company_info = data.get('company_info', {})
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            quality_grade = data.get('quality_grade', 'C')
            company_type = data.get('company_type', CompanyType.MATURE_PROFITABLE)
            metrics = data.get('financial_metrics', {})
            # Get adjusted parameters from config
            params = self.config.get_adjusted_parameters(
                sector=sector, 
                industry=industry,
                company_type=company_type, 
                quality_grade=quality_grade
            )
            
            # Create temporary config with adjusted parameters
            tmp_config = FinanceConfig()
            tmp_config.use_default_ebitda_multiple = True
            tmp_config.default_ev_ebitda_multiple = params.get('ev_ebitda_multiple', tmp_config.default_ev_ebitda_multiple)
            tmp_config.max_cagr_threshold = params.get('max_cagr', tmp_config.max_cagr_threshold)
            tmp_config.default_terminal_growth = params.get('terminal_growth', tmp_config.default_terminal_growth)
            
            # Use original DCF calculation
            share_price, equity_value = dcf_yf.get_share_price(ticker_symbol=ticker, config=tmp_config)
            current_price = metrics.get('current_price', 0)
            
            if current_price > 0:
                upside_downside = ((share_price - current_price) / current_price) * 100
            else:
                upside_downside = 0
            
            # Apply valuation discount if applicable
            valuation_discount = self.config.company_type_adjustments.get(
                company_type, {}
            ).get('valuation_discount', 0.0)
            
            if valuation_discount > 0:
                share_price *= (1 - valuation_discount)
                upside_downside = ((share_price - current_price) / current_price) * 100
            
            # Generate recommendation based on upside/downside
            if upside_downside > 25:
                recommendation = "Strong Buy"
            elif upside_downside > 10:
                recommendation = "Buy"
            elif upside_downside < -25:
                recommendation = "Strong Sell"
            elif upside_downside < -10:
                recommendation = "Sell"
            else:
                recommendation = "Hold"
            
            return {
                'method': 'DCF Analysis',
                'applicable': True,
                'predicted_price': share_price,
                'current_price': current_price,
                'upside_downside_pct': upside_downside,
                'total_equity_value': equity_value,
                'confidence': 'High' if company_type == CompanyType.MATURE_PROFITABLE else 'Medium',
                'valuation': 'Undervalued' if upside_downside > 20 else 'Overvalued' if upside_downside < -20 else 'Fair Value',
                'recommendation': recommendation,
                'parameters_used': {
                    'max_cagr': f"{params['max_cagr']:.1%}",
                    'terminal_growth': f"{params['terminal_growth']:.1%}",
                    'sector': sector,
                    'industry': industry,
                    'quality_adjustment': quality_grade,
                    'valuation_discount': f"{valuation_discount:.1%}" if valuation_discount > 0 else None
                }
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def is_applicable(self, company_type: str) -> bool:
        """Check if DCF applies to company type - excludes financial companies"""
        applicable_types = [
            CompanyType.MATURE_PROFITABLE.value,
            CompanyType.GROWTH_PROFITABLE.value,
            CompanyType.TURNAROUND.value,
            CompanyType.CYCLICAL.value,
            CompanyType.COMMODITY.value,
            CompanyType.REIT.value
        ]
        # Exclude financial companies as they have different business models
        excluded_types = [CompanyType.FINANCIAL.value, CompanyType.ETF.value]
        return company_type in applicable_types and company_type not in excluded_types
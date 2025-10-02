from typing import Dict, Any
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
from ...config.config import FinanceConfig
import yfinance as yf
import numpy as np

class StartupAnalyzer(IAnalyzer):
    """Startup analysis for loss-making companies"""
    
    def __init__(self):
        self.config = FinanceConfig()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform startup analysis"""
        try:
            metrics = data.get('financial_metrics', {})
            company_info = data.get('company_info', {})
            sector = company_info.get('sector', '')
            industry = company_info.get('industry', '')
            stock = yf.Ticker(ticker)
            revenue_data = data.get('revenue_data_statements', {})
            cashflow = stock.cashflow
            income_stmt = stock.income_stmt
            
            burn_rate = 0
            runway_quarters = 0
            
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0 and fcf_data.iloc[0] < 0:
                    burn_rate = abs(fcf_data.iloc[0]) / 4  # Quarterly burn
                    if metrics['total_cash'] > 0:
                        runway_quarters = metrics['total_cash'] / burn_rate
            
            # Enhanced revenue growth analysis
           
            revenue_growth_rates = []
            current_revenue = 0
            revenue_volatility = 0

            if not income_stmt.empty and 'Total Revenue' in income_stmt.index:
                revenue_data = income_stmt.loc['Total Revenue'].dropna()
                current_revenue = revenue_data.iloc[0]
                for i in range(1, min(len(revenue_data), 4)):
                    if revenue_data.iloc[i] > 0:
                        growth = (revenue_data.iloc[i-1] - revenue_data.iloc[i]) / revenue_data.iloc[i]
                        revenue_growth_rates.append(growth)
                
                # Calculate revenue volatility as risk factor
                if len(revenue_growth_rates) > 1:
                    revenue_volatility = np.std(revenue_growth_rates)
            
            runway_years = runway_quarters / 4 if runway_quarters > 0 else 0
            median_growth = np.median(revenue_growth_rates) if revenue_growth_rates else 0
            
            # Enhanced risk assessment
            risk_factors = []
            risk_score = 0  # 0-100 scale
            
            # Cash runway risks
            if runway_years < 0.5:
                risk_factors.append("CRITICAL: Less than 6 months cash runway")
                risk_score += 40
            elif runway_years < 1:
                risk_factors.append("CRITICAL: Less than 1 year cash runway")
                risk_score += 30
            elif runway_years < 2:
                risk_factors.append("HIGH: Less than 2 years cash runway")
                risk_score += 20
            elif runway_years < 3:
                risk_factors.append("MODERATE: Less than 3 years cash runway")
                risk_score += 10
            
            # Growth quality risks
            if median_growth < 0:
                risk_factors.append("CRITICAL: Declining revenue")
                risk_score += 25
            elif median_growth < 0.10:
                risk_factors.append("HIGH: Revenue growth below 10%")
                risk_score += 20
            elif median_growth < 0.20:
                risk_factors.append("MODERATE: Revenue growth below 20% startup threshold")
                risk_score += 10
            
            # Revenue volatility risk
            if revenue_volatility > 0.5:
                risk_factors.append("HIGH: Highly volatile revenue pattern")
                risk_score += 15
            elif revenue_volatility > 0.3:
                risk_factors.append("MODERATE: Volatile revenue pattern")
                risk_score += 10
            
            # Data quality risks
            if len(revenue_growth_rates) < 2:
                risk_factors.append("HIGH: Insufficient revenue history")
                risk_score += 15
            
            # Sector-specific risks
            high_risk_sectors = ['Biotechnology', 'Energy', 'Materials']
            if sector in high_risk_sectors:
                risk_factors.append(f"SECTOR RISK: {sector} has high regulatory/commodity risks")
                risk_score += 10
            
            # Get startup-specific parameters from config
            startup_params = self.config.company_type_adjustments.get(
                CompanyType.STARTUP_LOSS_MAKING, {}
            )
            base_multiple = startup_params.get('revenue_multiple_base', 2.0)
            growth_premium = startup_params.get('growth_multiple_premium', 1.5)
            startup_risk_premium = startup_params.get('risk_premium', 0.05)
            
            # Enhanced revenue multiple calculation using config
            growth_multiple = self.config.get_startup_revenue_multiple(median_growth, sector)
            
            # Apply risk adjustments to multiple
            risk_adjustment = 1.0
            if risk_score > 60:
                risk_adjustment = 0.5  # Severe risk discount
            elif risk_score > 40:
                risk_adjustment = 0.7  # High risk discount
            elif risk_score > 20:
                risk_adjustment = 0.85  # Moderate risk discount
            
            adjusted_multiple = growth_multiple * risk_adjustment
            
            # Stage-based differentiation
            stage = "Unknown"
            stage_multiple = 1.0
            
            if current_revenue < 1e6:  # <$1M revenue
                stage = "Pre-Revenue/Seed"
                stage_multiple = 0.5
            elif current_revenue < 10e6:  # <$10M revenue
                stage = "Early Stage"
                stage_multiple = 0.7
            elif current_revenue < 100e6:  # <$100M revenue
                stage = "Growth Stage"
                stage_multiple = 1.0
            else:
                stage = "Late Stage"
                stage_multiple = 1.2
            
            final_multiple = adjusted_multiple * stage_multiple
            
            # Growth assessment with enhanced criteria
            growth_quality = "Unknown"
            if revenue_growth_rates:
                if median_growth > 1.0:  # >100% growth
                    growth_quality = "Hypergrowth (>100%)"
                elif median_growth > 0.50:
                    growth_quality = "Exceptional (50-100%)"
                elif median_growth > 0.30:
                    growth_quality = "Strong (30-50%)"
                elif median_growth > 0.15:
                    growth_quality = "Moderate (15-30%)"
                elif median_growth > 0:
                    growth_quality = "Weak (<15%)"
                else:
                    growth_quality = "Declining"
            
            # Conservative growth projections with risk adjustment
            growth_decay = 0.8 if median_growth > 0.5 else 0.9  # High growth decays faster
            projected_revenue_1yr = current_revenue * (1 + min(median_growth * 0.8, 0.40))  # More conservative
            projected_revenue_2yr = projected_revenue_1yr * (1 + min(median_growth * growth_decay * 0.6, 0.30))
            
            # Calculate enterprise values
            current_ev = current_revenue * final_multiple
            forward_ev_1yr = projected_revenue_1yr * final_multiple
            forward_ev_2yr = projected_revenue_2yr * final_multiple
            
            # Convert to equity value
            total_debt = metrics['total_debt']
            total_cash = metrics['total_cash']
            net_debt = total_debt - total_cash
            shares_outstanding = data.get('shares_outstanding', 0)
            
            current_price_est = 0
            forward_price_1yr = 0
            forward_price_2yr = 0
            
            if shares_outstanding > 0:
                current_price_est = max(0, (current_ev - net_debt) / shares_outstanding)
                forward_price_1yr = max(0, (forward_ev_1yr - net_debt) / shares_outstanding)
                forward_price_2yr = max(0, (forward_ev_2yr - net_debt) / shares_outstanding)
            
            # Enhanced recommendation logic
            def get_startup_recommendation():
                if risk_score > 70:
                    return "AVOID - Critical risk factors"
                elif runway_years < 0.5:
                    return "AVOID - Imminent bankruptcy risk"
                elif runway_years < 1 and median_growth < 0.15:
                    return "AVOID - Insufficient runway with weak growth"
                elif runway_years > 4 and median_growth > 0.40 and risk_score < 30:
                    return "SPECULATIVE BUY - Strong fundamentals"
                elif runway_years > 2 and median_growth > 0.25 and risk_score < 40:
                    return "HOLD/WATCH - Adequate metrics, monitor closely"
                elif median_growth > 0.75 and runway_years > 1:
                    return "HIGH RISK/HIGH REWARD - Exceptional growth"
                elif risk_score > 50:
                    return "AVOID - High risk without adequate compensation"
                else:
                    return "MONITOR - Mixed signals, wait for clarity"

            return {
                'method': 'Enhanced Startup Analysis',
                'stage': stage,
                'cash_runway_years': runway_years,
                'predicted_price': current_price_est,
                'price_1y': forward_price_1yr,
                'price_2y': forward_price_2yr,
                'quarterly_burn_rate': burn_rate,
                'revenue_growth_rates': [f"{rate:.1%}" for rate in revenue_growth_rates],
                'median_growth': f"{median_growth:.1%}",
                'revenue_volatility': f"{revenue_volatility:.1%}",
                'growth_quality': growth_quality,
                'risk_factors': risk_factors,
                'risk_score': risk_score,
                'recommendation': get_startup_recommendation(),
                'revenue_multiple_breakdown': {
                    'base_multiple': growth_multiple,
                    'risk_adjustment': risk_adjustment,
                    'stage_adjustment': stage_multiple,
                    'final_multiple': final_multiple
                },
                'current_revenue': current_revenue,
                'projected_revenue_1yr': projected_revenue_1yr,
                'projected_revenue_2yr': projected_revenue_2yr,
                'implied_value_estimate': current_revenue * final_multiple if current_revenue > 0 else 0,
                'confidence_level': 'Very Low - Speculative' if risk_score > 40 else 'Low - High Risk',
                'investment_type': 'Venture Capital Style - Total Loss Possible'
            }
            
        except Exception as e:
            # self.error_analysis.append(f"startup_analysis():{str(e)}")
            return {'error': f"Startup analysis failed: {e}"}
            
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_risk_score(self, revenue_growth: float, runway_years: float, revenue: float) -> float:
        """Calculate risk score for startup"""
        risk_score = 0
        
        # Revenue risk (40 points)
        if revenue < 10_000_000:  # Less than $10M
            risk_score += 20
        elif revenue < 50_000_000:  # Less than $50M
            risk_score += 10
        
        # Growth risk (30 points)
        if revenue_growth < 0.1:  # Less than 10%
            risk_score += 30
        elif revenue_growth < 0.2:  # Less than 20%
            risk_score += 15
        
        # Runway risk (30 points)
        if runway_years < 1:
            risk_score += 30
        elif runway_years < 2:
            risk_score += 20
        elif runway_years < 3:
            risk_score += 10
        
        return min(risk_score, 100)
    
    def _generate_startup_recommendation(self, risk_score: float, runway_years: float, 
                                       revenue_growth: float, estimated_value: float, 
                                       market_cap: float) -> str:
        """Generate startup recommendation"""
        if runway_years < 1:
            return "AVOID - Critical runway risk"
        elif risk_score > 70:
            return "AVOID - Too many risk factors"
        elif revenue_growth > 0.5 and runway_years > 2:
            return "SPECULATIVE BUY - HIGH REWARD/HIGH RISK"
        elif revenue_growth > 0.2 and runway_years > 1.5:
            return "SPECULATIVE BUY - Monitor closely"
        else:
            return "HOLD/AVOID - High uncertainty"
    
    def is_applicable(self, company_type: str) -> bool:
        """Startup analysis only applies to loss-making companies"""
        return company_type == CompanyType.STARTUP_LOSS_MAKING.value
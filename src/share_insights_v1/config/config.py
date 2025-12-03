from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum

class CompanyType(Enum):
    MATURE_PROFITABLE = "mature_profitable"
    GROWTH_PROFITABLE = "growth_profitable"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"
    STARTUP_LOSS_MAKING = "startup_loss_making"
    REIT = "reit"
    FINANCIAL = "financial"
    COMMODITY = "commodity"

@dataclass
class IndustryConfig:
    """Configuration for specific industry parameters"""
    max_cagr: float
    terminal_growth: float
    ev_ebitda_multiple: float
    pe_multiple: float
    ps_multiple: float
    pb_multiple: float
    cyclical_discount: float = 0.0
    risk_premium: float = 0.0

@dataclass
class FinanceConfig:
    # Base CAGR Configuration
    max_cagr_threshold: float = 0.15
    min_cagr_threshold: float = -0.10
    default_cagr: float = 0.05
    
    # Base DCF Configuration
    default_terminal_growth: float = 0.025
    default_discount_rate: float = 0.10
    default_tax_rate: float = 0.21
    
    # Data Quality Thresholds
    min_data_points: int = 3
    max_ev_ebitda_multiple: float = 25.0
    default_ev_ebitda_multiple: float = 12.0
    use_default_ebitda_multiple: bool = False
    
    # Return configs
    market_return: float = 0.08
    cost_of_debt: float = 0.055  # Updated for 2024-2025 environment
    tax_rate: float = 0.21    
    years: int = 5
    
    # Risk-free rate and market conditions
    risk_free_rate: float = 0.045  # Current 10-year treasury
    equity_risk_premium: float = 0.055  # Market return - risk free rate
    
    # Industry-specific configurations
    industry_configs: Dict[str, IndustryConfig] = field(default_factory=lambda: {
        # Technology Sectors
        'Technology': IndustryConfig(
            max_cagr=0.20, terminal_growth=0.030, ev_ebitda_multiple=18.0,
            pe_multiple=25.0, ps_multiple=6.0, pb_multiple=3.5
        ),
        'Software - Application': IndustryConfig(
            max_cagr=0.25, terminal_growth=0.035, ev_ebitda_multiple=22.0,
            pe_multiple=35.0, ps_multiple=8.0, pb_multiple=4.0
        ),
        'Software - Infrastructure': IndustryConfig(
            max_cagr=0.15, terminal_growth=0.025, ev_ebitda_multiple=16.0,
            pe_multiple=22.0, ps_multiple=5.0, pb_multiple=3.0
        ),
        'Semiconductors': IndustryConfig(
            max_cagr=0.18, terminal_growth=0.030, ev_ebitda_multiple=20.0,
            pe_multiple=28.0, ps_multiple=4.0, pb_multiple=3.5, cyclical_discount=0.10
        ),
        
        # Healthcare
        'Healthcare': IndustryConfig(
            max_cagr=0.12, terminal_growth=0.030, ev_ebitda_multiple=15.0,
            pe_multiple=22.0, ps_multiple=4.0, pb_multiple=2.8
        ),
        'Biotechnology': IndustryConfig(
            max_cagr=0.30, terminal_growth=0.035, ev_ebitda_multiple=25.0,
            pe_multiple=45.0, ps_multiple=12.0, pb_multiple=4.0, risk_premium=0.02
        ),
        'Drug Manufacturers - Major': IndustryConfig(
            max_cagr=0.08, terminal_growth=0.025, ev_ebitda_multiple=12.0,
            pe_multiple=16.0, ps_multiple=3.0, pb_multiple=2.5
        ),
        
        # Financial Services
        'Financial Services': IndustryConfig(
            max_cagr=0.08, terminal_growth=0.020, ev_ebitda_multiple=10.0,
            pe_multiple=12.0, ps_multiple=2.5, pb_multiple=1.2
        ),
        'Banks - Regional': IndustryConfig(
            max_cagr=0.06, terminal_growth=0.020, ev_ebitda_multiple=8.0,
            pe_multiple=10.0, ps_multiple=2.0, pb_multiple=1.0
        ),
        'Fintech': IndustryConfig(  # Added for TIGR-like companies
            max_cagr=0.25, terminal_growth=0.030, ev_ebitda_multiple=20.0,
            pe_multiple=28.0, ps_multiple=8.0, pb_multiple=4.0
        ),
        
        # Energy & Materials
        'Energy': IndustryConfig(
            max_cagr=0.08, terminal_growth=0.015, ev_ebitda_multiple=8.0,
            pe_multiple=15.0, ps_multiple=1.0, pb_multiple=1.5, cyclical_discount=0.15
        ),
        'Oil & Gas E&P': IndustryConfig(
            max_cagr=0.10, terminal_growth=0.010, ev_ebitda_multiple=6.0,
            pe_multiple=12.0, ps_multiple=0.8, pb_multiple=1.2, cyclical_discount=0.20
        ),
        'Materials': IndustryConfig(
            max_cagr=0.08, terminal_growth=0.020, ev_ebitda_multiple=10.0,
            pe_multiple=16.0, ps_multiple=1.5, pb_multiple=1.8, cyclical_discount=0.12
        ),
        
        # Consumer
        'Consumer Cyclical': IndustryConfig(
            max_cagr=0.10, terminal_growth=0.025, ev_ebitda_multiple=12.0,
            pe_multiple=18.0, ps_multiple=1.5, pb_multiple=2.0, cyclical_discount=0.08
        ),
        'Consumer Staples': IndustryConfig(
            max_cagr=0.06, terminal_growth=0.025, ev_ebitda_multiple=14.0,
            pe_multiple=20.0, ps_multiple=2.0, pb_multiple=2.5
        ),
        'Restaurants': IndustryConfig(
            max_cagr=0.12, terminal_growth=0.025, ev_ebitda_multiple=16.0,
            pe_multiple=24.0, ps_multiple=2.5, pb_multiple=3.0
        ),
        
        # Utilities & REITs
        'Utilities': IndustryConfig(
            max_cagr=0.04, terminal_growth=0.020, ev_ebitda_multiple=10.0,
            pe_multiple=16.0, ps_multiple=2.0, pb_multiple=1.4
        ),
        'Real Estate': IndustryConfig(
            max_cagr=0.06, terminal_growth=0.022, ev_ebitda_multiple=15.0,
            pe_multiple=20.0, ps_multiple=3.0, pb_multiple=1.8
        ),
        
        # Communication Services
        'Communication Services': IndustryConfig(
            max_cagr=0.08, terminal_growth=0.025, ev_ebitda_multiple=12.0,
            pe_multiple=18.0, ps_multiple=2.5, pb_multiple=2.0
        ),
        'Entertainment': IndustryConfig(
            max_cagr=0.12, terminal_growth=0.025, ev_ebitda_multiple=15.0,
            pe_multiple=22.0, ps_multiple=3.0, pb_multiple=2.5
        ),
        
        # Industrials
        'Industrials': IndustryConfig(
            max_cagr=0.08, terminal_growth=0.025, ev_ebitda_multiple=12.0,
            pe_multiple=18.0, ps_multiple=1.8, pb_multiple=2.2
        ),
        'Aerospace & Defense': IndustryConfig(
            max_cagr=0.06, terminal_growth=0.020, ev_ebitda_multiple=11.0,
            pe_multiple=16.0, ps_multiple=1.5, pb_multiple=2.0
        ),
    })
    
    # Company type adjustments
    company_type_adjustments: Dict[CompanyType, Dict[str, float]] = field(default_factory=lambda: {
        CompanyType.MATURE_PROFITABLE: {
            'cagr_multiplier': 1.0,
            'terminal_growth_adjustment': 0.0,
            'risk_premium': 0.0
        },
        CompanyType.GROWTH_PROFITABLE: {
            'cagr_multiplier': 1.2,
            'terminal_growth_adjustment': 0.005,
            'risk_premium': 0.01
        },
        CompanyType.CYCLICAL: {
            'cagr_multiplier': 0.8,
            'terminal_growth_adjustment': -0.005,
            'risk_premium': 0.015,
            'apply_cyclical_discount': True
        },
        CompanyType.TURNAROUND: {
            'cagr_multiplier': 1.5,
            'terminal_growth_adjustment': 0.0,
            'risk_premium': 0.025,
            'valuation_discount': 0.20,
            'multiple_discount': 0.3  # 70% discount on all multiples
        },
        CompanyType.STARTUP_LOSS_MAKING: {
            'revenue_multiple_base': 2.0,  # More conservative base
            'growth_multiple_premium': 1.5,  # Reduced premium
            'risk_premium': 0.05,
            'min_growth_threshold': 0.15,  # 15% minimum for startups
            'runway_critical_months': 6,  # Critical runway threshold
            'runway_warning_months': 18,  # Warning threshold
            'volatility_penalty': 0.2,  # Penalty for high revenue volatility
            'stage_multipliers': {
                'pre_revenue': 0.3,
                'seed': 0.5, 
                'early': 0.7,
                'growth': 1.0,
                'late': 1.2
            }
        }
    })
    
    def get_industry_config(self, sector: str, industry: str) -> IndustryConfig:
        """Get industry-specific configuration with fallback logic"""
        # First try specific industry
        if industry in self.industry_configs:
            return self.industry_configs[industry]
        
        # Then try sector
        if sector in self.industry_configs:
            return self.industry_configs[sector]
        
        # Default fallback
        return IndustryConfig(
            max_cagr=self.max_cagr_threshold,
            terminal_growth=self.default_terminal_growth,
            ev_ebitda_multiple=self.default_ev_ebitda_multiple,
            pe_multiple=18.0,
            ps_multiple=2.5,
            pb_multiple=2.0
        )
    
    def get_startup_risk_adjustments(self, runway_years: float, revenue_volatility: float, 
                                   data_quality: str) -> Dict[str, float]:
        """Calculate risk adjustments specific to startup analysis"""
        startup_config = self.company_type_adjustments[CompanyType.STARTUP_LOSS_MAKING]
        
        # Runway risk adjustment
        runway_months = runway_years * 12
        if runway_months < startup_config['runway_critical_months']:
            runway_adjustment = 0.3  # Severe discount
        elif runway_months < startup_config['runway_warning_months']:
            runway_adjustment = 0.6  # High discount
        elif runway_months < 36:  # Less than 3 years
            runway_adjustment = 0.8  # Moderate discount
        else:
            runway_adjustment = 1.0  # No discount
        
        # Volatility adjustment
        if revenue_volatility > 0.5:
            volatility_adjustment = 0.7
        elif revenue_volatility > 0.3:
            volatility_adjustment = 0.85
        else:
            volatility_adjustment = 1.0
        
        # Data quality adjustment
        data_adjustments = {'High': 1.0, 'Medium': 0.9, 'Low': 0.7}
        data_adjustment = data_adjustments.get(data_quality, 0.8)
        
        return {
            'runway_adjustment': runway_adjustment,
            'volatility_adjustment': volatility_adjustment,
            'data_adjustment': data_adjustment,
            'combined_adjustment': runway_adjustment * volatility_adjustment * data_adjustment
        }
    
    def get_adjusted_parameters(self, sector: str, industry: str, 
                              company_type: CompanyType, quality_grade: str) -> Dict[str, float]:
        """Get fully adjusted parameters for a specific company"""
        industry_config = self.get_industry_config(sector, industry)
        type_adjustments = self.company_type_adjustments.get(company_type, {})
        
        # Base parameters from industry
        params = {
            'max_cagr': industry_config.max_cagr,
            'terminal_growth': industry_config.terminal_growth,
            'ev_ebitda_multiple': industry_config.ev_ebitda_multiple,
            'pe_multiple': industry_config.pe_multiple,
            'ps_multiple': industry_config.ps_multiple,
            'pb_multiple': industry_config.pb_multiple,
            'risk_premium': industry_config.risk_premium
        }
        
        # Apply company type adjustments
        if 'cagr_multiplier' in type_adjustments:
            params['max_cagr'] *= type_adjustments['cagr_multiplier']
        
        if 'terminal_growth_adjustment' in type_adjustments:
            params['terminal_growth'] += type_adjustments['terminal_growth_adjustment']
        
        if 'risk_premium' in type_adjustments:
            params['risk_premium'] += type_adjustments['risk_premium']
        
        # Apply cyclical discount if applicable
        if type_adjustments.get('apply_cyclical_discount') and industry_config.cyclical_discount > 0:
            params['cyclical_discount'] = industry_config.cyclical_discount
        
        # Quality adjustments
        quality_multipliers = {'A': 1.1, 'B': 1.0, 'C': 0.9, 'D': 0.8}
        quality_mult = quality_multipliers.get(quality_grade, 1.0)
        
        if quality_mult != 1.0:
            params['max_cagr'] *= quality_mult
            params['ev_ebitda_multiple'] *= quality_mult
            params['pe_multiple'] *= quality_mult
            params['ps_multiple'] *= quality_mult
            params['pb_multiple'] *= quality_mult
        
        # Apply turnaround multiple discount
        if 'multiple_discount' in type_adjustments:
            discount = type_adjustments['multiple_discount']
            params['ev_ebitda_multiple'] *= discount
            params['pe_multiple'] *= discount
            params['ps_multiple'] *= discount
            params['pb_multiple'] *= discount
        
        # Apply caps and floors
        params['max_cagr'] = min(params['max_cagr'], 0.30)  # Never exceed 30%
        params['max_cagr'] = max(params['max_cagr'], 0.02)  # Minimum 2%
        params['terminal_growth'] = min(params['terminal_growth'], 0.040)  # Max 4%
        params['terminal_growth'] = max(params['terminal_growth'], 0.010)  # Min 1%
        
        return params
    
    def get_startup_revenue_multiple(self, revenue_growth: float, sector: str) -> float:
        """Calculate appropriate revenue multiple for startups with enhanced risk controls"""
        startup_config = self.company_type_adjustments[CompanyType.STARTUP_LOSS_MAKING]
        base_multiple = startup_config['revenue_multiple_base']
        
        # More conservative growth-based premium
        if revenue_growth > 1.0:  # >100% growth
            growth_premium = 4.0  # Reduced from 6.0
        elif revenue_growth > 0.5:  # >50% growth
            growth_premium = 3.0  # Reduced from 4.0
        elif revenue_growth > 0.3:  # >30% growth
            growth_premium = 2.5  # Reduced from 3.0
        elif revenue_growth > 0.2:  # >20% growth
            growth_premium = 2.0
        elif revenue_growth > 0.1:  # >10% growth
            growth_premium = 1.5
        else:
            growth_premium = 1.0
        
        # More conservative sector multipliers
        sector_multipliers = {
            'Technology': 1.2,  # Reduced from 1.3
            'Healthcare': 1.1,  # Reduced from 1.2
            'Biotechnology': 1.3,  # Reduced from 1.5
            'Consumer Cyclical': 0.8,
            'Energy': 0.6,
            'Financial Services': 0.9,  # Reduced from 1.0
            'Communication Services': 1.0,
            'Industrials': 0.7,
            'Materials': 0.6
        }
        
        sector_mult = sector_multipliers.get(sector, 0.9)  # Default reduced to 0.9
        
        # Apply growth decay for very high growth (unsustainable)
        if revenue_growth > 0.75:
            sustainability_discount = 0.8
        elif revenue_growth > 0.5:
            sustainability_discount = 0.9
        else:
            sustainability_discount = 1.0
        
        final_multiple = base_multiple * growth_premium * sector_mult * sustainability_discount
        
        return min(final_multiple, 10.0)  # Reduced cap from 15x to 10x

# Example usage and validation
def validate_config():
    """Validate the configuration makes sense"""
    config = FinanceConfig()
    
    # Test different company scenarios
    test_cases = [
        ("Technology", "Software - Application", CompanyType.GROWTH_PROFITABLE, "A"),
        ("Energy", "Oil & Gas E&P", CompanyType.CYCLICAL, "C"),
        ("Healthcare", "Biotechnology", CompanyType.STARTUP_LOSS_MAKING, "B"),
        ("Financial Services", "Banks - Regional", CompanyType.MATURE_PROFITABLE, "B"),
    ]
    
    print("Configuration Validation:")
    print("-" * 60)
    
    for sector, industry, company_type, quality in test_cases:
        params = config.get_adjusted_parameters(sector, industry, company_type, quality)
        print(f"\n{industry} ({company_type.value}, Grade {quality}):")
        print(f"  Max CAGR: {params['max_cagr']:.1%}")
        print(f"  Terminal Growth: {params['terminal_growth']:.1%}")
        print(f"  EV/EBITDA: {params['ev_ebitda_multiple']:.1f}x")
        print(f"  P/E Multiple: {params['pe_multiple']:.1f}x")
        if 'cyclical_discount' in params:
            print(f"  Cyclical Discount: {params['cyclical_discount']:.1%}")

if __name__ == "__main__":
    validate_config()
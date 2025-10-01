from dataclasses import dataclass

@dataclass
class FinanceConfig:
    # CAGR Configuration
    max_cagr_threshold: float = 0.15  # 15% max CAGR
    min_cagr_threshold: float = -0.10  # -10% min CAGR
    default_cagr: float = 0.05  # 5% default CAGR

    # DCF Configuration
    default_terminal_growth: float = 0.025  # 2.5%
    default_discount_rate: float = 0.10  # 10%
    default_tax_rate: float = 0.21  # 21%

    # Data Quality Thresholds
    min_data_points: int = 2
    max_ev_ebitda_multiple: float = 20.0
    default_ev_ebitda_multiple: float = 12.0
    use_default_ebitda_multiple:bool = True
    # Return configs
    market_return = 0.1
    cost_of_debt = 0.04
    tax_rate = .21    
    years = 5
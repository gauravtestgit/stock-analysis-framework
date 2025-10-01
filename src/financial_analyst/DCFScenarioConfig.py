import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class DCFScenarioConfig:
    scenario_name: str
    max_fcf_cagr: float = 0.15
    max_ebitda_cagr: float = 0.15
    default_fcf_cagr: float = 0.05
    default_ebitda_cagr: float = 0.05
    terminal_growth: float = 0.025
    market_return: float = 0.08
    cost_of_debt: float = 0.04
    tax_rate: float = 0.21
    projection_years: int = 5

    def to_dict(self):
        """Convert to dictionary for easy display"""
        return {
            'Scenario': self.scenario_name,
            'Max FCF CAGR': f"{self.max_fcf_cagr:.1%}",
            'Max EBITDA CAGR': f"{self.max_ebitda_cagr:.1%}",
            'Default FCF CAGR': f"{self.default_fcf_cagr:.1%}",
            'Default EBITDA CAGR': f"{self.default_ebitda_cagr:.1%}",
            'Terminal Growth': f"{self.terminal_growth:.1%}",
            'Market Return': f"{self.market_return:.1%}",
            'Cost of Debt': f"{self.cost_of_debt:.1%}",
            'Tax Rate': f"{self.tax_rate:.1%}"
        }
    """Main class for running DCF scenario analysis"""
    
    def __init__(self):
        self.scenarios = {}
        self.results = {}
        
    def add_scenario(self, config: DCFScenarioConfig):
        """Add a scenario configuration"""
        self.scenarios[config.scenario_name] = config
        
    def create_preset_scenarios(self):
        """Create common preset scenarios"""
        
        # Conservative scenario
        conservative = DCFScenarioConfig(
            scenario_name="Conservative",
            max_fcf_cagr=0.08,
            max_ebitda_cagr=0.08,
            default_fcf_cagr=0.03,
            default_ebitda_cagr=0.03,
            terminal_growth=0.02,
            market_return=0.07
        )
        
        # Base case scenario
        base_case = DCFScenarioConfig(
            scenario_name="Base Case",
            max_fcf_cagr=0.12,
            max_ebitda_cagr=0.12,
            default_fcf_cagr=0.05,
            default_ebitda_cagr=0.05,
            terminal_growth=0.025,
            market_return=0.08
        )
        
        # Optimistic scenario
        optimistic = DCFScenarioConfig(
            scenario_name="Optimistic",
            max_fcf_cagr=0.20,
            max_ebitda_cagr=0.18,
            default_fcf_cagr=0.07,
            default_ebitda_cagr=0.07,
            terminal_growth=0.03,
            market_return=0.10
        )
        
        # Recovery scenario (for post-COVID companies)
        recovery = DCFScenarioConfig(
            scenario_name="Recovery",
            max_fcf_cagr=0.25,  # Allow higher growth for recovery
            max_ebitda_cagr=0.25,
            default_fcf_cagr=0.10,
            default_ebitda_cagr=0.10,
            terminal_growth=0.025,
            market_return=0.09
        )
        
        # Recession scenario
        recession = DCFScenarioConfig(
            scenario_name="Recession",
            max_fcf_cagr=0.05,
            max_ebitda_cagr=0.05,
            default_fcf_cagr=0.01,
            default_ebitda_cagr=0.01,
            terminal_growth=0.015,
            market_return=0.06
        )
        
        scenarios = [conservative, base_case, optimistic, recovery, recession]
        for scenario in scenarios:
            self.add_scenario(scenario)
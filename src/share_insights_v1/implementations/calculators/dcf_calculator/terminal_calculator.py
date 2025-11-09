import numpy as np
from typing import Dict, Optional
from ....utils.debug_printer import debug_print
from ....config.config import FinanceConfig

class TerminalCalculator:
    """Handles terminal value calculations with dominance checks"""
    
    def __init__(self, config: FinanceConfig = None):
        self.config = config or FinanceConfig()
        self.max_terminal_ratio = 1.0  # No terminal ratio cap (original behavior)
    
    def calculate_terminal_value(self, fcf_future: float, ebitda_future: float, 
                               wacc: float, ticker, sector: str = "") -> Dict:
        """Calculate terminal value using hybrid approach with caps"""
        
        # Calculate both methods
        perpetuity_value = self._perpetuity_growth_method(fcf_future, wacc)
        multiple_value = self._ebitda_multiple_method(ticker, ebitda_future)
        
        # Get average with sector adjustments
        average_value = self._get_weighted_average(perpetuity_value, multiple_value, sector)
        
        return {
            'terminal_value_pg': perpetuity_value,
            'terminal_value_ebitda_multiple': multiple_value,
            'average_terminal_value': average_value
        }
    
    def apply_terminal_caps(self, terminal_value: float, pv_fcf: float) -> Dict:
        """Apply terminal value dominance caps"""
        total_value = terminal_value + pv_fcf
        terminal_ratio = terminal_value / total_value if total_value > 0 else 0
        
        debug_print(f"Terminal value ratio: {terminal_ratio:.1%}")
        
        if terminal_ratio > self.max_terminal_ratio:
            debug_print(f"Terminal value dominance detected ({terminal_ratio:.1%}), applying caps")
            
            # Reduce terminal value to acceptable ratio
            max_terminal = pv_fcf * (self.max_terminal_ratio / (1 - self.max_terminal_ratio))
            adjustment_factor = max_terminal / terminal_value
            
            return {
                'adjusted_terminal_value': max_terminal,
                'adjustment_factor': adjustment_factor,
                'confidence_impact': 'Low',  # Lower confidence due to high terminal dependence
                'original_ratio': terminal_ratio
            }
        
        return {
            'adjusted_terminal_value': terminal_value,
            'adjustment_factor': 1.0,
            'confidence_impact': 'None',
            'original_ratio': terminal_ratio
        }
    
    def _perpetuity_growth_method(self, fcf_future: float, wacc: float) -> float:
        """Calculate terminal value using perpetuity growth"""
        growth_rate = self.config.default_terminal_growth
        
        # Perpetuity growth model invalid for negative FCF
        if fcf_future <= 0:
            debug_print(f"Warning: Negative FCF ${fcf_future:,.0f} - perpetuity growth model not applicable")
            return 0
        
        if growth_rate >= wacc:
            debug_print(f'Error. Growth rate: {growth_rate} must be less than WACC: {wacc}. Using defaults')
            growth_rate = min(self.config.default_terminal_growth, wacc - 0.005)
            debug_print(f"Using adjusted growth rate: {growth_rate:.2%}")

        terminal_value_pg = fcf_future * (1 + growth_rate) / (wacc - growth_rate)
        debug_print(f"Terminal Value Perpetuity Growth: ${terminal_value_pg:,.0f}")
        return terminal_value_pg
    
    def _ebitda_multiple_method(self, ticker, ebitda_future: float) -> float:
        """Calculate terminal value using EBITDA multiple"""
        ev_ebitda_multiple = ticker.info.get('enterpriseToEbitda', self.config.default_ev_ebitda_multiple)
        
        if ev_ebitda_multiple is None or ev_ebitda_multiple <= 0 or ev_ebitda_multiple > 25:
            debug_print(f"Warning: Invalid EV/EBITDA multiple {ev_ebitda_multiple}x, using default of {self.config.default_ev_ebitda_multiple}x")
            ev_ebitda_multiple = self.config.default_ev_ebitda_multiple
        else:
            debug_print(f'using retrieved EV/EBITDA multiple: {ev_ebitda_multiple}x')
        
        terminal_enterprise_value = ebitda_future * ev_ebitda_multiple
        debug_print(f"EV/EBITDA Multiple: {ev_ebitda_multiple:.1f}x")
        debug_print(f"Terminal Value EBITDA Multiple: ${terminal_enterprise_value:,.0f}")
        
        return terminal_enterprise_value
    
    def _get_weighted_average(self, perpetuity_value: float, multiple_value: float, sector: str) -> float:
        """Get simple average (original DCF logic)"""
        # Handle None values
        if perpetuity_value is None or perpetuity_value <= 0:
            debug_print("Warning: Using only EBITDA multiple method (perpetuity growth unavailable)")
            return multiple_value
        if multiple_value is None or multiple_value <= 0:
            debug_print("Warning: Using only perpetuity growth method (EBITDA multiple unavailable)")
            return perpetuity_value
        
        # Simple equal weighting (original behavior)
        average_value = (perpetuity_value + multiple_value) / 2
        debug_print(f'Average Terminal Value: ${average_value:,.0f}')
        return average_value
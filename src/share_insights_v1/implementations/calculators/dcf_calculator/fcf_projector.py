from typing import List
from ....utils.debug_printer import debug_print

class FCFProjector:
    """Handles free cash flow projections and present value calculations"""
    
    def __init__(self):
        pass
    
    def project_cash_flows(self, ticker, fcf_cagr: float, years: int = 5) -> List[float]:
        """Project future free cash flows"""
        cashflow = ticker.cashflow
        fcf_ending = cashflow.loc['Free Cash Flow'].iloc[0]
        
        projected_fcf = []
        for i in range(1, years + 1):
            if fcf_ending < 0:
                # For negative FCF, positive CAGR should reduce losses
                projected_fcf.append(fcf_ending * (1 - fcf_cagr)**i)
            else:
                projected_fcf.append(fcf_ending * (1 + fcf_cagr)**i)
        
        # Debug output
        for i, fcf in enumerate(projected_fcf):
            debug_print(f'Year {i+1}, projected FCF: ${fcf:,.0f}')
        
        return projected_fcf
    
    def calculate_present_values(self, projected_fcf: List[float], wacc: float) -> List[float]:
        """Calculate present value of projected cash flows"""
        pv_fcf = []
        
        for i, fcf in enumerate(projected_fcf):
            discount_factor = 1 / ((1 + wacc)**(i + 1))
            pv = fcf * discount_factor
            pv_fcf.append(pv)
            debug_print(f"Year {i + 1}: PV FCF: ${pv:,.0f}")
        
        return pv_fcf
    
    def calculate_pv_terminal_value(self, terminal_value: float, wacc: float, years: int) -> float:
        """Calculate present value of terminal value"""
        discount_factor = 1 / ((1 + wacc)**years)
        pv_terminal = terminal_value * discount_factor
        debug_print(f'PV Terminal Value: ${pv_terminal:,.0f}')
        return pv_terminal
    
    def project_future_metric(self, ticker, metric_name: str, cagr: float, years: int) -> float:
        """Project future value of any metric (FCF, EBITDA, etc.)"""
        if metric_name.upper() == 'FCF':
            current_value = ticker.cashflow.loc['Free Cash Flow'].iloc[0]
        elif metric_name.upper() == 'EBITDA':
            current_value = ticker.income_stmt.loc['EBITDA'].iloc[0]
        else:
            raise ValueError(f"Unsupported metric: {metric_name}")
        
        if current_value < 0:
            # For negative values, positive CAGR should reduce losses
            future_value = current_value * (1 - cagr)**years
        else:
            future_value = current_value * (1 + cagr)**years
        
        debug_print(f'{metric_name} Future: {future_value:,.2f}')
        return future_value
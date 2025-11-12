from typing import Dict
from .growth_calculator import GrowthCalculator
from .terminal_calculator import TerminalCalculator
from .wacc_calculator import WACCCalculator
from .fcf_projector import FCFProjector
from ....utils.debug_printer import debug_print
from ....config.config import FinanceConfig

class DCFEngine:
    """Main DCF calculation engine orchestrating all components"""
    
    def __init__(self, config: FinanceConfig = None):
        self.config = config or FinanceConfig()
        self.growth_calc = GrowthCalculator(config)
        self.terminal_calc = TerminalCalculator(config)
        self.wacc_calc = WACCCalculator(config)
        self.fcf_projector = FCFProjector()
    
    def calculate_dcf(self, ticker_symbol: str) -> Dict:
        """Main DCF calculation using config parameters (already adjusted by analyzer)"""
        import yfinance as yf
        from ....models.company import CompanyType
        
        ticker = yf.Ticker(ticker_symbol)
        
        # Get company type from config (passed by analyzer)
        company_type = getattr(self.config, 'company_type', None)
        
        # Use the config as-is (already adjusted by DCF analyzer)
        # Update components with config
        self.growth_calc.config = self.config
        self.terminal_calc.config = self.config
        
        try:
            # 1. Calculate WACC
            wacc_data = self.wacc_calc.calculate_wacc(ticker)
            wacc = wacc_data['wacc']
            
            # 2. Calculate growth rates
            fcf_cagr = self.growth_calc.calculate_fcf_cagr(ticker)
            ebitda_cagr = self.growth_calc.calculate_ebitda_cagr(ticker)
            
            debug_print(f'FCF CAGR: {fcf_cagr}')
            debug_print(f'EBITDA CAGR: {ebitda_cagr}')
            
            # 3. Project future cash flows
            projected_fcf = self.fcf_projector.project_cash_flows(ticker, fcf_cagr, self.config.years)
            fcf_future = self.fcf_projector.project_future_metric(ticker, 'FCF', fcf_cagr, self.config.years)
            ebitda_future = self.fcf_projector.project_future_metric(ticker, 'EBITDA', ebitda_cagr, self.config.years)
            
            # 4. Calculate present values
            pv_fcf_list = self.fcf_projector.calculate_present_values(projected_fcf, wacc)
            pv_fcf = sum(pv_fcf_list)
            debug_print(f'PV FCF: ${pv_fcf:,.0f}')
            
            # 5. Calculate terminal value
            terminal_data = self.terminal_calc.calculate_terminal_value(
                fcf_future, ebitda_future, wacc, ticker
            )
            
            # 6. Apply terminal value caps
            terminal_caps = self.terminal_calc.apply_terminal_caps(
                terminal_data['average_terminal_value'], pv_fcf
            )
            
            final_terminal_value = terminal_caps['adjusted_terminal_value']
            pv_terminal_value = self.fcf_projector.calculate_pv_terminal_value(
                final_terminal_value, wacc, self.config.years
            )
            
            # 7. Calculate enterprise and equity values
            enterprise_value = pv_fcf + pv_terminal_value
            equity_data = self._calculate_equity_value(ticker, enterprise_value)
            
            # 8. Apply risk adjustments for extreme cases
            risk_adjusted_equity = self._apply_risk_adjustments(
                equity_data, terminal_caps, company_type, pv_fcf
            )
            
            # 9. Determine confidence based on adjustments
            confidence = self._calculate_confidence(terminal_caps)
            
            # 10. Compile results
            return self._compile_results(
                ticker_symbol, ticker, wacc_data, fcf_cagr, ebitda_cagr,
                fcf_future, ebitda_future, terminal_data, terminal_caps,
                projected_fcf, pv_fcf_list, pv_fcf, pv_terminal_value,
                enterprise_value, risk_adjusted_equity, confidence
            )
            
        except Exception as e:
            debug_print(f"DCF calculation error: {e}")
            raise Exception(f"DCF calculation failed: {str(e)}")
    
    def _calculate_equity_value(self, ticker, enterprise_value: float) -> Dict:
        """Calculate equity value using original DCF logic"""
        total_debt = ticker.info.get('totalDebt', 0) or 0
        total_cash = ticker.info.get('totalCash', 0) or 0
        
        debug_print(f'Total Debt: ${total_debt:,.0f}, Total Cash: ${total_cash:,.0f}')
        debug_print(f'Enterprise Value: ${enterprise_value:,.0f}, Net Debt: ${total_debt-total_cash:,.2f}')
        
        # Original logic: simple net debt calculation
        adjusted_debt = total_debt - total_cash
        equity_value = enterprise_value - adjusted_debt
        
        debug_print(f'Equity Value: ${equity_value:,.0f}')
        
        shares_outstanding = ticker.info.get('sharesOutstanding', 0)
        share_price = equity_value / shares_outstanding if shares_outstanding > 0 else 0
        
        debug_print(f'Share Price: ${share_price:.2f}')
        debug_print(f'Ticker, DCF Share Price, Last Close Price\\n{ticker.info.get("symbol")}, ${share_price:.2f}, ${ticker.info.get("previousClose", 0):.2f}')
        
        return {
            'total_debt': total_debt,
            'total_cash': total_cash,
            'adjusted_debt': adjusted_debt,
            'equity_value': equity_value,
            'shares_outstanding': shares_outstanding,
            'share_price': share_price
        }
    
    def _apply_risk_adjustments(self, equity_data: Dict, terminal_caps: Dict, 
                               company_type, pv_fcf: float) -> Dict:
        """Apply risk adjustments for extreme valuation cases"""
        from ....models.company import CompanyType
        
        original_share_price = equity_data['share_price']
        adjusted_share_price = original_share_price
        risk_discount = 0.0
        
        # Apply extreme case discount for turnaround companies with impossible terminal dominance
        # Handle both string and enum company_type values
        is_turnaround = (company_type == CompanyType.TURNAROUND or 
                        company_type == CompanyType.TURNAROUND.value or
                        str(company_type).lower() == 'turnaround')
        
        if (is_turnaround and 
            pv_fcf < 0 and 
            terminal_caps['original_ratio'] > 1.0):
            
            # Calculate logical discount based on terminal dominance severity
            base_discount = 0.40  # Base discount for negative FCF turnaround
            
            # Additional penalty for mathematical impossibility
            excess_dominance = max(0, terminal_caps['original_ratio'] - 1.0)
            dominance_penalty = min(0.40, excess_dominance * 2.0)
            
            risk_discount = min(0.80, base_discount + dominance_penalty)
            adjusted_share_price = original_share_price * (1 - risk_discount)
            
            debug_print(f"Risk adjustment applied: {risk_discount:.0%} discount")
            debug_print(f"Original price: ${original_share_price:.2f} -> Adjusted: ${adjusted_share_price:.2f}")
        
        # Return updated equity data
        return {
            **equity_data,
            'share_price': adjusted_share_price,
            'original_share_price': original_share_price,
            'risk_discount': risk_discount
        }
    
    def _calculate_confidence(self, terminal_caps: Dict) -> str:
        """Calculate confidence based on terminal value dominance"""
        # Terminal value dominance
        if terminal_caps['original_ratio'] > 0.90:
            return "Low"
        elif terminal_caps['original_ratio'] > 0.80:
            return "Medium"
        else:
            return "High"
    
    def _compile_results(self, ticker_symbol: str, ticker, wacc_data: Dict, 
                        fcf_cagr: float, ebitda_cagr: float, fcf_future: float,
                        ebitda_future: float, terminal_data: Dict, terminal_caps: Dict,
                        projected_fcf: list, pv_fcf_list: list, pv_fcf: float,
                        pv_terminal_value: float, enterprise_value: float,
                        equity_data: Dict, confidence: str) -> Dict:
        """Compile all results into final dictionary"""
        
        return {
            'wacc': wacc_data['wacc'],
            'cost_equity': wacc_data['cost_equity'],
            'ev_ebitda_multiple': ticker.info.get('enterpriseToEbitda', self.config.default_ev_ebitda_multiple),
            'fcf_cagr': fcf_cagr,
            'ebitda_cagr': ebitda_cagr,
            'fcf_future': fcf_future,
            'ebitda_future': ebitda_future,
            'terminal_value_pg': terminal_data['terminal_value_pg'],
            'terminal_value_ebitda_multiple': terminal_data['terminal_value_ebitda_multiple'],
            'average_terminal_value': terminal_data['average_terminal_value'],
            'adjusted_terminal_value': terminal_caps['adjusted_terminal_value'],
            'terminal_adjustment_factor': terminal_caps['adjustment_factor'],
            'projected_free_cash_flows': projected_fcf,
            'present_value_free_cash_flows': pv_fcf_list,
            'pv_fcf': pv_fcf,
            'pv_terminal_value': pv_terminal_value,
            'enterprise_value': enterprise_value,
            'adjusted_debt': equity_data['adjusted_debt'],
            'equity_value': equity_data['equity_value'],
            'share_price': equity_data['share_price'],
            'ticker_symbol': ticker_symbol,
            'last_close_price': ticker.info.get("previousClose", 0),
            'confidence': confidence,
            'terminal_ratio': terminal_caps['original_ratio']
        }
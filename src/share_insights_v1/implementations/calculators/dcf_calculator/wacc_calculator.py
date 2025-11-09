from typing import Dict
from ....utils.debug_printer import debug_print
from ....utils import beta_calculator
from ....config.config import FinanceConfig
import yfinance as yf

class WACCCalculator:
    """Handles WACC and cost of capital calculations"""
    
    def __init__(self, config: FinanceConfig = None):
        self.config = config or FinanceConfig()
    
    def calculate_wacc(self, ticker) -> Dict:
        """Calculate WACC with all components"""
        cost_equity = self._calculate_cost_of_equity(ticker)
        debt_to_equity = ticker.info.get('debtToEquity', 0) / 100
        
        debug_print(f'Cost of Equity: {cost_equity}')
        debug_print(f'Debt to Equity: {debt_to_equity:.2f}')
        
        # Calculate weights
        if debt_to_equity == 0 or debt_to_equity is None:
            equity_weight = 1.0
            debt_weight = 0.0
        else:
            equity_weight = 1 / (1 + debt_to_equity)
            debt_weight = debt_to_equity / (1 + debt_to_equity)
        
        wacc = (equity_weight * cost_equity + 
                debt_weight * self.config.cost_of_debt * (1 - self.config.tax_rate))
        
        debug_print(f'WACC: {wacc}')
        
        return {
            'wacc': wacc,
            'cost_equity': cost_equity,
            'debt_to_equity': debt_to_equity,
            'equity_weight': equity_weight,
            'debt_weight': debt_weight
        }
    
    def _calculate_cost_of_equity(self, ticker) -> float:
        """Calculate cost of equity using CAPM"""
        beta = beta_calculator.BetaCalculator(ticker_symbol=ticker.info.get('symbol')).get_beta_with_fallbacks()
        risk_free_rate = self._get_risk_free_rate()
        
        cost_equity = risk_free_rate + beta * (self.config.market_return - risk_free_rate)
        return cost_equity
    
    def _get_risk_free_rate(self, ticker_symbol: str = '^TNX') -> float:
        """Get risk-free rate from 10-year treasury"""
        try:
            treasury = yf.Ticker(ticker_symbol)
            risk_free_rate = treasury.info['previousClose'] / 100
            return risk_free_rate
        except:
            debug_print("Warning: Could not fetch risk-free rate, using default")
            return 0.04  # Default 4%
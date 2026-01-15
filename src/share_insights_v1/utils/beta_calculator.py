import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .debug_printer import debug_print
import warnings

warnings.filterwarnings('ignore')

class BetaCalculator:
    """
    Comprehensive beta calculation with multiple fallback strategies
    """
    
    def __init__(self, ticker_symbol, market_index='^GSPC'):
        self.ticker_symbol = ticker_symbol.upper()
        self.market_index = market_index
        self.ticker = yf.Ticker(ticker_symbol)
        
    def get_beta_with_fallbacks(self, period_years=2):
        """
        Main function that tries multiple approaches to get beta
        """
        debug_print(f"Getting beta for {self.ticker_symbol}...")
        
        # Method 1: Try yfinance info beta
        beta = self.get_yfinance_beta()
        debug_print(f"  yfinance beta: {beta}")
        if beta is not None and self.is_valid_beta(beta):
            debug_print(f"✓ Using yfinance beta: {beta:.3f}")
            return beta
        
        # Method 2: Calculate beta from price data
        beta = self.calculate_beta_from_prices(period_years)
        if beta is not None and self.is_valid_beta(beta):
            debug_print(f"✓ Calculated beta from price data: {beta:.3f}")
            return beta
        
        # Method 3: Industry average beta
        beta = self.get_industry_beta()
        if beta is not None:
            debug_print(f"✓ Using industry average beta: {beta:.3f}")
            return beta
        
        # Method 4: Sector average beta
        beta = self.get_sector_beta()
        if beta is not None:
            debug_print(f"✓ Using sector average beta: {beta:.3f}")
            return beta
        
        # Method 5: Company characteristics-based beta
        beta = self.estimate_beta_from_characteristics()
        if beta is not None:
            debug_print(f"✓ Using characteristics-based beta: {beta:.3f}")
            return beta
        
        # Final fallback: Market average
        default_beta = 1.0
        debug_print(f"⚠️  Using default market beta: {default_beta}")
        return default_beta
    
    def get_yfinance_beta(self):
        """
        Try to get beta from yfinance info
        """
        try:
            info = self.ticker.info
            beta = info.get('beta')
            if beta is not None and not pd.isna(beta):
                return float(beta)
        except Exception as e:
            debug_print(f"  yfinance beta failed: {str(e)[:50]}...")
        return None
    
    def calculate_beta_from_prices(self, years=2, min_data_points=50):
        """
        Calculate beta from historical price data using regression
        """
        try:
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years*365)
            
            # Download stock and market data
            stock_data = yf.download(self.ticker_symbol, start=start_date, end=end_date, progress=False)
            market_data = yf.download(self.market_index, start=start_date, end=end_date, progress=False)
            
            if stock_data.empty or market_data.empty:
                debug_print(f"  No price data available for beta calculation")
                return None
            
            # Calculate returns
            stock_returns = stock_data['Adj Close'].pct_change().dropna()
            market_returns = market_data['Adj Close'].pct_change().dropna()
            
            # Align dates
            aligned_data = pd.concat([stock_returns, market_returns], axis=1, join='inner')
            aligned_data.columns = ['stock', 'market']
            aligned_data = aligned_data.dropna()
            
            if len(aligned_data) < min_data_points:
                debug_print(f"  Insufficient data points: {len(aligned_data)} < {min_data_points}")
                return None
            
            # Calculate beta using regression
            covariance = np.cov(aligned_data['stock'], aligned_data['market'])[0, 1]
            market_variance = np.var(aligned_data['market'])
            
            if market_variance == 0:
                debug_print(f"  Market variance is zero")
                return None
            
            beta = covariance / market_variance
            
            # Calculate R-squared for quality check
            correlation = np.corrcoef(aligned_data['stock'], aligned_data['market'])[0, 1]
            r_squared = correlation ** 2
            
            debug_print(f"  Calculated beta: {beta:.3f} (R²: {r_squared:.3f}, n={len(aligned_data)})")
            
            # Quality check - reject if R-squared is too low
            if r_squared < 0.1:  # Less than 10% explanatory power
                debug_print(f"  Low R-squared ({r_squared:.3f}) - beta may be unreliable")
                return None
            
            return beta
            
        except Exception as e:
            debug_print(f"  Beta calculation from prices failed: {str(e)[:50]}...")
            return None
    
    def get_industry_beta(self):
        """
        Get beta based on industry classification
        """
        try:
            info = self.ticker.info
            industry = info.get('industry', '').lower()
            
            # Industry beta mapping (based on historical averages)
            industry_betas = {
                # Technology
                'software': 1.3,
                'hardware': 1.4,
                'semiconductors': 1.5,
                'internet': 1.4,
                'telecommunications': 0.8,
                
                # Healthcare
                'biotechnology': 1.2,
                'pharmaceuticals': 0.9,
                'medical devices': 1.0,
                'healthcare': 0.9,
                
                # Financial
                'banks': 1.2,
                'insurance': 1.1,
                'investment': 1.4,
                'financial services': 1.2,
                'reit': 0.8,
                
                # Consumer
                'retail': 1.2,
                'restaurants': 1.3,
                'apparel': 1.4,
                'automotive': 1.3,
                'consumer goods': 1.0,
                
                # Industrial
                'aerospace': 1.1,
                'construction': 1.3,
                'machinery': 1.2,
                'transportation': 1.2,
                'logistics': 1.1,
                
                # Materials & Energy
                'oil & gas': 1.4,
                'mining': 1.5,
                'chemicals': 1.1,
                'steel': 1.4,
                'utilities': 0.6,
                
                # Others
                'agriculture': 0.8,
                'tobacco': 0.7,
                'defense': 0.9
            }
            
            # Find matching industry
            for key, beta in industry_betas.items():
                if key in industry:
                    debug_print(f"  Industry '{industry}' matched to '{key}'")
                    return beta
            
            debug_print(f"  Industry '{industry}' not found in mapping")
            return None
            
        except Exception as e:
            debug_print(f"  Industry beta lookup failed: {str(e)[:50]}...")
            return None
    
    def get_sector_beta(self):
        """
        Get beta based on sector classification (broader than industry)
        """
        try:
            info = self.ticker.info
            sector = info.get('sector', '').lower()
            
            # Sector beta mapping
            sector_betas = {
                'technology': 1.3,
                'healthcare': 1.0,
                'financial services': 1.2,
                'consumer cyclical': 1.2,
                'consumer defensive': 0.8,
                'industrials': 1.1,
                'energy': 1.3,
                'materials': 1.2,
                'utilities': 0.6,
                'real estate': 0.8,
                'communication services': 1.1
            }
            
            # Find matching sector
            for key, beta in sector_betas.items():
                if key in sector:
                    debug_print(f"  Sector '{sector}' matched to '{key}'")
                    return beta
            
            debug_print(f"  Sector '{sector}' not found in mapping")
            return None
            
        except Exception as e:
            debug_print(f"  Sector beta lookup failed: {str(e)[:50]}...")
            return None
    
    def estimate_beta_from_characteristics(self):
        """
        Estimate beta based on company financial characteristics
        """
        try:
            info = self.ticker.info
            
            # Base beta
            beta_estimate = 1.0
            
            # Adjust based on company size (smaller = higher beta)
            market_cap = info.get('marketCap', 0)
            if market_cap > 0:
                if market_cap > 50e9:  # Large cap (>$50B)
                    size_adjustment = -0.2
                elif market_cap > 10e9:  # Mid cap ($10B-$50B)
                    size_adjustment = 0.0
                elif market_cap > 2e9:  # Small cap ($2B-$10B)
                    size_adjustment = 0.2
                else:  # Micro cap (<$2B)
                    size_adjustment = 0.4
                    
                beta_estimate += size_adjustment
                debug_print(f"  Size adjustment: {size_adjustment:+.2f} (Market cap: ${market_cap/1e9:.1f}B)")
            
            # Adjust based on leverage (higher debt = higher beta)
            debt_to_equity = info.get('debtToEquity', 0)
            if debt_to_equity and debt_to_equity > 0:
                leverage_ratio = debt_to_equity / 100  # Convert from percentage
                if leverage_ratio > 1.0:  # High leverage
                    leverage_adjustment = 0.3
                elif leverage_ratio > 0.5:  # Moderate leverage
                    leverage_adjustment = 0.1
                else:  # Low leverage
                    leverage_adjustment = -0.1
                    
                beta_estimate += leverage_adjustment
                debug_print(f"  Leverage adjustment: {leverage_adjustment:+.2f} (D/E: {leverage_ratio:.2f})")
            
            # Adjust based on profitability volatility (if available)
            try:
                # Get profit margins for volatility estimate
                profit_margins = []
                income_stmt = self.ticker.income_stmt
                if not income_stmt.empty and 'Net Income' in income_stmt.index:
                    net_incomes = income_stmt.loc['Net Income']
                    # Simple volatility proxy
                    if len(net_incomes) > 1:
                        income_volatility = np.std(net_incomes) / np.abs(np.mean(net_incomes))
                        if income_volatility > 1.0:  # High volatility
                            volatility_adjustment = 0.2
                        elif income_volatility > 0.5:  # Moderate volatility
                            volatility_adjustment = 0.1
                        else:  # Low volatility
                            volatility_adjustment = -0.1
                            
                        beta_estimate += volatility_adjustment
                        debug_print(f"  Volatility adjustment: {volatility_adjustment:+.2f}")
            except:
                pass  # Skip if data not available
            
            # Ensure reasonable bounds
            beta_estimate = max(0.2, min(beta_estimate, 2.5))
            
            debug_print(f"  Characteristics-based beta estimate: {beta_estimate:.3f}")
            return beta_estimate
            
        except Exception as e:
            debug_print(f"  Characteristics-based beta failed: {str(e)[:50]}...")
            return None
    
    def is_valid_beta(self, beta, min_beta=0.1, max_beta=3.0):
        """
        Check if beta value is reasonable
        """
        if beta is None or pd.isna(beta):
            return False
        return min_beta <= beta <= max_beta
    
    def get_beta_with_unleveraging(self, target_debt_ratio=None):
        """
        Calculate unlevered beta and re-lever for different debt structure
        Useful for companies undergoing debt restructuring
        """
        try:
            # Get base beta
            levered_beta = self.get_beta_with_fallbacks()
            
            info = self.ticker.info
            current_debt_equity = info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else 0
            tax_rate = 0.21  # Assume corporate tax rate
            
            # Unlever the beta (remove effect of current debt)
            if current_debt_equity > 0:
                unlevered_beta = levered_beta / (1 + (1 - tax_rate) * current_debt_equity)
            else:
                unlevered_beta = levered_beta
            
            debug_print(f"Unlevered beta: {unlevered_beta:.3f}")
            
            # Re-lever with target debt ratio (if provided)
            if target_debt_ratio is not None:
                relevered_beta = unlevered_beta * (1 + (1 - tax_rate) * target_debt_ratio)
                debug_print(f"Re-levered beta (D/E={target_debt_ratio:.2f}): {relevered_beta:.3f}")
                return relevered_beta
            
            return unlevered_beta
            
        except Exception as e:
            debug_print(f"Beta unlevering failed: {e}")
            return self.get_beta_with_fallbacks()

def get_robust_beta(ticker_symbol, market_index='^GSPC', period_years=2):
    """
    Simple wrapper function for easy integration with existing DCF code
    """
    calculator = BetaCalculator(ticker_symbol, market_index)
    return calculator.get_beta_with_fallbacks(period_years)

def cost_of_equity_with_robust_beta(ticker_symbol, market_return, risk_free_rate=0.045):
    """
    Calculate cost of equity with robust beta handling
    """
    debug_print(f"\nCalculating cost of equity for {ticker_symbol}:")
    
    # Get robust beta
    beta = get_robust_beta(ticker_symbol)
    
    # Calculate cost of equity
    cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)
    
    debug_print(f"Final calculation:")
    debug_print(f"  Risk-free rate: {risk_free_rate:.2%}")
    debug_print(f"  Market return: {market_return:.2%}")
    debug_print(f"  Beta: {beta:.3f}")
    debug_print(f"  Cost of equity: {cost_of_equity:.2%}")
    
    return cost_of_equity, beta

# Example usage and testing
def test_beta_calculations():
    """
    Test beta calculation with various scenarios
    """
    test_cases = [
        'AAPL',  # Should have beta available
        'TSLA',  # High beta stock
        'KO',    # Low beta stock  
        'AAL',   # Distressed company
        'FAKE123'  # Non-existent ticker
    ]
    
    debug_print("="*80)
    debug_print("BETA CALCULATION TESTING")
    debug_print("="*80)
    
    results = {}
    
    for ticker in test_cases:
        debug_print(f"\n{'-'*60}")
        debug_print(f"Testing: {ticker}")
        debug_print(f"{'-'*60}")
        
        try:
            calculator = BetaCalculator(ticker)
            beta = calculator.get_beta_with_fallbacks()
            results[ticker] = beta
            
        except Exception as e:
            debug_print(f"Error testing {ticker}: {e}")
            results[ticker] = None
    
    # Summary
    debug_print(f"\n{'='*60}")
    debug_print("BETA CALCULATION SUMMARY")
    debug_print(f"{'='*60}")
    for ticker, beta in results.items():
        if beta is not None:
            debug_print(f"{ticker:>8}: {beta:.3f}")
        else:
            debug_print(f"{ticker:>8}: FAILED")

if __name__ == "__main__":
    # Run tests
    test_beta_calculations()
    
    # Example integration
    debug_print(f"\n{'='*80}")
    debug_print("COST OF EQUITY CALCULATION EXAMPLE")
    debug_print(f"{'='*80}")
    
    cost_of_equity, beta = cost_of_equity_with_robust_beta('AAL', market_return=0.08)
    debug_print(f"\nFinal result for AAL: Cost of Equity = {cost_of_equity:.2%}")
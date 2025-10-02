import yfinance as yf
import pandas as pd
import pandas_ta as pd_ta
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')
from . import dcf_yf
from .config import FinanceConfig
from .stock_analyzer import CompanyType
from ..util.debug_printer import debug_print
import json

class BacktestAnalyzer:
    """Backtesting analyzer to test predictions against actual outcomes"""
    
    def __init__(self, ticker: str, analysis_date: str, config: Optional[FinanceConfig] = None):
        """
        Initialize backtesting analyzer
        
        Args:
            ticker: Stock symbol
            analysis_date: Date to run analysis from (YYYY-MM-DD format)
            config: Finance configuration
        """
        self.ticker = ticker.upper()
        self.analysis_date = datetime.strptime(analysis_date, '%Y-%m-%d')
        self.config = config or FinanceConfig()
        self.stock = yf.Ticker(ticker)
        
        # Get historical data up to analysis date
        self.historical_data = self._get_historical_data()
        self.company_type = None
        self.error_analysis = []
        
    def _get_historical_data(self) -> Dict:
        """Get all historical data up to analysis date"""
        try:
            # Get price history up to analysis date
            end_date = self.analysis_date + timedelta(days=1)
            start_date = self.analysis_date - timedelta(days=1095)  # 3 years of data
            
            hist_prices = self.stock.history(start=start_date, end=end_date)
            
            # Get financial statements (these are typically quarterly/annual)
            income_stmt = self.stock.income_stmt
            balance_sheet = self.stock.balance_sheet
            cashflow = self.stock.cashflow
            
            return {
                'prices': hist_prices,
                'income_stmt': income_stmt,
                'balance_sheet': balance_sheet,
                'cashflow': cashflow
            }
        except Exception as e:
            self.error_analysis.append(f"Historical data fetch error: {e}")
            return {}
    
    def get_historical_financial_metrics(self) -> Dict:
        """Extract financial metrics as they existed on analysis date"""
        try:
            if self.historical_data['prices'].empty:
                return {}
            
            # Get price on analysis date
            analysis_price = self._get_price_on_date(self.analysis_date)
            
            # Get financial data closest to analysis date
            metrics = {
                'analysis_date': self.analysis_date.strftime('%Y-%m-%d'),
                'historical_price': analysis_price,
                'market_cap': 0,
                'enterprise_value': 0,
                'total_revenue': 0,
                'net_income': 0,
                'free_cash_flow': 0,
                'total_debt': 0,
                'total_cash': 0,
                'shares_outstanding': 0,
                'beta': 1.0,
                'pe_ratio': None,
                'pb_ratio': None,
                'ps_ratio': None,
                'revenue_growth': 0,
                'earnings_growth': 0
            }
            
            # Extract from financial statements (use data available before analysis date)
            if not self.historical_data['income_stmt'].empty:
                income_stmt = self.historical_data['income_stmt']
                # Get most recent data before analysis date
                available_dates = [d for d in income_stmt.columns if d <= self.analysis_date]
                if available_dates:
                    latest_date = max(available_dates)
                    
                    if 'Total Revenue' in income_stmt.index:
                        metrics['total_revenue'] = income_stmt.loc['Total Revenue', latest_date]
                    
                    if 'Net Income' in income_stmt.index:
                        metrics['net_income'] = income_stmt.loc['Net Income', latest_date]
            
            # Calculate revenue growth from historical data
            metrics['revenue_growth'] = self._calculate_historical_revenue_growth()
            
            # Get shares outstanding (approximate from market data)
            if analysis_price > 0 and metrics['total_revenue'] > 0:
                # Estimate shares outstanding (this is approximate)
                metrics['shares_outstanding'] = 1000000000  # Default estimate
                metrics['market_cap'] = analysis_price * metrics['shares_outstanding']
            
            debug_print(f"Historical metrics for {self.ticker} on {self.analysis_date}: {metrics}")
            return metrics
            
        except Exception as e:
            self.error_analysis.append(f"Historical metrics error: {e}")
            return {}
    
    def _get_price_on_date(self, target_date: datetime) -> float:
        """Get stock price on specific date"""
        try:
            prices = self.historical_data['prices']
            if prices.empty:
                return 0
            
            # Handle timezone-aware dates
            target_date_tz = target_date
            if prices.index.tz is not None:
                target_date_tz = target_date.replace(tzinfo=prices.index.tz)
            
            # Find closest date
            closest_date = min(prices.index, key=lambda x: abs((x - target_date_tz).total_seconds()))
            return float(prices.loc[closest_date, 'Close'])
        except Exception as e:
            debug_print(f"Price lookup error: {e}")
            return 0
    
    def _calculate_historical_revenue_growth(self) -> float:
        """Calculate revenue growth rate from historical data"""
        try:
            income_stmt = self.historical_data['income_stmt']
            if income_stmt.empty or 'Total Revenue' not in income_stmt.index:
                return 0
            
            # Get revenue data before analysis date (handle timezone)
            analysis_date_check = self.analysis_date
            available_dates = []
            for d in income_stmt.columns:
                try:
                    # Convert to comparable format
                    if hasattr(d, 'tz') and d.tz is not None:
                        check_date = analysis_date_check.replace(tzinfo=d.tz)
                    else:
                        check_date = analysis_date_check
                    
                    if d <= check_date:
                        available_dates.append(d)
                except:
                    # Fallback: convert both to date for comparison
                    if d.date() <= analysis_date_check.date():
                        available_dates.append(d)
            if len(available_dates) < 2:
                return 0
            
            # Sort dates and get recent growth
            available_dates.sort(reverse=True)
            recent_revenue = income_stmt.loc['Total Revenue', available_dates[0]]
            previous_revenue = income_stmt.loc['Total Revenue', available_dates[1]]
            
            if previous_revenue > 0:
                return (recent_revenue - previous_revenue) / previous_revenue
            return 0
            
        except Exception as e:
            debug_print(f"Revenue growth calculation error: {e}")
            return 0
    
    def historical_technical_analysis(self) -> Dict:
        """Run technical analysis as it would have appeared on analysis date"""
        try:
            # Get price data up to analysis date
            prices = self.historical_data['prices']
            if prices.empty:
                return {'error': 'No historical price data'}
            
            # Filter data up to analysis date (handle timezone)
            analysis_date_tz = self.analysis_date
            if prices.index.tz is not None:
                # Make analysis_date timezone-aware to match price data
                analysis_date_tz = self.analysis_date.replace(tzinfo=prices.index.tz)
            
            analysis_data = prices[prices.index <= analysis_date_tz]
            if len(analysis_data) < 50:
                return {'error': 'Insufficient historical data'}
            
            current_price = analysis_data['Close'].iloc[-1]
            
            # Calculate moving averages as they existed on analysis date
            ma_20 = analysis_data['Close'].rolling(window=20).mean().iloc[-1] if len(analysis_data) >= 20 else None
            ma_50 = analysis_data['Close'].rolling(window=50).mean().iloc[-1] if len(analysis_data) >= 50 else None
            ma_200 = analysis_data['Close'].rolling(window=200).mean().iloc[-1] if len(analysis_data) >= 200 else None
            
            # Calculate volatility from historical data
            volatility = analysis_data['Close'].pct_change().std() * np.sqrt(252)
            
            # 52-week high/low as of analysis date
            year_ago = self.analysis_date - timedelta(days=365)
            if analysis_data.index.tz is not None:
                year_ago = year_ago.replace(tzinfo=analysis_data.index.tz)
            
            year_data = analysis_data[analysis_data.index >= year_ago]
            high_52w = year_data['High'].max() if not year_data.empty else current_price
            low_52w = year_data['Low'].min() if not year_data.empty else current_price
            
            # Determine trend
            trend = 'Sideways'
            predicted_price = current_price
            
            if ma_200 is not None and ma_50 is not None:
                if current_price > ma_50 > ma_200:
                    trend = 'Strong Uptrend'
                    predicted_price = current_price * (1 + volatility)
                elif current_price < ma_50 < ma_200:
                    trend = 'Strong Downtrend'
                    predicted_price = current_price * (1 - volatility * 0.5)
                elif current_price > ma_50:
                    trend = 'Uptrend'
                    predicted_price = current_price * (1 + volatility * 0.5)
                elif current_price < ma_50:
                    trend = 'Downtrend'
                    predicted_price = current_price * (1 - volatility * 0.3)
            
            # Calculate RSI as of analysis date
            rsi_14 = None
            try:
                analysis_data_copy = analysis_data.copy()
                analysis_data_copy['rsi'] = pd_ta.rsi(analysis_data_copy['Close'], length=14)
                rsi_14 = analysis_data_copy['rsi'].iloc[-1]
            except:
                pass
            
            return {
                'method': 'Historical Technical Analysis',
                'analysis_date': self.analysis_date.strftime('%Y-%m-%d'),
                'historical_price': float(current_price),
                'predicted_price': predicted_price,
                'ma_20': float(ma_20) if ma_20 is not None else None,
                'ma_50': float(ma_50) if ma_50 is not None else None,
                'ma_200': float(ma_200) if ma_200 is not None else None,
                'trend': trend,
                'volatility_annual': volatility,
                'high_52w': float(high_52w),
                'low_52w': float(low_52w),
                'rsi_14': float(rsi_14) if rsi_14 is not None else None,
                'distance_from_high': (current_price - high_52w) / high_52w,
                'distance_from_low': (current_price - low_52w) / low_52w
            }
            
        except Exception as e:
            self.error_analysis.append(f"Historical technical analysis error: {e}")
            return {'error': f"Technical analysis failed: {e}"}
    
    def historical_dcf_analysis(self) -> Dict:
        """Run DCF analysis using historical data"""
        try:
            historical_metrics = self.get_historical_financial_metrics()
            if not historical_metrics:
                return {'error': 'No historical financial data'}
            
            # Use historical price as current price for DCF
            historical_price = historical_metrics['historical_price']
            if historical_price <= 0:
                return {'error': 'Invalid historical price'}
            
            # Run DCF with historical data (simplified version)
            # This would need to be adapted to use historical financials
            share_price, equity_value = dcf_yf.get_share_price(
                ticker_symbol=self.ticker, 
                config=self.config
            )
            
            upside_downside = ((share_price - historical_price) / historical_price) * 100
            
            return {
                'method': 'Historical DCF Analysis',
                'analysis_date': self.analysis_date.strftime('%Y-%m-%d'),
                'predicted_price': share_price,
                'historical_price': historical_price,
                'upside_downside_pct': upside_downside,
                'total_equity_value': equity_value,
                'confidence': 'Medium',
                'valuation': 'Undervalued' if upside_downside > 20 else 'Overvalued' if upside_downside < -20 else 'Fair Value'
            }
            
        except Exception as e:
            self.error_analysis.append(f"Historical DCF error: {e}")
            return {'error': f"DCF analysis failed: {e}"}
    
    def get_actual_performance(self, months_forward: int = 12) -> Dict:
        """Get actual stock performance after analysis date"""
        try:
            future_date = self.analysis_date + timedelta(days=months_forward * 30)
            current_date = datetime.now()
            
            # Don't go beyond current date
            end_date = min(future_date, current_date)
            
            # Get price data from analysis date to end date
            future_prices = self.stock.history(
                start=self.analysis_date, 
                end=end_date + timedelta(days=1)
            )
            
            if future_prices.empty:
                return {'error': 'No future price data available'}
            
            start_price = future_prices['Close'].iloc[0]
            end_price = future_prices['Close'].iloc[-1]
            
            actual_return = (end_price - start_price) / start_price * 100
            
            # Calculate volatility during period
            volatility = future_prices['Close'].pct_change().std() * np.sqrt(252)
            
            # High and low during period
            period_high = future_prices['High'].max()
            period_low = future_prices['Low'].min()
            
            return {
                'analysis_date': self.analysis_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'start_price': float(start_price),
                'end_price': float(end_price),
                'actual_return_pct': actual_return,
                'period_high': float(period_high),
                'period_low': float(period_low),
                'volatility': volatility,
                'days_elapsed': len(future_prices)
            }
            
        except Exception as e:
            self.error_analysis.append(f"Actual performance error: {e}")
            return {'error': f"Performance calculation failed: {e}"}
    
    def run_backtest(self, months_forward: int = 12) -> Dict:
        """Run complete backtest analysis"""
        print(f"\n=== BACKTESTING {self.ticker} FROM {self.analysis_date.strftime('%Y-%m-%d')} ===")
        
        # Run historical analysis
        historical_metrics = self.get_historical_financial_metrics()
        technical_analysis = self.historical_technical_analysis()
        dcf_analysis = self.historical_dcf_analysis()
        
        # Get actual performance
        actual_performance = self.get_actual_performance(months_forward)
        
        # Calculate prediction accuracy
        accuracy_results = self._calculate_accuracy(
            technical_analysis, dcf_analysis, actual_performance
        )
        
        backtest_results = {
            'ticker': self.ticker,
            'analysis_date': self.analysis_date.strftime('%Y-%m-%d'),
            'backtest_type': 'Historical Analysis',
            'historical_metrics': historical_metrics,
            'predictions': {
                'technical_analysis': technical_analysis,
                'dcf_analysis': dcf_analysis
            },
            'actual_performance': actual_performance,
            'accuracy_analysis': accuracy_results,
            'errors': self.error_analysis
        }
        
        return backtest_results
    
    def _calculate_accuracy(self, technical: Dict, dcf: Dict, actual: Dict) -> Dict:
        """Calculate prediction accuracy"""
        try:
            if 'error' in actual:
                return {'error': 'Cannot calculate accuracy without actual performance'}
            
            actual_return = actual['actual_return_pct']
            accuracy = {}
            
            # Technical analysis accuracy
            if 'error' not in technical and 'predicted_price' in technical:
                historical_price = technical['historical_price']
                predicted_price = technical['predicted_price']
                predicted_return = (predicted_price - historical_price) / historical_price * 100
                
                accuracy['technical'] = {
                    'predicted_return': predicted_return,
                    'actual_return': actual_return,
                    'error_pct': abs(predicted_return - actual_return),
                    'direction_correct': (predicted_return > 0) == (actual_return > 0)
                }
            
            # DCF analysis accuracy
            if 'error' not in dcf and 'predicted_price' in dcf:
                historical_price = dcf['historical_price']
                predicted_price = dcf['predicted_price']
                predicted_return = (predicted_price - historical_price) / historical_price * 100
                
                accuracy['dcf'] = {
                    'predicted_return': predicted_return,
                    'actual_return': actual_return,
                    'error_pct': abs(predicted_return - actual_return),
                    'direction_correct': (predicted_return > 0) == (actual_return > 0)
                }
            
            return accuracy
            
        except Exception as e:
            return {'error': f"Accuracy calculation failed: {e}"}

def test_backtest(ticker: str = "AAPL", analysis_date: str = "2023-10-01"):
    """Test backtesting functionality"""
    
    analyzer = BacktestAnalyzer(ticker, analysis_date)
    results = analyzer.run_backtest(months_forward=12)
    
    print(f"\n=== BACKTEST RESULTS ===")
    print(f"Ticker: {results['ticker']}")
    print(f"Analysis Date: {results['analysis_date']}")
    
    if 'error' not in results['actual_performance']:
        actual = results['actual_performance']
        print(f"Actual Performance: {actual['actual_return_pct']:.1f}%")
        print(f"Period: {actual['start_price']:.2f} -> {actual['end_price']:.2f}")
    
    # Print prediction accuracy
    accuracy = results.get('accuracy_analysis', {})
    if 'technical' in accuracy:
        tech = accuracy['technical']
        print(f"Technical Prediction: {tech['predicted_return']:.1f}% (Error: {tech['error_pct']:.1f}%)")
        print(f"Direction Correct: {tech['direction_correct']}")
    
    if 'dcf' in accuracy:
        dcf = accuracy['dcf']
        print(f"DCF Prediction: {dcf['predicted_return']:.1f}% (Error: {dcf['error_pct']:.1f}%)")
        print(f"Direction Correct: {dcf['direction_correct']}")
    
    # Save results
    filename = f"backtest_{ticker.lower()}_{analysis_date.replace('-', '')}.json"
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nBacktest results saved to {filename}")
    return results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        ticker = sys.argv[1]
        analysis_date = sys.argv[2]
        test_backtest(ticker, analysis_date)
    else:
        # Default test
        test_backtest("AMZN", "2023-10-01")
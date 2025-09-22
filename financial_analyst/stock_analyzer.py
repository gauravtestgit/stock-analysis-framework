import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import warnings
warnings.filterwarnings('ignore')
import dcf_yf
from config import FinanceConfig
import os
from util.debug_printer import debug_print
import json

class CompanyType(Enum):
    MATURE_PROFITABLE = "mature_profitable"
    GROWTH_PROFITABLE = "growth_profitable"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"
    STARTUP_LOSS_MAKING = "startup_loss_making"
    REIT = "reit"
    FINANCIAL = "financial"
    COMMODITY = "commodity"

class StockAnalyzer:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(ticker)
        self.info = self.stock.info
        self.company_type = None
        self.error_analysis = []
        
    def classify_company(self) -> CompanyType:
        """Classify company type to determine appropriate valuation method"""
        try:
            market_cap = self.info.get('marketCap', 0)
            sector = self.info.get('sector', '')
            industry = self.info.get('industry', '')
            
            # Get financial data
            income_stmt = self.stock.income_stmt
            cashflow = self.stock.cashflow
            
            # Check profitability
            net_income = self.info.get('netIncomeToCommon', 0)
            fcf = 0
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0:
                    fcf = fcf_data.iloc[0]
            
            # Classification logic
            if 'Real Estate' in sector or 'REIT' in industry:
                return CompanyType.REIT
            elif 'Financial' in sector or 'Bank' in industry:
                return CompanyType.FINANCIAL
            elif sector in ['Energy', 'Materials'] or 'Mining' in industry:
                return CompanyType.COMMODITY
            elif net_income <= 0 and fcf <= 0 and market_cap < 5e9:  # <$5B market cap
                return CompanyType.STARTUP_LOSS_MAKING
            elif net_income <= 0 or fcf <= 0:
                return CompanyType.TURNAROUND
            elif market_cap > 50e9:  # >$50B market cap
                return CompanyType.MATURE_PROFITABLE
            elif self.info.get('revenueGrowth', 0) > 0.15:  # >15% revenue growth
                return CompanyType.GROWTH_PROFITABLE
            elif sector in ['Energy', 'Materials', 'Industrials']:
                return CompanyType.CYCLICAL
            else:
                return CompanyType.MATURE_PROFITABLE
                
        except Exception as e:
            self.error_analysis.append(f"classify_company():{str(e)}")
            return CompanyType.MATURE_PROFITABLE  # Default fallback

    def get_financial_metrics(self) -> Dict:
        """Extract key financial metrics for analysis"""
        try:
            metrics = {
                'market_cap': self.info.get('marketCap', 0),
                'enterprise_value': self.info.get('enterpriseValue', 0),
                'total_revenue': self.info.get('totalRevenue', 0),
                'net_income': self.info.get('netIncomeToCommon', 0),
                'free_cash_flow': 0,
                'total_debt': self.info.get('totalDebt', 0) or 0,
                'total_cash': self.info.get('totalCash', 0) or 0,
                'shares_outstanding': self.info.get('sharesOutstanding', 0),
                'current_price': self.info.get('currentPrice', 0),
                'beta': self.info.get('beta', 1.0),
                'pe_ratio': self.info.get('trailingPE'),
                'pb_ratio': self.info.get('priceToBook'),
                'ps_ratio': self.info.get('priceToSalesTrailing12Months'),
                'peg_ratio': self.info.get('pegRatio'),
                'roe': self.info.get('returnOnEquity'),
                'roa': self.info.get('returnOnAssets'),
                'debt_to_equity': self.info.get('debtToEquity', 0) / 100 if self.info.get('debtToEquity') else 0,
                'current_ratio': self.info.get('currentRatio'),
                'revenue_growth': self.info.get('revenueGrowth'),
                'earnings_growth': self.info.get('earningsGrowth'),
                'dividend_yield': self.info.get('dividendYield'),
                'payout_ratio': self.info.get('payoutRatio')
            }
            
            # Get FCF from cash flow statement
            cashflow = self.stock.cashflow
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0:
                    metrics['free_cash_flow'] = fcf_data.iloc[0]
            
            return metrics
        except Exception as e:
            self.error_analysis.append(f"get_financial_metrics():{str(e)}")
            print(f"Error getting financial metrics for {self.ticker}: {e}")
            return {}

    def dcf_analysis(self) -> Dict:
        """DCF analysis for mature/stable companies"""
        # This would integrate your existing DCF model
        try:
            config = FinanceConfig()
            config.default_cagr = 0.05
            config.max_cagr_threshold = 0.15
            config.use_default_ebitda_multiple = False
            share_price, equity_value = dcf_yf.get_share_price(ticker_symbol=self.ticker, config=config)
            current_price = self.info.get('currentPrice', 0)
            return {
                'method': 'DCF Analysis',
                'applicable': True,
                'estimated_value': share_price,  # Would call your DCF function here
                'current_price': current_price,
                'total_equity_value': equity_value,
                'confidence': 'High' if self.company_type == CompanyType.MATURE_PROFITABLE else 'Medium'
            }
        except Exception as e:
            self.error_analysis.append(f"dcf_analysis():{str(e)}")
            return{}

    def comparable_company_analysis(self) -> Dict:
        """Compare valuation multiples to industry peers"""
        try:
            industry = self.info.get('industry', '')
            sector = self.info.get('sector', '')
            
            # Industry average multiples (simplified - in practice, you'd get from database)
            industry_multiples = {
                'Technology': {'pe': 25, 'ps': 6, 'ev_ebitda': 18},
                'Healthcare': {'pe': 22, 'ps': 4, 'ev_ebitda': 15},
                'Consumer Cyclical': {'pe': 18, 'ps': 1.5, 'ev_ebitda': 12},
                'Financial Services': {'pe': 12, 'pb': 1.2, 'ev_ebitda': 10},
                'Energy': {'pe': 15, 'ps': 1.0, 'ev_ebitda': 8},
                'Utilities': {'pe': 16, 'ps': 2, 'ev_ebitda': 10},
                'Default': {'pe': 18, 'ps': 2.5, 'ev_ebitda': 12}
            }
            
            sector_multiples = industry_multiples.get(sector, industry_multiples['Default'])
            
            metrics = self.get_financial_metrics()
            
            # Calculate implied values based on multiples
            implied_values = {}
            
            if metrics['pe_ratio'] and sector_multiples.get('pe'):
                eps = metrics['net_income'] / metrics['shares_outstanding'] if metrics['shares_outstanding'] > 0 else 0
                implied_values['pe_based'] = eps * sector_multiples['pe']
            
            if metrics['ps_ratio'] and sector_multiples.get('ps'):
                sales_per_share = metrics['total_revenue'] / metrics['shares_outstanding'] if metrics['shares_outstanding'] > 0 else 0
                implied_values['ps_based'] = sales_per_share * sector_multiples['ps']
            
            return {
                'method': 'Comparable Company Analysis',
                'sector': sector,
                'industry_multiples': sector_multiples,
                'current_multiples': {
                    'pe': metrics['pe_ratio'],
                    'ps': metrics['ps_ratio'],
                    'pb': metrics['pb_ratio']
                },
                'implied_values': implied_values,
                'relative_valuation': 'Fair' if not implied_values else 'Undervalued' if max(implied_values.values()) > metrics['current_price'] * 1.2 else 'Overvalued'
            }
            
        except Exception as e:
            self.error_analysis.append(f"comparable_company_analysis():{str(e)}")
            return {'error': f"CCA analysis failed: {e}"}

    def technical_analysis(self) -> Dict:
        """Basic technical analysis indicators"""
        try:
            # Get historical data
            hist = self.stock.history(period='1y')
            if hist.empty:
                return {'error': 'No historical data available'}
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate moving averages
            ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
            ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
            ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1] if len(hist) >= 200 else None
            
            # Calculate volatility
            volatility = hist['Close'].pct_change().std() * np.sqrt(252)
            
            # Support and resistance levels
            high_52w = hist['High'].max()
            low_52w = hist['Low'].min()
            
            # Volume analysis
            avg_volume = hist['Volume'].mean()
            recent_volume = hist['Volume'].iloc[-10:].mean()
            
            # Determine trend based on Moving averages
            ma_trend = ''
            if ma_200 is not None and ma_50 is not None:
                # Full trend analysis with all 3 MAs
                if current_price > ma_50 > ma_200:
                    ma_trend = 'Strong Uptrend'
                elif current_price < ma_50 < ma_200:
                    ma_trend = 'Strong Downtrend'
                elif current_price > ma_50:
                    ma_trend = 'Uptrend'
                elif current_price < ma_50:
                    ma_trend = 'Downtrend'
                else:
                    ma_trend = 'Sideways'
            elif ma_50 is not None:
                # Simple trend analysis with just 50-day MA
                if current_price > ma_50:
                    ma_trend = 'Short-term Uptrend'
                elif current_price < ma_50:
                    ma_trend = 'Short-term Downtrend'
                else:
                    ma_trend = 'Sideways'
            elif ma_20 is not None:
                if current_price > ma_20:
                    ma_trend = 'Near-term Uptrend'
                elif current_price < ma_20:
                    ma_trend = 'Near-term Downtrend'
                else:
                    ma_trend = 'Sideways'
            else:
                ma_trend = 'Insufficient Moving Averages Data'
                
            return {
                'method': 'Technical Analysis',
                'current_price': current_price,
                'ma_20': ma_20,
                'ma_50': ma_50,
                'ma_200': ma_200,
                'trend': ma_trend,
                'volatility_annual': volatility,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'distance_from_high': (current_price - high_52w) / high_52w,
                'distance_from_low': (current_price - low_52w) / low_52w,
                'volume_trend': 'Above Average' if recent_volume > avg_volume * 1.2 else 'Below Average' if recent_volume < avg_volume * 0.8 else 'Normal'
            }
            
        except Exception as e:
            self.error_analysis.append(f"technical_analysis():{str(e)}")
            return {'error': f"Technical analysis failed: {e}"}

    def startup_analysis(self) -> Dict:
        """Specialized analysis for loss-making startups"""
        try:
            metrics = self.get_financial_metrics()
            
            # Cash runway analysis
            cashflow = self.stock.cashflow
            burn_rate = 0
            runway_quarters = 0
            
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0 and fcf_data.iloc[0] < 0:
                    burn_rate = abs(fcf_data.iloc[0]) / 4  # Quarterly burn
                    if metrics['total_cash'] > 0:
                        runway_quarters = metrics['total_cash'] / burn_rate
            
            # Revenue growth analysis
            income_stmt = self.stock.income_stmt
            revenue_growth_rates = []
            
            if not income_stmt.empty and 'Total Revenue' in income_stmt.index:
                revenue_data = income_stmt.loc['Total Revenue'].dropna()
                for i in range(1, min(len(revenue_data), 4)):
                    if revenue_data.iloc[i] > 0:
                        growth = (revenue_data.iloc[i-1] - revenue_data.iloc[i]) / revenue_data.iloc[i]
                        revenue_growth_rates.append(growth)
            
            return {
                'method': 'Startup Analysis',
                'cash_runway_years': runway_quarters / 4 if runway_quarters > 0 else 0,
                'quarterly_burn_rate': burn_rate,
                'revenue_growth_rates': revenue_growth_rates,
                'median_growth': np.median(revenue_growth_rates) if revenue_growth_rates else 0,
                'risk_level': 'Critical' if runway_quarters < 4 else 'High' if runway_quarters < 8 else 'Moderate',
                'valuation_approach': 'Revenue Multiple + Option Value'
            }
            
        except Exception as e:
            self.error_analysis.append(f"startup_analysis():{str(e)}")
            return {'error': f"Startup analysis failed: {e}"}

    def quality_score(self) -> Dict:
        """Assess overall company quality"""
        metrics = self.get_financial_metrics()
        score = 0
        max_score = 100
        missing_data_penalty = 0

        try:
        # Profitability (25 points)
            roe = metrics.get('roe', 0)
            if roe is not None:
                if roe > 0.15:
                    score += 15
                elif roe > 0.10:
                    score += 10
                elif roe > 0.05:
                    score += 5
            else:
                missing_data_penalty += 3
            net_income = metrics.get('net_income', 0)
            if net_income > 0:
                score += 10
        
        # Financial Health (25 points)
            debt_equity = metrics.get('debt_to_equity', 0)
            if debt_equity is not None:
                if debt_equity < 0.3:
                    score += 15
                elif debt_equity < 0.6:
                    score += 10
                elif debt_equity < 1.0:
                    score += 5
            else:
                missing_data_penalty += 2
            
            current_ratio = metrics.get('current_ratio', 0)
            if current_ratio is not None:
                if current_ratio > 2.0:
                    score += 10
                elif current_ratio > 1.5:
                    score += 7
                elif current_ratio > 1.0:
                    score += 3
            else:
                missing_data_penalty += 2

        
        # Growth (25 points)
            revenue_growth = metrics.get('revenue_growth', 0)
            if revenue_growth is not None:
                if revenue_growth > 0.20:
                    score += 15
                elif revenue_growth > 0.10:
                    score += 10
                elif revenue_growth > 0.05:
                    score += 5
            else:
                missing_data_penalty += 2

        
            earnings_growth = metrics.get('earnings_growth', 0)
            if earnings_growth is not None:
                if earnings_growth > 0.15:
                    score += 10
                elif earnings_growth > 0.05:
                    score += 5
            else:
                missing_data_penalty += 2
        
        # Valuation (25 points)
            pe_ratio = metrics.get('pe_ratio', 0)
            if pe_ratio is not None:
                if pe_ratio and 10 < pe_ratio < 20:
                    score += 15
                elif pe_ratio and 8 < pe_ratio < 25:
                    score += 10
                elif pe_ratio and pe_ratio < 30:
                    score += 5
            else:
                missing_data_penalty += 2
            
            peg_ratio = metrics.get('peg_ratio', 0)
            if peg_ratio is not None and peg_ratio > 0:
                if peg_ratio and peg_ratio < 1.0:
                    score += 10
                elif peg_ratio and peg_ratio < 1.5:
                    score += 5
            else:
                missing_data_penalty += 1
            
            final_score = max(0, score - missing_data_penalty)
            data_quality = "High" if missing_data_penalty <= 3 else "Medium" if missing_data_penalty <= 7 else "Low"
        
            return {
                'quality_score': score,
                'max_score': max_score,
                'missing_data_penalty': missing_data_penalty,
                'data_quality': data_quality,
                'quality_grade': 'A' if final_score >= 80 else 'B' if final_score >= 60 else 'C' if final_score >= 40 else 'D',
                'strengths': [],
                'weaknesses': []
            }
        except Exception as e:
            self.error_analysis.append(f"quality_score():{str(e)}")
            return {'error': f"Quality score calculation failed: {e}"}

    def comprehensive_analysis(self) -> Dict:
        """Run complete analysis based on company type"""
        print(f"\n=== Analyzing {self.ticker} ===")
        
        # Classify company
        self.company_type = self.classify_company()
        print(f"Company Type: {self.company_type.value}")
        
        # Get basic metrics
        metrics = self.get_financial_metrics()
        
        # Run appropriate analyses based on company type
        analyses = {
            'company_type': self.company_type.value,
            'financial_metrics': metrics,
            #'quality_score': self.quality_score() # remove post testing. add quality score at the end
        }
        
        # Always run technical analysis
        analyses['technical_analysis'] = self.technical_analysis()
        
        # Run specific analyses based on company type
        if self.company_type == CompanyType.STARTUP_LOSS_MAKING:
            analyses['startup_analysis'] = self.startup_analysis()
        elif self.company_type in [CompanyType.MATURE_PROFITABLE, CompanyType.GROWTH_PROFITABLE]:
            analyses['dcf_analysis'] = self.dcf_analysis()
            analyses['comparable_analysis'] = self.comparable_company_analysis()
        elif self.company_type == CompanyType.CYCLICAL:
            analyses['comparable_analysis'] = self.comparable_company_analysis()
            # Could add commodity price correlation analysis here
        else:
            analyses['comparable_analysis'] = self.comparable_company_analysis()
        
        # Generate summary recommendation
        try:
            analyses['quality_score'] = self.quality_score()
            analyses['summary'] = self.generate_summary(analyses)
        except Exception as e:
            self.error_analysis.append(f"generate_summary():{str(e)}")
            analyses['summary'] = {'error': f"Summary generation failed: {e}"}
        
        return analyses

    def generate_summary(self, analyses: Dict) -> Dict:
        """Generate investment summary and recommendation"""
        quality = analyses['quality_score']['quality_grade']
        
        # Simple recommendation logic (would be more sophisticated in practice)
        if quality in ['A', 'B'] and self.company_type in [CompanyType.MATURE_PROFITABLE, CompanyType.GROWTH_PROFITABLE]:
            recommendation = 'BUY'
        elif quality == 'C':
            recommendation = 'HOLD'
        else:
            recommendation = 'AVOID'
        
        return {
            'recommendation': recommendation,
            'confidence': 'High' if self.company_type == CompanyType.MATURE_PROFITABLE else 'Medium',
            'key_risks': ['Market risk', 'Company-specific risk'],
            'investment_thesis': f"{self.company_type.value} company with {quality} quality score"
        }

def analyze_multiple_stocks(tickers: List[str]) -> pd.DataFrame:
    """Analyze multiple stocks and return comparison DataFrame"""
    results = []
    
    for ticker in tickers:
        try:
            analyzer = StockAnalyzer(ticker)
            analysis = analyzer.comprehensive_analysis()
            
            # Extract key metrics for comparison
            result = {
                'Ticker': ticker,
                'Company_Type': analysis['company_type'],
                'Current_Price': analysis['financial_metrics'].get('current_price', 0),
                'Market_Cap': analysis['financial_metrics'].get('market_cap', 0),
                'Quality_Score': analysis['quality_score']['quality_score'],
                'Quality_Grade': analysis['quality_score']['quality_grade'],
                'PE_Ratio': analysis['financial_metrics'].get('pe_ratio'),
                'Revenue_Growth': analysis['financial_metrics'].get('revenue_growth'),
                'Debt_to_Equity': analysis['financial_metrics'].get('debt_to_equity'),
                'Recommendation': analysis['summary']['recommendation'],
                'Technical_Trend': analysis['technical_analysis'].get('trend', 'Unknown') if 'error' not in analysis['technical_analysis'] else 'Unknown',
                'Errors':analyzer.error_analysis
            }
            results.append(result)
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {e}")
            continue
    
    return pd.DataFrame(results)
def read_stock_data(file_path) -> pd.DataFrame:
    # Read NASDAQ data from CSV file
    df = pd.read_csv(file_path)
    return df

def save_analysis(stock_data, write_header=False):
    row_df = pd.DataFrame([stock_data], columns=['Symbol', 'DCF Price', 'Equity Value', 'Last Close'])
    row_df.to_csv('C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/stock_analysis.csv', 
                  index=False, mode='a', header=write_header)
    return

def save_analysis_to_csv(analyzer:StockAnalyzer, analysis, ticker, file_path='C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/stock_analysis.csv'):
    
    """Save analysis results to CSV file"""
    metrics = analysis.get('financial_metrics', {})
    quality = analysis.get('quality_score', {})
    summary = analysis.get('summary', {})
    dcf = analysis.get('dcf_analysis', {})
    
    row_data = {
        'Ticker': ticker,
        'Company_Type': analysis.get('company_type', ''),
        'Current_Price': f"${metrics.get('current_price', 0):,.2f}",
        'DCF_Value': f"${dcf.get('estimated_value', 0):,.2f}",
        'Market_Cap': f"${metrics.get('market_cap', 0):,.0f}",
        'PE_Ratio': metrics.get('pe_ratio', ''),
        'Revenue_Growth': metrics.get('revenue_growth', 0),
        'Quality_Score': quality.get('quality_score', 0),
        'Quality_Grade': quality.get('quality_grade', ''),
        'Recommendation': summary.get('recommendation', ''),
        'Confidence': summary.get('confidence', ''),
        'Errors': analyzer.error_analysis
    }
    debug_print(row_data.keys())
    df = pd.DataFrame([row_data])
    df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)


def read_stock_from_file():
    df = read_stock_data('C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/financial_analyst/resources/nasdaq.csv')
    print(len(df['Symbol']))
    count = 0
    stock_data = []
    config = FinanceConfig()
    config.default_cagr = 0.05
    config.max_cagr_threshold = 0.15
    config.use_default_ebitda_multiple = False
    debug_print(f'default settings\n{vars(config)}')
    #stock_analysis_df = pd.DataFrame(stock_data, columns=['Symbol', 'DCF Price', 'Equity Value', 'Last Close'])
    for symbol in df['Symbol']:
        try:
            count += 1
            if count == 20:
                break
            print(f'Processing stock {count}...', end='\r', flush=True)
            analyzer = StockAnalyzer(symbol)
            analysis = analyzer.comprehensive_analysis()
            save_analysis_to_csv(analyzer = analyzer, analysis = analysis, ticker = analyzer.ticker), analyzer.ticker
            
        except Exception as e:
            #print(f'Symbol: {symbol}, Error: {str(e)}')
            analysis = {'Ticker':symbol, 'Company_Type':'Error: {str(e)}'}
            save_analysis_to_csv(analyzer = analyzer, analysis = analysis, ticker = analyzer.ticker)
            continue
    return
# Example usage
if __name__ == "__main__":
    # Analyze individual stock
    os.environ['DEBUG'] = 'true'
    analyzer = StockAnalyzer("AACB")
    analysis = analyzer.comprehensive_analysis()
    debug_print(f"==========Analysis complete for {analyzer.ticker}==========")
    debug_print(json.dumps(analysis, indent=2, default=str))
    
    # read_stock_from_file()
    #save_analysis_to_csv(analysis, analyzer.ticker)
    
    
    # # Analyze multiple stocks for comparison
    # tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    # comparison_df = analyze_multiple_stocks(tickers)
    # print("\n=== Multi-Stock Comparison ===")
    # print(comparison_df.to_string(index=False))
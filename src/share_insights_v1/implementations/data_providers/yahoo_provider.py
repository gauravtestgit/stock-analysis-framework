import yfinance as yf
from typing import Dict, Any
from ...interfaces.data_provider import IDataProvider
from ...models.financial_metrics import FinancialMetrics

class YahooFinanceProvider(IDataProvider):
    """Yahoo Finance data provider implementation"""
    def get_revenue_trend(self, stock : yf.Ticker) -> Dict:
        """Get revenue trend from yfinance"""
    
        
    
        # Method 1: From income statement (quarterly and annual)
        quarterly_income = stock.quarterly_income_stmt
        annual_income = stock.income_stmt
        cashflow = stock.cashflow
        # Method 2: From financials (same as income_stmt)
        quarterly_financials = stock.quarterly_financials
        annual_financials = stock.financials
        
        # Extract revenue data
        revenue_data = {
            'quarterly_income_stmt': quarterly_income,
            'annual_income_stmt': annual_income,
            'quarterly_financial_stmt': quarterly_financials,
            'annual_financial_stmt': annual_financials,
            'cashflow': cashflow
        }
    
        # Annual revenue
        if not annual_income.empty and 'Total Revenue' in annual_income.index:
            annual_revenue = annual_income.loc['Total Revenue'].dropna()
            revenue_data['annual_revenue'] = annual_revenue.to_dict()
            
            # Calculate growth rates
            revenue_values = annual_revenue.values
            if len(revenue_values) >= 2:
                recent_growth = (revenue_values[0] - revenue_values[1]) / revenue_values[1] * 100
                revenue_data['recent_annual_growth'] = recent_growth
        
        # Quarterly revenue
        if not quarterly_income.empty and 'Total Revenue' in quarterly_income.index:
            quarterly_revenue = quarterly_income.loc['Total Revenue'].dropna()
            revenue_data['quarterly_revenue'] = quarterly_revenue.to_dict()
            
            # Calculate QoQ growth
            revenue_values = quarterly_revenue.values
            if len(revenue_values) >= 2:
                qoq_growth = (revenue_values[0] - revenue_values[1]) / revenue_values[1] * 100
                revenue_data['recent_quarterly_growth'] = qoq_growth
        
        # Method 3: From info (current metrics)
        info = stock.info
        revenue_data['current_revenue'] = info.get('totalRevenue', 0)
        revenue_data['revenue_growth'] = info.get('revenueGrowth', 0)
        revenue_data['quarterly_revenue_growth'] = info.get('quarterlyRevenueGrowth', 0)
        
        return revenue_data
    
    def get_financial_metrics(self, ticker: str) -> Dict[str, Any]:
        """Get financial metrics from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            revenue_data = self.get_revenue_trend(stock)
            info = stock.info
            cashflow = stock.cashflow
            
            fcf = 0
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0:
                    fcf = fcf_data.iloc[0]

            return {
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'fund_family': info.get('fundFamily', ''),
                'category': info.get('category', ''),
                'quote_type': info.get('quoteType', ''),
                'long_name': info.get('longName', ''),
                'enterprise_value': info.get('enterpriseValue', 0),
                'total_revenue': info.get('totalRevenue', 0),
                'net_income': info.get('netIncomeToCommon', 0),
                'current_revenue': f"${revenue_data.get('current_revenue'):,.2f}",
                'yearly_revenue_growth': revenue_data.get('revenue_growth'),
                'quarterly_revenue_growth': revenue_data.get('quarterly_revenue_growth'),
                'calculated_annual_growth': revenue_data.get('recent_annual_growth', 0),
                'calculated_quarterly_growth': revenue_data.get('recent_quarterly_growth', 0),
                # 'revenue_data_statements': revenue_data,
                'free_cash_flow': fcf,
                'total_debt': info.get('totalDebt', 0) or 0,
                'total_cash': info.get('totalCash', 0) or 0,
                'shares_outstanding': info.get('sharesOutstanding', 0),
                'current_price': info.get('currentPrice', 0),
                'beta': info.get('beta', 1.0),
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),
                'peg_ratio': info.get('pegRatio'),
                'roe': info.get('returnOnEquity'),
                'roa': info.get('returnOnAssets'),
                'debt_to_equity': info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else 0,
                'current_ratio': info.get('currentRatio'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                'dividend_yield': info.get('dividendYield'),
                'payout_ratio': info.get('payoutRatio'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_price_data(self, ticker: str) -> Dict[str, Any]:
        """Get price and technical data"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            return {
                'price_history': hist,
                'current_price': hist['Close'].iloc[-1] if not hist.empty else None,
                'volume': hist['Volume'].iloc[-1] if not hist.empty else None
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_professional_analyst_data(self, ticker: str) -> Dict:
        """Fetch analyst data from multiple sources"""
        data = {}
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Price targets
            data['target_price'] = info.get('targetMeanPrice', 0)
            data['target_high'] = info.get('targetHighPrice', 0)
            data['target_low'] = info.get('targetLowPrice', 0)
            
            # Recommendations
            data['recommendation'] = info.get('recommendationMean')
            data['recommendation_key'] = info.get('recommendationKey')
            
            # Estimates
            data['forward_eps'] = info.get('forwardEps', 0)
            data['eps_current_year'] = info.get('trailingEps', 0)
            
            # Growth estimates
            data['earnings_growth'] = info.get('earningsGrowth', 0)
            data['revenue_growth'] = info.get('revenueGrowth', 0)
            
            # Analyst count
            data['analyst_count'] = info.get('numberOfAnalystOpinions', 0)       
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            data = {}
        
        return data
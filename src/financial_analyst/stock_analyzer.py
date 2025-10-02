import yfinance as yf
import pandas as pd
import pandas_ta as pd_ta
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import warnings
warnings.filterwarnings('ignore')
from . import dcf_yf
from .config import FinanceConfig
import os
from ..util.debug_printer import debug_print
import json
from datetime import datetime, timedelta
from ..professional_analyst_integration.analyst_integration import AnalystDataProvider as adp

class CompanyType(Enum):
    MATURE_PROFITABLE = "mature_profitable"
    GROWTH_PROFITABLE = "growth_profitable"
    CYCLICAL = "cyclical"
    TURNAROUND = "turnaround"
    STARTUP_LOSS_MAKING = "startup_loss_making"
    REIT = "reit"
    FINANCIAL = "financial"
    COMMODITY = "commodity"
    ETF = "etf"

class StockAnalyzer:
    def __init__(self, ticker: str, config : Optional['FinanceConfig']):
        self.ticker = ticker.upper()
        self.stock = yf.Ticker(ticker)
        self.info = self.stock.info
        self.company_type = None
        self.error_analysis = []
        self.metrics = self.get_financial_metrics()
        self.config = config if config is not None else FinanceConfig()
        
        # Check if stock is delisted/invalid
        if not self.info or self.info.get('regularMarketPrice') is None:
            self.error_analysis.append(f"Stock {self.ticker} appears to be delisted or invalid")
        
    def classify_company(self) -> CompanyType:
        """Classify company type to determine appropriate valuation method"""
        try:
            market_cap = self.info.get('marketCap', 0)
            sector = self.info.get('sector', '')
            industry = self.info.get('industry', '')
            
            # Check for ETFs first
            fund_family = self.info.get('fundFamily', '')
            category = self.info.get('category', '')
            quote_type = self.info.get('quoteType', '')
            long_name = self.info.get('longName', '')
            
            # Enhanced ETF Detection
            etf_indicators = [
                quote_type == 'ETF',
                'ETF' in long_name.upper(),
                'FUND' in long_name.upper(),
                'TRUST' in long_name.upper(),
                bool(fund_family),
                bool(category),
                self.ticker.endswith('ETF'),
                # Common ETF tickers
                self.ticker in ['QQQ', 'SPY', 'IWM', 'VTI', 'VOO', 'SLV', 'GLD', 'TLT', 'EFA', 'EEM'],
                # ETF naming patterns
                any(pattern in self.ticker for pattern in ['SPDR', 'iShares', 'Vanguard']),
                # Check if total revenue is 0 (typical for ETFs)
                self.info.get('totalRevenue', 1) == 0
            ]
            
            if any(etf_indicators):
                return CompanyType.ETF
            
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

    def get_revenue_trend(self):
        """Get revenue trend from yfinance"""
    
        stock = self.stock
    
        # Method 1: From income statement (quarterly and annual)
        quarterly_income = stock.quarterly_income_stmt
        annual_income = stock.income_stmt
    
        # Method 2: From financials (same as income_stmt)
        quarterly_financials = stock.quarterly_financials
        annual_financials = stock.financials
        
        # Extract revenue data
        revenue_data = {}
    
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

    def get_financial_metrics(self) -> Dict:
        """Extract key financial metrics for analysis"""
        try:
            revenue_data = self.get_revenue_trend()
            metrics = {
                'market_cap': self.info.get('marketCap', 0),
                'enterprise_value': self.info.get('enterpriseValue', 0),
                'total_revenue': self.info.get('totalRevenue', 0),
                'net_income': self.info.get('netIncomeToCommon', 0),
                'current_revenue': f"${revenue_data.get('current_revenue'):,.2f}",
                'yearly_revenue_growth': revenue_data.get('revenue_growth'),
                'quarterly_revenue_growth': revenue_data.get('quarterly_revenue_growth'),
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
            debug_print(f"==========Financial Metrics for {self.ticker}=========")
            debug_print(json.dumps(metrics, indent=2, default=str))
            return metrics
        except Exception as e:
            self.error_analysis.append(f"get_financial_metrics():{str(e)}")
            print(f"Error getting financial metrics for {self.ticker}: {e}")
            
            return {}

    def dcf_analysis(self) -> Dict:
        """DCF analysis for mature/stable companies"""
        
        
        
        # This would integrate your existing DCF model
        try:
            
            sector = self.info.get('sector', '')
            industry = self.info.get('industry', '')
            quality_grade = self.quality_score().get('quality_grade', 'C')
            
            params = self.config.get_adjusted_parameters(sector = sector, industry=industry,
                                                         company_type=self.company_type, quality_grade=quality_grade)

            tmp_config = FinanceConfig()
            tmp_config.use_default_ebitda_multiple = True
            tmp_config.default_ev_ebitda_multiple = params.get('ev_ebitda_multiple', tmp_config.default_ev_ebitda_multiple)
            tmp_config.max_cagr_threshold = params.get('max_cagr', tmp_config.max_cagr_threshold)
            tmp_config.default_terminal_growth = params.get('terminal_growth', tmp_config.default_terminal_growth)            

            share_price, equity_value = dcf_yf.get_share_price(ticker_symbol=self.ticker, config=tmp_config)
            current_price = self.info.get('currentPrice', 0)

            if current_price > 0:
                upside_downside = ((share_price - current_price) / current_price) * 100
            
            # Apply any company-type specific discounts
            valuation_discount = self.config.company_type_adjustments.get(
                self.company_type, {}
            ).get('valuation_discount', 0.0)
            
            if valuation_discount > 0:
                share_price *= (1 - valuation_discount)
                upside_downside = ((share_price - current_price) / current_price) * 100

            return {
                'method': 'DCF Analysis',
                'applicable': True,
                'predicted_price': share_price,  # Would call your DCF function here
                'current_price': current_price,
                'upside_downside_pct': upside_downside,
                'total_equity_value': equity_value,
                'confidence': 'High' if self.company_type == CompanyType.MATURE_PROFITABLE else 'Medium',
                'valuation': 'Undervalued' if upside_downside > 20 else 'Overvalued' if upside_downside < -20 else 'Fair Value',
                'parameters_used': {
                    'max_cagr': f"{params['max_cagr']:.1%}",
                    'terminal_growth': f"{params['terminal_growth']:.1%}",
                    'sector': sector,
                    'industry': industry,
                    'quality_adjustment': quality_grade,
                    'valuation_discount': f"{valuation_discount:.1%}" if valuation_discount > 0 else None
                }
            }
        except Exception as e:
            self.error_analysis.append(f"dcf_analysis():{str(e)}")
            return{}

    def comparable_company_analysis(self) -> Dict:
        """Compare valuation multiples to industry peers"""
        try:
            total_revenue = self.info.get('totalRevenue', 0)
            net_income = self.info.get('netIncomeToCommon', 0)
            # book_value = self.info.get('totalStockholderEquity', 0)
            shares_outstanding = self.info.get('sharesOutstanding', 0)
            sector = self.info.get('sector', '')
            industry = self.info.get('industry', '')
            quality_grade = self.quality_score().get('quality_grade', 'C')
            # Get industry-specific multiples directly from config
            params = self.config.get_adjusted_parameters(
            sector, industry, self.company_type, quality_grade
            )

            # Extract target multiples from config parameters
            sector_multiples = {
                'pe': params.get('pe_multiple', 18),
                'ps': params.get('ps_multiple', 2.5),
                'pb': params.get('pb_multiple', 12),
                'ev_ebitda': params.get('ev_ebitda_multiple', 12)
            }

            

            # Industry average multiples (simplified - in practice, you'd get from database)
            # industry_multiples = {
            #     'Technology': {'pe': 25, 'ps': 6, 'ev_ebitda': 18, 'pb':3.5},
            #     'Healthcare': {'pe': 22, 'ps': 4, 'ev_ebitda': 15, 'pb':2.8},
            #     'Consumer Cyclical': {'pe': 18, 'ps': 1.5, 'ev_ebitda': 12, 'pb':2.0},
            #     'Financial Services': {'pe': 12, 'pb': 1.2, 'ev_ebitda': 10, 'pb':1.2},
            #     'Energy': {'pe': 15, 'ps': 1.0, 'ev_ebitda': 8, 'pb':1.5},
            #     'Utilities': {'pe': 16, 'ps': 2, 'ev_ebitda': 10, 'pb':1.4},
            #     'Default': {'pe': 18, 'ps': 2.5, 'ev_ebitda': 12, 'pb':2.0}
            # }
            
            # sector_multiples = industry_multiples.get(sector, industry_multiples['Default'])
            
            metrics = self.metrics
            
            # Calculate implied values based on multiples
            implied_values = {}
            
            if metrics['pe_ratio'] and sector_multiples.get('pe'):
                eps = metrics['net_income'] / metrics['shares_outstanding'] if metrics['shares_outstanding'] > 0 else 0
                implied_values['pe_based'] = eps * sector_multiples['pe']
            
            if metrics['ps_ratio'] and sector_multiples.get('ps'):
                sales_per_share = metrics['total_revenue'] / metrics['shares_outstanding'] if metrics['shares_outstanding'] > 0 else 0
                implied_values['ps_based'] = sales_per_share * sector_multiples['ps']

            # if metrics['pb_ratio'] and sector_multiples.get('pb'):
            #     book_per_share = metrics['book_value'] / metrics['shares_outstanding'] if metrics['shares_outstanding'] > 0 else 0
            #     implied_values['pe_based'] = book_per_share * sector_multiples['pb']
            
            predicted_price = np.average(list(implied_values.values())) if implied_values else None

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
                'predicted_price' : predicted_price,
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
            price_targets = {}
            predicted_price = current_price
            ma_trend = ''
            
            if ma_200 is not None and ma_50 is not None:
                # Full trend analysis with all 3 MAs
                if current_price > ma_50 > ma_200:
                    ma_trend = 'Strong Uptrend'
                    price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    predicted_price = price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_50 < ma_200:
                    ma_trend = 'Strong Downtrend'
                    price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    predicted_price = price_targets['medium_term'] = max(ma_200, current_price * (1 - volatility * 0.5))
                elif current_price > ma_50:
                    ma_trend = 'Uptrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_50:
                    ma_trend = 'Downtrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    price_targets['medium_term'] = max(ma_50, current_price * (1 - volatility * 0.5))
                else:
                    ma_trend = 'Sideways'
            elif ma_50 is not None:
                # Simple trend analysis with just 50-day MA
                if current_price > ma_50:
                    ma_trend = 'Short-term Uptrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_50:
                    ma_trend = 'Short-term Downtrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    price_targets['medium_term'] = max(ma_50, current_price * (1 - volatility * 0.5))
                else:
                    ma_trend = 'Sideways'
            elif ma_20 is not None:
                if current_price > ma_20:
                    ma_trend = 'Near-term Uptrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 + volatility * 0.5)  # 6-month target
                    price_targets['medium_term'] = current_price * (1 + volatility)  # 12-month target
                elif current_price < ma_20:
                    ma_trend = 'Near-term Downtrend'
                    predicted_price = price_targets['short_term'] = current_price * (1 - volatility * 0.3)
                    price_targets['medium_term'] = max(ma_20, current_price * (1 - volatility * 0.5))
                else:
                    ma_trend = 'Sideways'
            else:
                ma_trend = 'Insufficient Moving Averages Data'

            
            if current_price < high_52w * 0.8:  # More than 20% below high
                    price_targets['breakout_target'] = high_52w * 1.05  # 5% above resistance
            if current_price > low_52w * 1.2:  # More than 20% above low
                    price_targets['support_level'] = low_52w * 0.95  # 5% below support

            
            #Calculate RSI
            df = self.stock.history(period="1y")
            df['rsi'] = pd_ta.rsi(df['Close'],length=14)
            debug_print(df['rsi'][-1])
            rsi_14 = df['rsi'][-1] or None
                
            return {
                'method': 'Technical Analysis',
                'current_price': current_price,
                'predicted_price' : predicted_price,
                'price_targets' : price_targets,
                'ma_20': ma_20,
                'ma_50': ma_50,
                'ma_200': ma_200,
                'trend': ma_trend,
                'volatility_annual': volatility,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'distance_from_high': (current_price - high_52w) / high_52w,
                'distance_from_low': (current_price - low_52w) / low_52w,
                'volume_trend': f"Average Daily Volume:{avg_volume}, Trend: " + ('Above Average' if recent_volume > avg_volume * 1.2 else 'Below Average' if recent_volume < avg_volume * 0.8 else 'Normal'),
                'rsi_14' : rsi_14
            }
            
        except Exception as e:
            self.error_analysis.append(f"technical_analysis():{str(e)}")
            return {'error': f"Technical analysis failed: {e}"}

    def startup_analysis(self) -> Dict:
        """Specialized analysis for loss-making startups with enhanced risk assessment"""
        try:
            metrics = self.metrics
            sector = self.info.get('sector', '')
            industry = self.info.get('industry', '')
            
            # Enhanced cash runway analysis
            cashflow = self.stock.cashflow
            burn_rate = 0
            runway_quarters = 0
            
            if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
                fcf_data = cashflow.loc['Free Cash Flow'].dropna()
                if len(fcf_data) > 0 and fcf_data.iloc[0] < 0:
                    burn_rate = abs(fcf_data.iloc[0]) / 4  # Quarterly burn
                    if metrics['total_cash'] > 0:
                        runway_quarters = metrics['total_cash'] / burn_rate
            
            # Enhanced revenue growth analysis
            income_stmt = self.stock.income_stmt
            revenue_growth_rates = []
            current_revenue = 0
            revenue_volatility = 0

            if not income_stmt.empty and 'Total Revenue' in income_stmt.index:
                revenue_data = income_stmt.loc['Total Revenue'].dropna()
                current_revenue = revenue_data.iloc[0]
                for i in range(1, min(len(revenue_data), 4)):
                    if revenue_data.iloc[i] > 0:
                        growth = (revenue_data.iloc[i-1] - revenue_data.iloc[i]) / revenue_data.iloc[i]
                        revenue_growth_rates.append(growth)
                
                # Calculate revenue volatility as risk factor
                if len(revenue_growth_rates) > 1:
                    revenue_volatility = np.std(revenue_growth_rates)
            
            runway_years = runway_quarters / 4 if runway_quarters > 0 else 0
            median_growth = np.median(revenue_growth_rates) if revenue_growth_rates else 0
            
            # Enhanced risk assessment
            risk_factors = []
            risk_score = 0  # 0-100 scale
            
            # Cash runway risks
            if runway_years < 0.5:
                risk_factors.append("CRITICAL: Less than 6 months cash runway")
                risk_score += 40
            elif runway_years < 1:
                risk_factors.append("CRITICAL: Less than 1 year cash runway")
                risk_score += 30
            elif runway_years < 2:
                risk_factors.append("HIGH: Less than 2 years cash runway")
                risk_score += 20
            elif runway_years < 3:
                risk_factors.append("MODERATE: Less than 3 years cash runway")
                risk_score += 10
            
            # Growth quality risks
            if median_growth < 0:
                risk_factors.append("CRITICAL: Declining revenue")
                risk_score += 25
            elif median_growth < 0.10:
                risk_factors.append("HIGH: Revenue growth below 10%")
                risk_score += 20
            elif median_growth < 0.20:
                risk_factors.append("MODERATE: Revenue growth below 20% startup threshold")
                risk_score += 10
            
            # Revenue volatility risk
            if revenue_volatility > 0.5:
                risk_factors.append("HIGH: Highly volatile revenue pattern")
                risk_score += 15
            elif revenue_volatility > 0.3:
                risk_factors.append("MODERATE: Volatile revenue pattern")
                risk_score += 10
            
            # Data quality risks
            if len(revenue_growth_rates) < 2:
                risk_factors.append("HIGH: Insufficient revenue history")
                risk_score += 15
            
            # Sector-specific risks
            high_risk_sectors = ['Biotechnology', 'Energy', 'Materials']
            if sector in high_risk_sectors:
                risk_factors.append(f"SECTOR RISK: {sector} has high regulatory/commodity risks")
                risk_score += 10
            
            # Get startup-specific parameters from config
            startup_params = self.config.company_type_adjustments.get(
                CompanyType.STARTUP_LOSS_MAKING, {}
            )
            base_multiple = startup_params.get('revenue_multiple_base', 2.0)
            growth_premium = startup_params.get('growth_multiple_premium', 1.5)
            startup_risk_premium = startup_params.get('risk_premium', 0.05)
            
            # Enhanced revenue multiple calculation using config
            growth_multiple = self.config.get_startup_revenue_multiple(median_growth, sector)
            
            # Apply risk adjustments to multiple
            risk_adjustment = 1.0
            if risk_score > 60:
                risk_adjustment = 0.5  # Severe risk discount
            elif risk_score > 40:
                risk_adjustment = 0.7  # High risk discount
            elif risk_score > 20:
                risk_adjustment = 0.85  # Moderate risk discount
            
            adjusted_multiple = growth_multiple * risk_adjustment
            
            # Stage-based differentiation
            stage = "Unknown"
            stage_multiple = 1.0
            
            if current_revenue < 1e6:  # <$1M revenue
                stage = "Pre-Revenue/Seed"
                stage_multiple = 0.5
            elif current_revenue < 10e6:  # <$10M revenue
                stage = "Early Stage"
                stage_multiple = 0.7
            elif current_revenue < 100e6:  # <$100M revenue
                stage = "Growth Stage"
                stage_multiple = 1.0
            else:
                stage = "Late Stage"
                stage_multiple = 1.2
            
            final_multiple = adjusted_multiple * stage_multiple
            
            # Growth assessment with enhanced criteria
            growth_quality = "Unknown"
            if revenue_growth_rates:
                if median_growth > 1.0:  # >100% growth
                    growth_quality = "Hypergrowth (>100%)"
                elif median_growth > 0.50:
                    growth_quality = "Exceptional (50-100%)"
                elif median_growth > 0.30:
                    growth_quality = "Strong (30-50%)"
                elif median_growth > 0.15:
                    growth_quality = "Moderate (15-30%)"
                elif median_growth > 0:
                    growth_quality = "Weak (<15%)"
                else:
                    growth_quality = "Declining"
            
            # Conservative growth projections with risk adjustment
            growth_decay = 0.8 if median_growth > 0.5 else 0.9  # High growth decays faster
            projected_revenue_1yr = current_revenue * (1 + min(median_growth * 0.8, 0.40))  # More conservative
            projected_revenue_2yr = projected_revenue_1yr * (1 + min(median_growth * growth_decay * 0.6, 0.30))
            
            # Calculate enterprise values
            current_ev = current_revenue * final_multiple
            forward_ev_1yr = projected_revenue_1yr * final_multiple
            forward_ev_2yr = projected_revenue_2yr * final_multiple
            
            # Convert to equity value
            total_debt = metrics['total_debt']
            total_cash = metrics['total_cash']
            net_debt = total_debt - total_cash
            shares_outstanding = self.info.get('sharesOutstanding', 0)
            
            current_price_est = 0
            forward_price_1yr = 0
            forward_price_2yr = 0
            
            if shares_outstanding > 0:
                current_price_est = max(0, (current_ev - net_debt) / shares_outstanding)
                forward_price_1yr = max(0, (forward_ev_1yr - net_debt) / shares_outstanding)
                forward_price_2yr = max(0, (forward_ev_2yr - net_debt) / shares_outstanding)
            
            # Enhanced recommendation logic
            def get_startup_recommendation():
                if risk_score > 70:
                    return "AVOID - Critical risk factors"
                elif runway_years < 0.5:
                    return "AVOID - Imminent bankruptcy risk"
                elif runway_years < 1 and median_growth < 0.15:
                    return "AVOID - Insufficient runway with weak growth"
                elif runway_years > 4 and median_growth > 0.40 and risk_score < 30:
                    return "SPECULATIVE BUY - Strong fundamentals"
                elif runway_years > 2 and median_growth > 0.25 and risk_score < 40:
                    return "HOLD/WATCH - Adequate metrics, monitor closely"
                elif median_growth > 0.75 and runway_years > 1:
                    return "HIGH RISK/HIGH REWARD - Exceptional growth"
                elif risk_score > 50:
                    return "AVOID - High risk without adequate compensation"
                else:
                    return "MONITOR - Mixed signals, wait for clarity"

            return {
                'method': 'Enhanced Startup Analysis',
                'stage': stage,
                'cash_runway_years': runway_years,
                'predicted_price': current_price_est,
                'price_1y': forward_price_1yr,
                'price_2y': forward_price_2yr,
                'quarterly_burn_rate': burn_rate,
                'revenue_growth_rates': [f"{rate:.1%}" for rate in revenue_growth_rates],
                'median_growth': f"{median_growth:.1%}",
                'revenue_volatility': f"{revenue_volatility:.1%}",
                'growth_quality': growth_quality,
                'risk_factors': risk_factors,
                'risk_score': risk_score,
                'recommendation': get_startup_recommendation(),
                'revenue_multiple_breakdown': {
                    'base_multiple': growth_multiple,
                    'risk_adjustment': risk_adjustment,
                    'stage_adjustment': stage_multiple,
                    'final_multiple': final_multiple
                },
                'current_revenue': current_revenue,
                'projected_revenue_1yr': projected_revenue_1yr,
                'projected_revenue_2yr': projected_revenue_2yr,
                'implied_value_estimate': current_revenue * final_multiple if current_revenue > 0 else 0,
                'confidence_level': 'Very Low - Speculative' if risk_score > 40 else 'Low - High Risk',
                'investment_type': 'Venture Capital Style - Total Loss Possible'
            }
            
        except Exception as e:
            self.error_analysis.append(f"startup_analysis():{str(e)}")
            return {'error': f"Startup analysis failed: {e}"}

    def quality_score(self) -> Dict:
        """Assess overall company quality"""
        metrics = self.metrics
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
                'quality_score': final_score,
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

    def get_analyst_data(self) -> Dict:
        analyst_data_provider = adp()
        analyst_data = adp.get_analyst_data(self=analyst_data_provider,ticker=self.ticker) or {}
        return analyst_data


    def comprehensive_analysis(self) -> Dict:
        """Run complete analysis based on company type"""
        print(f"\n=== Analyzing {self.ticker} ===")
        
        # Classify company
        self.company_type = self.classify_company()
        print(f"Company Type: {self.company_type.value}")
        
        # Get basic metrics
        metrics = self.metrics
        
        # Run appropriate analyses based on company type
        analyses = {
            'company_type': self.company_type.value,
            'financial_metrics': metrics,
            'quality_score': self.quality_score()
        }
        
        # Always get professional analsyt data
        analyses['professional_analysis'] = self.get_analyst_data()

        # Always run technical analysis
        analyses['technical_analysis'] = self.technical_analysis()
        
        # Run specific analyses based on company type
        if self.company_type == CompanyType.STARTUP_LOSS_MAKING:
            analyses['startup_analysis'] = self.startup_analysis()
        elif self.company_type in [CompanyType.MATURE_PROFITABLE, CompanyType.GROWTH_PROFITABLE]:
            analyses['dcf_analysis'] = self.dcf_analysis()
            analyses['comparable_analysis'] = self.comparable_company_analysis()
        elif self.company_type in [CompanyType.CYCLICAL, CompanyType.FINANCIAL]:
            analyses['comparable_analysis'] = self.comparable_company_analysis()
            # Could add commodity price correlation analysis here
        elif self.company_type == CompanyType.ETF:
            # ETFs only get technical analysis - no fundamental analysis needed
            pass
        else:
            analyses['dcf_analysis'] = self.dcf_analysis()
            analyses['comparable_analysis'] = self.comparable_company_analysis()
        
        # Generate summary recommendation
        try:
            # analyses['quality_score'] = self.quality_score()
            analyses['summary'] = self.generate_summary(analyses)
        except Exception as e:
            self.error_analysis.append(f"generate_summary():{str(e)}")
            analyses['summary'] = {'error': f"Summary generation failed: {e}"}
        
        return analyses
    
    def generate_summary(self, analyses: Dict) -> Dict:
        """Generate holistic investment summary combining all analysis methods"""
        
        # Extract key components
        quality = analyses['quality_score']['quality_grade']
        quality_score = analyses['quality_score']['quality_score']
        company_type = analyses['company_type']
        
        # Initialize recommendation components
        signals = {'bullish': [], 'bearish': [], 'neutral': []}
        overall_confidence = 'Medium'
        risk_factors = []
        opportunities = []
        
        # Process DCF Analysis (if available)
        dcf_signal = None
        if 'dcf_analysis' in analyses and 'error' not in analyses['dcf_analysis']:
            dcf = analyses['dcf_analysis']
            upside = dcf.get('upside_downside_pct', 0)
            
            if upside > 25:
                signals['bullish'].append(f"DCF shows {upside:.0f}% upside")
                dcf_signal = 'Strong Buy'
            elif upside > 10:
                signals['bullish'].append(f"DCF shows {upside:.0f}% upside") 
                dcf_signal = 'Buy'
            elif upside < -25:
                signals['bearish'].append(f"DCF shows {upside:.0f}% downside")
                dcf_signal = 'Strong Sell'
            elif upside < -10:
                signals['bearish'].append(f"DCF shows {upside:.0f}% downside")
                dcf_signal = 'Sell'
            else:
                signals['neutral'].append("DCF suggests fair valuation")
                dcf_signal = 'Hold'
        
        # Process Startup Analysis (if available)
        startup_signal = None
        if 'startup_analysis' in analyses and 'error' not in analyses['startup_analysis']:
            startup = analyses['startup_analysis']
            recommendation = startup.get('recommendation', '')
            
            if 'SPECULATIVE BUY' in recommendation or 'HIGH REWARD' in recommendation:
                signals['bullish'].append("Strong revenue growth with adequate runway")
                startup_signal = 'Speculative Buy'
                risk_factors.append("High volatility - total loss possible")
            elif 'AVOID' in recommendation:
                signals['bearish'].append("Critical cash runway or poor growth")
                startup_signal = 'Avoid'
                risk_factors.append("Bankruptcy risk")
            else:
                signals['neutral'].append("Mixed startup fundamentals")
                startup_signal = 'Monitor'
                
            # Add runway-specific risks
            runway = startup.get('cash_runway_years', 0)
            if runway < 1:
                risk_factors.append("Critical: <1 year cash runway")
            elif runway < 2:
                risk_factors.append("High risk: <2 years cash runway")
        
        # Process Technical Analysis
        technical_signal = None
        if 'technical_analysis' in analyses and 'error' not in analyses['technical_analysis']:
            tech = analyses['technical_analysis']
            trend = tech.get('trend', 'Unknown')
            
            if 'Strong Uptrend' in trend or 'Uptrend' in trend:
                signals['bullish'].append(f"Technical: {trend}")
                technical_signal = 'Buy'
            elif 'Strong Downtrend' in trend or 'Downtrend' in trend:
                signals['bearish'].append(f"Technical: {trend}")
                technical_signal = 'Sell'
            else:
                signals['neutral'].append(f"Technical: {trend}")
                technical_signal = 'Neutral'
            
            # Volume analysis
            volume_trend = tech.get('volume_trend', 'Normal')
            if volume_trend == 'Above Average' and 'Uptrend' in trend:
                signals['bullish'].append("Strong volume supporting uptrend")
            elif volume_trend == 'Above Average' and 'Downtrend' in trend:
                signals['bearish'].append("High volume selling pressure")
        
        # Process Comparable Analysis
        comparable_signal = None
        if 'comparable_analysis' in analyses and 'error' not in analyses['comparable_analysis']:
            comp = analyses['comparable_analysis']
            relative_val = comp.get('relative_valuation', 'Fair')
            
            if relative_val == 'Undervalued':
                signals['bullish'].append("Trading below peer multiples")
                comparable_signal = 'Buy'
            elif relative_val == 'Overvalued':
                signals['bearish'].append("Trading above peer multiples")
                comparable_signal = 'Sell'
            else:
                signals['neutral'].append("Fair valuation vs peers")
                comparable_signal = 'Hold'
        
        # Quality Assessment Impact
        if quality in ['A', 'B']:
            if quality == 'A':
                signals['bullish'].append("High quality company metrics")
                opportunities.append("Strong fundamentals support long-term growth")
            else:
                signals['bullish'].append("Good quality company metrics")
        elif quality == 'D':
            signals['bearish'].append("Poor quality metrics")
            risk_factors.append("Weak financial health")
        
        # Data Quality Impact
        data_quality = analyses['quality_score'].get('data_quality', 'Medium')
        if data_quality == 'Low':
            risk_factors.append("Limited financial data availability")
            overall_confidence = 'Low'
        
        # Synthesize Overall Recommendation
        bullish_count = len(signals['bullish'])
        bearish_count = len(signals['bearish'])
        
        # Company-type specific logic
        if company_type == 'startup_loss_making':
            if startup_signal == 'Speculative Buy' and technical_signal in ['Buy', 'Neutral']:
                overall_recommendation = 'SPECULATIVE BUY'
                overall_confidence = 'Low - High Risk'
            elif startup_signal == 'Avoid':
                overall_recommendation = 'AVOID'
                overall_confidence = 'High'
            else:
                overall_recommendation = 'MONITOR'
                overall_confidence = 'Low'
        
        elif company_type in ['mature_profitable', 'growth_profitable']:
            # Weight DCF more heavily for stable companies
            if dcf_signal in ['Strong Buy', 'Buy'] and bullish_count >= bearish_count:
                overall_recommendation = 'BUY'
                overall_confidence = 'High' if quality in ['A', 'B'] else 'Medium'
            elif dcf_signal in ['Strong Sell', 'Sell'] or bearish_count > bullish_count + 1:
                overall_recommendation = 'SELL'
                overall_confidence = 'Medium'
            else:
                overall_recommendation = 'HOLD'
                overall_confidence = 'Medium'
        
        else:  # cyclical, turnaround, etc.
            if bullish_count > bearish_count + 1 and quality in ['A', 'B']:
                overall_recommendation = 'BUY'
                overall_confidence = 'Medium'
            elif bearish_count > bullish_count + 1:
                overall_recommendation = 'SELL'
                overall_confidence = 'Medium'
            else:
                overall_recommendation = 'HOLD'
                overall_confidence = 'Low'
        
        # Risk level assessment
        risk_level = 'Low'
        if company_type == 'startup_loss_making':
            risk_level = 'Very High'
        elif len(risk_factors) >= 3:
            risk_level = 'High'
        elif len(risk_factors) >= 1:
            risk_level = 'Medium'
        
        # Investment thesis
        def generate_thesis():
            if company_type == 'startup_loss_making':
                return f"High-risk speculative play on revenue growth potential. {startup_signal or 'Monitor'} based on cash runway and growth metrics."
            elif company_type == 'mature_profitable':
                return f"Stable dividend-paying company. DCF suggests {dcf_signal or 'fair valuation'} with {quality} quality metrics."
            elif company_type == 'growth_profitable':
                return f"Growth company with {quality} fundamentals. Multiple analysis methods suggest {overall_recommendation.lower()}."
            elif company_type == 'etf':
                return f"Exchange-traded fund - technical analysis only. Current trend: {technical_signal or 'neutral'}. Suitable for diversification and sector exposure."
            else:
                return f"{company_type.replace('_', ' ').title()} company requiring careful timing. Current signals: {overall_recommendation.lower()}."
        
        return {
            'recommendation': overall_recommendation,
            'confidence': overall_confidence,
            'risk_level': risk_level,
            'signals': {
                'bullish': signals['bullish'],
                'bearish': signals['bearish'],
                'neutral': signals['neutral']
            },
            'individual_signals': {
                'dcf': dcf_signal,
                'startup': startup_signal, 
                'technical': technical_signal,
                'comparable': comparable_signal
            },
            'key_risks': risk_factors,
            'opportunities': opportunities,
            'investment_thesis': generate_thesis(),
            'data_quality': data_quality,
            'next_steps': self._generate_next_steps(overall_recommendation, company_type, risk_factors)
        }
    
    def _generate_next_steps(self, recommendation: str, company_type: str, risk_factors: List[str]) -> List[str]:
        """Generate actionable next steps based on recommendation"""
        steps = []
        
        if recommendation == 'BUY':
            steps.append("Consider position sizing based on risk tolerance")
            steps.append("Monitor quarterly earnings for confirmation of thesis")
            if company_type in ['mature_profitable', 'growth_profitable']:
                steps.append("Review management guidance and forward outlook")
        
        elif recommendation == 'SPECULATIVE BUY':
            steps.append("Limit position size to <2% of portfolio")
            steps.append("Monitor cash burn rate and runway quarterly") 
            steps.append("Set stop-loss at -50% to limit downside")
            steps.append("Track revenue growth sustainability")
        
        elif recommendation == 'SELL' or recommendation == 'AVOID':
            if 'Bankruptcy risk' in risk_factors:
                steps.append("Exit position immediately if held")
            steps.append("Monitor for fundamental changes before reconsidering")
            
        elif recommendation == 'HOLD':
            steps.append("Monitor for catalysts that could change thesis")
            steps.append("Review position at next earnings announcement")
        
        elif recommendation == 'MONITOR':
            steps.append("Wait for clearer fundamental signals")
            steps.append("Consider adding to watchlist for quarterly review")
        
        # Universal steps
        if 'Limited financial data' in str(risk_factors):
            steps.append("Seek additional data sources beyond yFinance")
        
        return steps

    def generate_summary2(self, analyses: Dict) -> Dict:
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
            analyzer = StockAnalyzer(ticker, None)
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

def save_analysis_to_csv(analyzer:StockAnalyzer, analysis, ticker, file_path='C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/src/resources/stock_analysis.csv'):
    
    """Save analysis results to CSV file"""
    metrics = analysis.get('financial_metrics', {})
    quality = analysis.get('quality_score', {})
    summary = analysis.get('summary', {})
    dcf = analysis.get('dcf_analysis', {})
    technical = analysis.get('technical_analysis', {})
    comparable = analysis.get('comparable_analysis', {})
    startup = analysis.get('startup_analysis', {})
    professional = analysis.get('professional_analysis', {})

    row_data = {
        'Ticker': ticker,
        'Sector': analyzer.info.get('sector', ''),
        'Industry': analyzer.info.get('industry', ''),
        'Company_Type': analysis.get('company_type', ''),
        'Current_Price': f"${metrics.get('current_price', 0):,.2f}",
        'DCF_Price': f"${dcf.get('predicted_price', 0) or 0:,.2f}",
        'Technical_Price' : f"${technical.get('predicted_price', 0) or 0:,.2f}",
        'Comparable_Price' : f"${comparable.get('predicted_price', 0) or 0:,.2f}",
        'Startup_Price' : f"${startup.get('predicted_price', 0) or 0:,.2f}",
        'Professional_Price' : f"${professional.get('target_price', 0) or 0:,.2f}",
        'Equity Value': f"${dcf.get('total_equity_value', 0):,.0f}",
        'RSI 14': technical.get('rsi_14', 'RSI_14 Unavailable'),
        'Current_Multiples' : comparable.get('current_multiples'),
        'Technical Trend on MA': technical.get('trend', 'Trend Unavailable'),
        'MA_20': technical.get('ma_20', 'MA20 Unavailable'),
        'MA_50': technical.get('ma_50', 'MA50 Unavailable'),
        'MA_200': technical.get('ma_200', 'MA200 Unavailable'),
        'Relative_Valuation': comparable.get('relative_valuation', 'N/A'),
        'Last_Close': f"${metrics.get('last_close', 0):,.2f}",
        'Market_Cap': f"${metrics.get('market_cap', 0):,.0f}",
        'PE_Ratio': metrics.get('pe_ratio', ''),
        'Revenue_Growth': metrics.get('revenue_growth', 0),
        'Quality_Score': quality.get('quality_score', 0),
        'Quality_Grade': quality.get('quality_grade', ''),
        'Growth_Quality': startup.get('growth_quality', ''),
        'Median_Growth' : startup.get('median_growth', 0),
        'Current_Revenue' : f"${startup.get('current_revenue',0):,.0f}",
        'Implied_Value_Estimate' : f"${startup.get('implied_value_estimate', 0):,.0f}",
        'Key_Risks': summary.get('key_risks', []),        
        'Recommendation': summary.get('recommendation', ''),
        'Professional_Recommendation' : professional.get('recommendation', ''),
        'Professional_Count' : professional.get('analyst_count', 0),
        'Confidence': summary.get('confidence', ''),
        'Signal-Bullish' : summary.get('signals', {}).get('bullish', []),
        'Signal-Bearish' : summary.get('signals', {}).get('bearish', []),
        'Signal-Neutral' : summary.get('signals', {}).get('neutral', []),
        'Signal-DCF' : summary.get('individual_signals', {}).get('dcf', ''),
        'Signal-Startup' : summary.get('individual_signals', {}).get('startup', ''),
        'Signal-Technical' : summary.get('individual_signals', {}).get('technical', ''),
        'Signal-Comparable' : summary.get('individual_signals', {}).get('comparable', ''),
        'Risk_Level': summary.get('risk_level', ''),
        'Investment_Thesis': summary.get('investment_thesis', ''),
        'Data_Quality': summary.get('data_quality', ''),
        'Next_Steps': summary.get('next_steps', []),
        'Errors': analyzer.error_analysis
    }
    debug_print(row_data.keys())
    df = pd.DataFrame([row_data])
    df.to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)


def read_stock_from_file(file_path : str):
    df = read_stock_data(file_path=file_path)
    print(len(df['Symbol']))
    total_stocks = len(df['Symbol'])
    count = 0
    stock_data = []
    config = FinanceConfig()
    config.default_cagr = 0.05
    config.max_cagr_threshold = 0.15
    config.use_default_ebitda_multiple = False
    debug_print(f'default settings\n{vars(config)}')
    #stock_analysis_df = pd.DataFrame(stock_data, columns=['Symbol', 'DCF Price', 'Equity Value', 'Last Close'])
    time_start = datetime.now()
    time_diff = 0
    time_remaining = 0
    time_per_stock = 0
    for symbol in df['Symbol']:
        try:
            
            count += 1
            
            if count >= 2:
                time_1 = datetime.now()
                time_diff = time_1 - time_start
                time_per_stock = time_diff / (count - 1)
                time_remaining = time_per_stock * (total_stocks - count)
            # if count == 200:
                #     break
            time_remaining = time_per_stock * (total_stocks - count)
            print(f'Processing stock {count}. Time remaining {time_remaining}', end='\r', flush=True)
            analyzer = StockAnalyzer(symbol, config)
            analysis = analyzer.comprehensive_analysis()
            save_analysis_to_csv(analyzer = analyzer, analysis = analysis, ticker = analyzer.ticker), analyzer.ticker
            
        except Exception as e:
            #print(f'Symbol: {symbol}, Error: {str(e)}')
            analysis = {'Ticker':symbol, 'Company_Type':'Error: {str(e)}'}
            save_analysis_to_csv(analyzer = analyzer, analysis = analysis, ticker = analyzer.ticker)
            continue
    return

def test_single(symbol: str):
    os.environ['DEBUG'] = 'true'
    config = FinanceConfig()
    analyzer = StockAnalyzer(symbol, None)
    analysis = analyzer.comprehensive_analysis()
    debug_print(f"==========Analysis complete for {analyzer.ticker}==========")
    debug_print(json.dumps(analysis, indent=2, default=str))
    debug_print(analysis.get('comparable_analysis', {}).get('implied_values'))
    save_analysis_to_csv(analyzer, analysis, analyzer.ticker)
    debug_print(f"===========Generic info for {analyzer.ticker}===========")
    debug_print(json.dumps(analyzer.info, indent=2, default=str))
# Example usage
if __name__ == "__main__":
    # Analyze individual stock
    import sys
    print (len(sys.argv))
    if len(sys.argv) == 2:
        test_single(sys.argv[1].strip())
    else:
        file_path = "C:/Users/x_gau/source/repos/agentic/langchain/tutorials/finance-app/src/resources/nyse.csv"
        read_stock_from_file(file_path=file_path)
    # Analyze from a list in a csv file
    
    
    
    
    
    # # Analyze multiple stocks for comparison
    # tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
    # comparison_df = analyze_multiple_stocks(tickers)
    # print("\n=== Multi-Stock Comparison ===")
    # print(comparison_df.to_string(index=False))
from typing import Dict, Any, List
import yfinance as yf
import pandas as pd
import numpy as np
from ...interfaces.analyzer import IAnalyzer
from ...models.company import CompanyType
from ...implementations.llm_providers.llm_manager import LLMManager

class RevenueStreamAnalyzer(IAnalyzer):
    """Analyzes revenue streams and estimates earnings based on market indicators"""
    
    def __init__(self):
        self.llm_manager = LLMManager()
        
        # Market indicator mappings by sector
        self.sector_indicators = {
            'Technology': ['QQQ', 'XLK', 'SOXX'],  # Tech ETFs
            'Healthcare': ['XLV', 'IBB', 'XBI'],   # Healthcare ETFs
            'Financial Services': ['XLF', 'KBE', 'KRE'],  # Financial ETFs
            'Consumer Cyclical': ['XLY', 'RTH', 'XRT'],   # Consumer ETFs
            'Consumer Defensive': ['XLP', 'VDC'],          # Staples ETFs
            'Energy': ['XLE', 'OIH', 'XOP'],              # Energy ETFs
            'Industrials': ['XLI', 'IYT'],                # Industrial ETFs
            'Real Estate': ['XLRE', 'VNQ', 'IYR'],        # REIT ETFs
            'Utilities': ['XLU', 'VPU'],                  # Utility ETFs
            'Materials': ['XLB', 'XME'],                  # Materials ETFs
            'Communication Services': ['XLC', 'VOX']       # Telecom ETFs
        }
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform revenue stream analysis"""
        try:
            financial_metrics = data.get('financial_metrics', {})
            
            # Extract basic company info
            sector = financial_metrics.get('sector', 'Unknown')
            industry = financial_metrics.get('industry', 'Unknown')
            business_summary = financial_metrics.get('longBusinessSummary', '')
            
            # Get revenue breakdown
            revenue_streams = self._identify_revenue_streams(ticker, financial_metrics, business_summary)
            
            # Analyze market correlations
            market_analysis = self._analyze_market_correlations(ticker, sector)
            
            # Estimate earnings based on market trends
            earnings_forecast = self._estimate_market_based_earnings(ticker, financial_metrics, market_analysis)
            
            # Generate LLM-powered insights
            llm_insights = self._generate_revenue_insights(ticker, revenue_streams, market_analysis, financial_metrics)
            
            return {
                'method': 'Revenue Stream Analysis',
                'revenue_streams': revenue_streams,
                'market_analysis': market_analysis,
                'earnings_forecast': earnings_forecast,
                'revenue_insights': llm_insights,
                'sector': sector,
                'industry': industry,
                'recommendation': self._generate_recommendation(earnings_forecast, market_analysis)
            }
            
        except Exception as e:
            return {'error': f'Revenue stream analysis failed: {str(e)}'}
    
    def _identify_revenue_streams(self, ticker: str, financial_metrics: Dict, business_summary: str) -> Dict[str, Any]:
        """Identify and categorize revenue streams"""
        try:
            stock = yf.Ticker(ticker)
            
            # Get segment data if available
            segments = {}
            try:
                # Try to get segment revenue from financials
                financials = stock.financials
                if not financials.empty and 'Total Revenue' in financials.index:
                    total_revenue = financials.loc['Total Revenue'].iloc[0]
                    segments['total_revenue'] = float(total_revenue) if pd.notna(total_revenue) else 0
            except:
                segments['total_revenue'] = financial_metrics.get('totalRevenue', 0)
            
            # Classify revenue model based on business summary and metrics
            revenue_model = self._classify_revenue_model(business_summary, financial_metrics)
            
            # Estimate revenue composition
            revenue_composition = self._estimate_revenue_composition(revenue_model, financial_metrics)
            
            return {
                'segments': segments,
                'revenue_model': revenue_model,
                'composition': revenue_composition,
                'total_revenue_ttm': segments.get('total_revenue', 0),
                'revenue_growth_yoy': financial_metrics.get('revenueGrowth', 0) * 100 if financial_metrics.get('revenueGrowth') else 0
            }
            
        except Exception as e:
            return {'error': f'Revenue stream identification failed: {str(e)}'}
    
    def _classify_revenue_model(self, business_summary: str, financial_metrics: Dict) -> str:
        """Classify the company's revenue model"""
        summary_lower = business_summary.lower()
        
        # SaaS/Subscription indicators
        if any(term in summary_lower for term in ['software', 'saas', 'subscription', 'cloud', 'platform']):
            return 'SaaS/Subscription'
        
        # E-commerce/Retail
        elif any(term in summary_lower for term in ['retail', 'e-commerce', 'marketplace', 'store']):
            return 'Retail/E-commerce'
        
        # Manufacturing
        elif any(term in summary_lower for term in ['manufactur', 'produc', 'industrial']):
            return 'Manufacturing'
        
        # Financial Services
        elif any(term in summary_lower for term in ['bank', 'financial', 'insurance', 'credit']):
            return 'Financial Services'
        
        # Healthcare/Pharma
        elif any(term in summary_lower for term in ['healthcare', 'pharmaceutical', 'medical', 'drug']):
            return 'Healthcare/Pharma'
        
        # Energy/Utilities
        elif any(term in summary_lower for term in ['energy', 'oil', 'gas', 'utility', 'power']):
            return 'Energy/Utilities'
        
        # Media/Advertising
        elif any(term in summary_lower for term in ['media', 'advertising', 'content', 'entertainment']):
            return 'Media/Advertising'
        
        else:
            return 'Diversified/Other'
    
    def _estimate_revenue_composition(self, revenue_model: str, financial_metrics: Dict) -> Dict[str, float]:
        """Estimate revenue composition based on model type"""
        # Default composition estimates by revenue model
        compositions = {
            'SaaS/Subscription': {
                'recurring_revenue': 0.8,
                'one_time_revenue': 0.15,
                'services_revenue': 0.05
            },
            'Retail/E-commerce': {
                'product_sales': 0.85,
                'marketplace_fees': 0.10,
                'advertising_revenue': 0.05
            },
            'Manufacturing': {
                'product_sales': 0.90,
                'services_revenue': 0.08,
                'licensing_revenue': 0.02
            },
            'Financial Services': {
                'interest_income': 0.60,
                'fee_income': 0.30,
                'trading_revenue': 0.10
            },
            'Healthcare/Pharma': {
                'product_sales': 0.75,
                'licensing_revenue': 0.15,
                'services_revenue': 0.10
            },
            'Energy/Utilities': {
                'commodity_sales': 0.80,
                'regulated_revenue': 0.15,
                'services_revenue': 0.05
            },
            'Media/Advertising': {
                'advertising_revenue': 0.70,
                'subscription_revenue': 0.20,
                'content_licensing': 0.10
            },
            'Diversified/Other': {
                'primary_revenue': 0.70,
                'secondary_revenue': 0.20,
                'other_revenue': 0.10
            }
        }
        
        return compositions.get(revenue_model, compositions['Diversified/Other'])
    
    def _analyze_market_correlations(self, ticker: str, sector: str) -> Dict[str, Any]:
        """Analyze correlations with market indicators"""
        try:
            # Get sector ETFs
            sector_etfs = self.sector_indicators.get(sector, ['SPY'])  # Default to S&P 500
            
            # Get price data for correlation analysis
            stock = yf.Ticker(ticker)
            stock_data = stock.history(period='1y')['Close']
            
            correlations = {}
            for etf in sector_etfs[:2]:  # Limit to 2 ETFs to avoid rate limits
                try:
                    etf_data = yf.Ticker(etf).history(period='1y')['Close']
                    if len(stock_data) > 0 and len(etf_data) > 0:
                        # Align data and calculate correlation
                        aligned_data = pd.concat([stock_data, etf_data], axis=1, join='inner')
                        if len(aligned_data) > 10:  # Need sufficient data points
                            correlation = aligned_data.iloc[:, 0].corr(aligned_data.iloc[:, 1])
                            correlations[etf] = float(correlation) if pd.notna(correlation) else 0
                except:
                    correlations[etf] = 0
            
            # Calculate average correlation
            avg_correlation = np.mean(list(correlations.values())) if correlations else 0
            
            return {
                'sector_correlations': correlations,
                'average_correlation': avg_correlation,
                'market_sensitivity': 'High' if avg_correlation > 0.7 else 'Medium' if avg_correlation > 0.4 else 'Low'
            }
            
        except Exception as e:
            return {'error': f'Market correlation analysis failed: {str(e)}'}
    
    def _estimate_market_based_earnings(self, ticker: str, financial_metrics: Dict, market_analysis: Dict) -> Dict[str, Any]:
        """Estimate earnings based on market trends"""
        try:
            # Get current financial metrics
            current_revenue = financial_metrics.get('totalRevenue', 0)
            current_earnings = financial_metrics.get('netIncomeToCommon', 0)
            revenue_growth = financial_metrics.get('revenueGrowth', 0)
            
            # Market sensitivity factor
            market_sensitivity = market_analysis.get('average_correlation', 0.5)
            
            # Base growth estimate (conservative)
            base_growth = revenue_growth if revenue_growth and revenue_growth > -0.5 else 0.05  # 5% default
            
            # Adjust growth based on market correlation
            market_adjusted_growth = base_growth * (1 + market_sensitivity * 0.2)  # Up to 20% adjustment
            
            # Estimate next year revenue and earnings
            estimated_revenue_1y = current_revenue * (1 + market_adjusted_growth)
            estimated_earnings_1y = current_earnings * (1 + market_adjusted_growth * 1.2)  # Earnings leverage
            
            # Calculate confidence based on data quality
            confidence = min(0.9, 0.3 + market_sensitivity * 0.6)  # 30-90% confidence range
            
            return {
                'current_revenue': current_revenue,
                'current_earnings': current_earnings,
                'estimated_revenue_1y': estimated_revenue_1y,
                'estimated_earnings_1y': estimated_earnings_1y,
                'growth_rate_estimate': market_adjusted_growth * 100,
                'confidence_level': confidence,
                'methodology': 'Market-correlation adjusted growth projection'
            }
            
        except Exception as e:
            return {'error': f'Earnings estimation failed: {str(e)}'}
    
    def _generate_revenue_insights(self, ticker: str, revenue_streams: Dict, market_analysis: Dict, financial_metrics: Dict) -> Dict[str, Any]:
        """Generate LLM-powered revenue insights"""
        try:
            prompt = f"""
            Analyze the revenue streams and market position for {ticker}:
            
            Revenue Model: {revenue_streams.get('revenue_model', 'Unknown')}
            Total Revenue: ${revenue_streams.get('total_revenue_ttm', 0):,.0f}
            Revenue Growth: {revenue_streams.get('revenue_growth_yoy', 0):.1f}%
            Market Sensitivity: {market_analysis.get('market_sensitivity', 'Unknown')}
            Sector Correlation: {market_analysis.get('average_correlation', 0):.2f}
            
            Provide a brief analysis covering:
            1. Revenue stream quality and sustainability
            2. Market exposure and cyclicality
            3. Growth drivers and risks
            4. Competitive positioning
            
            Format as JSON with keys: revenue_quality, market_exposure, growth_drivers, competitive_position
            """
            
            response = self.llm_manager.generate_response(prompt)
            
            # Try to parse JSON response
            try:
                import json
                # Extract JSON from response if wrapped in markdown
                if '```json' in response:
                    json_str = response.split('```json')[1].split('```')[0].strip()
                elif '```' in response:
                    json_str = response.split('```')[1].split('```')[0].strip()
                else:
                    json_str = response.strip()
                
                insights = json.loads(json_str)
                return insights
            except:
                # Fallback to basic analysis
                return {
                    'revenue_quality': 'Analysis unavailable',
                    'market_exposure': f"Market sensitivity: {market_analysis.get('market_sensitivity', 'Unknown')}",
                    'growth_drivers': f"Revenue growth: {revenue_streams.get('revenue_growth_yoy', 0):.1f}%",
                    'competitive_position': 'Requires further analysis'
                }
                
        except Exception as e:
            return {'error': f'Revenue insights generation failed: {str(e)}'}
    
    def _generate_recommendation(self, earnings_forecast: Dict, market_analysis: Dict) -> str:
        """Generate investment recommendation based on revenue analysis"""
        try:
            growth_rate = earnings_forecast.get('growth_rate_estimate', 0)
            confidence = earnings_forecast.get('confidence_level', 0.5)
            market_sensitivity = market_analysis.get('average_correlation', 0.5)
            
            # Scoring system
            score = 0
            
            # Growth score
            if growth_rate > 15:
                score += 3
            elif growth_rate > 5:
                score += 2
            elif growth_rate > 0:
                score += 1
            
            # Confidence score
            if confidence > 0.7:
                score += 2
            elif confidence > 0.5:
                score += 1
            
            # Market sensitivity (diversification benefit)
            if market_sensitivity < 0.5:  # Lower correlation = more defensive
                score += 1
            
            # Generate recommendation
            if score >= 5:
                return 'Strong Buy'
            elif score >= 4:
                return 'Buy'
            elif score >= 2:
                return 'Hold'
            else:
                return 'Sell'
                
        except:
            return 'Hold'
    
    def is_applicable(self, company_type: str) -> bool:
        """Revenue stream analysis applies to all company types"""
        return True
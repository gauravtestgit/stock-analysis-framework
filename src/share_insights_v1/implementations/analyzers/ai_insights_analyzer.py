from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
import json
import os
from datetime import datetime, timedelta
from ...implementations.llm_providers.llm_manager import LLMManager

class AIInsightsAnalyzer(IAnalyzer):
    """AI-powered analyzer for market insights and revenue trends"""
    
    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider
        self.llm_manager = LLMManager()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using AI insights for market analysis and revenue trends"""
        try:
            # Store ticker for use in helper methods
            self._current_ticker = ticker
            financial_metrics = data.get('financial_metrics', {})
            current_price = financial_metrics.get('current_price', 0)
            
            # Get current price from price data if not available in financial metrics
            if not current_price:
                price_data = data.get('price_data', {})
                price_history = price_data.get('price_history')
                if price_history is not None and not price_history.empty:
                    current_price = price_history['Close'].iloc[-1]
            
            # Get AI insights
            ai_insights = self._get_ai_insights(ticker, financial_metrics)
            
            # Focus on AI-powered market insights and revenue analysis
            # News sentiment is now handled by dedicated NewsSentimentAnalyzer
            
            # Analyze revenue trends
            revenue_trends = self._analyze_revenue_trends(financial_metrics)
            
            # Calculate target price first
            target_price = self._calculate_ai_target_price(current_price, ai_insights)
            
            # Generate AI recommendation based on target price and insights
            ai_recommendation = self._generate_ai_recommendation(
                ai_insights, revenue_trends, current_price, target_price
            )
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(revenue_trends)
            
            return {
                'method': 'AI Insights Analysis',
                'applicable': True,
                'current_price': current_price,
                'predicted_price': self._calculate_ai_target_price(current_price, ai_insights),
                'recommendation': ai_recommendation,
                'confidence': confidence,
                'ai_insights': ai_insights,
                'revenue_trends': revenue_trends,
                'market_analysis': self._get_market_analysis(ticker, financial_metrics),
                'ai_methods_used': {
                    'insights': ai_insights.get('ai_method', 'Unknown'),
                    'revenue_trends': revenue_trends.get('ai_method', 'Unknown')
                },
                'risk_factors': self._identify_ai_risk_factors(ai_insights),
                'analysis_type': 'ai_insights'
            }
            
        except Exception as e:
            return {'error': f"AI insights analysis failed: {str(e)}"}
    
    def _get_ai_insights(self, ticker: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered insights about the company or ETF"""
        
        try:
            company_name = financial_metrics.get('long_name', ticker)
            quote_type = financial_metrics.get('quote_type', 'EQUITY')
            
            # Check if this is an ETF
            is_etf = ('ETF' in company_name.upper() or 
                     quote_type == 'ETF' or 
                     ticker.lower().endswith('.nz') and any(x in company_name.upper() for x in ['SMART', 'INDEX', 'FUND']))
            
            if is_etf:
                return self._get_etf_insights(ticker, company_name, financial_metrics)
            else:
                return self._get_company_insights(ticker, company_name, financial_metrics)
                
        except Exception as e:
            print(f"AI insights API error: {e}")
            fallback_insights = self._get_fallback_insights(ticker, financial_metrics)
            fallback_insights['ai_method'] = 'Fallback'
            return fallback_insights
    
    def _get_etf_insights(self, ticker: str, fund_name: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get ETF-specific insights"""
        
        market_cap = financial_metrics.get('market_cap', 0)
        current_price = financial_metrics.get('current_price', 0)
        pe_ratio = financial_metrics.get('pe_ratio', 0)
        pb_ratio = financial_metrics.get('pb_ratio', 0)
        
        # Determine market context
        market_context = self._get_market_context(ticker)
        
        prompt = f"""Analyze {fund_name} ({ticker}) ETF and provide insights:

ETF Details:
- Fund Name: {fund_name}
- Assets Under Management: ${market_cap:,.0f}
- Current Price: ${current_price:.2f}
- P/E Ratio: {pe_ratio:.2f}
- P/B Ratio: {pb_ratio or 'N/A'}
- Market Context: {market_context['market_name']}

As an ETF analyst, provide analysis focusing on ETF-specific factors in JSON format:
{{
    "market_position": "Strong/Moderate/Weak",
    "growth_prospects": "High/Moderate/Low", 
    "competitive_advantage": "Strong/Moderate/Weak",
    "management_quality": "Excellent/Good/Average/Poor",
    "industry_outlook": "Very Positive/Positive/Neutral/Negative",
    "key_strengths": ["Low expense ratio", "Diversified holdings", "Good liquidity"],
    "key_risks": ["Market concentration risk", "Tracking error", "Currency risk"]
}}

IMPORTANT: {market_context['analysis_notes']}

Consider ETF-specific factors like:
- Fund size and liquidity relative to {market_context['market_name']} standards
- Expense ratios competitive within {market_context['market_name']}
- Tracking performance vs benchmark
- Geographic/sector concentration
- Provider reputation in {market_context['market_name']}"""
        
        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")
        
        json_str = self._extract_json_from_response(response)
        try:
            insights = json.loads(json_str)
            insights['ai_method'] = 'LLM'
            return insights
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")
    
    def _get_company_insights(self, ticker: str, company_name: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get company-specific insights"""
        
        sector = financial_metrics.get('sector', 'Unknown')
        industry = financial_metrics.get('industry', 'Unknown')
        market_cap = financial_metrics.get('market_cap', 0)
        revenue_growth = financial_metrics.get('yearly_revenue_growth', 0)
        roe = financial_metrics.get('roe', 0) or 0
        
        prompt = f"""Analyze {company_name} ({ticker}) and provide insights:

Company Details:
- Sector: {sector}
- Industry: {industry}
- Market Cap: ${market_cap:,.0f}
- Revenue Growth: {revenue_growth:.1%}
- ROE: {roe:.1%}

Provide analysis in JSON format:
{{
    "market_position": "Strong/Moderate/Weak",
    "growth_prospects": "High/Moderate/Low", 
    "competitive_advantage": "Strong/Moderate/Weak",
    "management_quality": "Excellent/Good/Average/Poor",
    "industry_outlook": "Very Positive/Positive/Neutral/Negative",
    "key_strengths": ["strength1", "strength2"],
    "key_risks": ["risk1", "risk2"]
}}"""
        
        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")
        
        json_str = self._extract_json_from_response(response)
        try:
            insights = json.loads(json_str)
            insights['ai_method'] = 'LLM'
            return insights
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")
    

    
    def _analyze_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze revenue trends using AI (or performance trends for ETFs)"""
        
        try:
            company_name = financial_metrics.get('long_name', '')
            quote_type = financial_metrics.get('quote_type', 'EQUITY')
            
            # Check if this is an ETF
            is_etf = ('ETF' in company_name.upper() or 
                     quote_type == 'ETF' or 
                     any(x in company_name.upper() for x in ['SMART', 'INDEX', 'FUND']))
            
            if is_etf:
                return self._analyze_etf_performance_trends(financial_metrics)
            else:
                return self._analyze_company_revenue_trends(financial_metrics)
                
        except Exception as e:
            print(f"Revenue trends API error: {e}")
            fallback_trends = self._get_fallback_revenue_trends(financial_metrics)
            fallback_trends['ai_method'] = 'Fallback'
            return fallback_trends
    
    def _analyze_etf_performance_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze ETF performance trends"""
        
        current_price = financial_metrics.get('current_price', 0)
        high_52w = financial_metrics.get('fifty_two_week_high', 0)
        low_52w = financial_metrics.get('fifty_two_week_low', 0)
        market_cap = financial_metrics.get('market_cap', 0)
        
        # Calculate performance metrics
        if high_52w and low_52w and current_price:
            ytd_range_position = (current_price - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5
        else:
            ytd_range_position = 0.5
        
        # Get market context - need ticker from somewhere
        ticker = getattr(self, '_current_ticker', '')
        market_context = self._get_market_context(ticker)
        
        prompt = f"""Analyze ETF performance trends for {market_context['market_name']} market:
- Current Price: ${current_price:.2f}
- 52-week High: ${high_52w:.2f}
- 52-week Low: ${low_52w:.2f}
- Position in Range: {ytd_range_position:.1%}
- Assets Under Management: ${market_cap:,.0f}
- Market Context: {market_context['market_name']}

Provide ETF performance analysis in JSON format:
{{
    "trend_assessment": "Strong Performance/Moderate Performance/Stable/Declining",
    "growth_rate": {ytd_range_position:.3f},
    "growth_consistency": "Consistent/Variable/Volatile",
    "future_outlook": "Very Positive/Positive/Neutral/Cautious/Negative"
}}

IMPORTANT: {market_context['analysis_notes']}

Consider factors like:
- Price performance vs 52-week range
- Fund size stability relative to {market_context['market_name']} market
- Market conditions for underlying assets in {market_context['region']}"""
        
        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")
        
        json_str = self._extract_json_from_response(response)
        try:
            trends = json.loads(json_str)
            trends['ai_method'] = 'LLM'
            return trends
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")
    
    def _analyze_company_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company revenue trends"""
        
        revenue_growth = financial_metrics.get('revenue_growth', 0) or 0
        yearly_growth = financial_metrics.get('yearly_revenue_growth', 0) or 0
        total_revenue = financial_metrics.get('total_revenue', 0) or 0
        
        prompt = f"""Analyze revenue trends for a company with these metrics:
- Current revenue growth: {revenue_growth:.1%}
- Yearly revenue growth: {yearly_growth:.1%}
- Total revenue: ${total_revenue:,.0f}

Provide analysis in JSON format:
{{
    "trend_assessment": "Strong Growth/Moderate Growth/Stable/Declining",
    "growth_rate": {yearly_growth},
    "growth_consistency": "Consistent/Variable/Volatile",
    "future_outlook": "Very Positive/Positive/Neutral/Cautious/Negative"
}}"""
        
        response = self.llm_manager.generate_response(prompt)
        if not response or not response.strip():
            raise Exception("Empty response from LLM")
        
        json_str = self._extract_json_from_response(response)
        try:
            trends = json.loads(json_str)
            trends['ai_method'] = 'LLM'
            return trends
        except json.JSONDecodeError:
            raise Exception("Invalid JSON response from LLM")
    
    def _generate_ai_recommendation(self, ai_insights: Dict, revenue_trends: Dict, current_price: float, target_price: float) -> str:
        """Generate recommendation based on target price and AI insights"""
        
        # Primary logic: base recommendation on price target vs current price
        if current_price > 0 and target_price > 0:
            upside_pct = ((target_price - current_price) / current_price) * 100
            
            # Base recommendation on upside/downside
            if upside_pct > 15:
                base_recommendation = 'Strong Buy'
            elif upside_pct > 5:
                base_recommendation = 'Buy'
            elif upside_pct < -15:
                base_recommendation = 'Strong Sell'
            elif upside_pct < -5:
                base_recommendation = 'Sell'
            else:
                base_recommendation = 'Hold'
            
            # Adjust based on qualitative factors (but don't contradict price logic)
            risk_factors = 0
            positive_factors = 0
            
            # Count negative factors
            if ai_insights.get('competitive_advantage') == 'Weak':
                risk_factors += 1
            if revenue_trends.get('future_outlook') == 'Negative':
                risk_factors += 1
            if ai_insights.get('industry_outlook') == 'Negative':
                risk_factors += 1
            
            # Count positive factors
            if ai_insights.get('market_position') == 'Strong':
                positive_factors += 1
            if ai_insights.get('growth_prospects') == 'High':
                positive_factors += 1
            
            # Only downgrade recommendation if significant risks and marginal upside
            if risk_factors >= 2 and upside_pct < 10:
                if base_recommendation == 'Strong Buy':
                    return 'Buy'
                elif base_recommendation == 'Buy':
                    return 'Hold'
            
            return base_recommendation
        
        # Fallback to qualitative assessment if no price data
        return self._get_fallback_recommendation(ai_insights, revenue_trends)
    
    def _calculate_ai_target_price(self, current_price: float, ai_insights: Dict) -> float:
        """Calculate AI-based target price"""
        
        if not current_price:
            return 0
        
        # Base adjustment on AI insights
        adjustment_factor = 1.0
        
        if ai_insights.get('growth_prospects') == 'High':
            adjustment_factor += 0.15
        elif ai_insights.get('growth_prospects') == 'Low':
            adjustment_factor -= 0.10
        
        if ai_insights.get('market_position') == 'Strong':
            adjustment_factor += 0.10
        elif ai_insights.get('market_position') == 'Weak':
            adjustment_factor -= 0.10
        
        return current_price * adjustment_factor
    
    def _calculate_confidence(self, revenue_trends: Dict) -> str:
        """Calculate confidence level based on data quality"""
        
        confidence_score = 0
        
        # Revenue trend consistency
        if revenue_trends.get('growth_consistency') == 'Consistent':
            confidence_score += 1
        else:
            confidence_score += 0.5
        
        # AI method quality
        if revenue_trends.get('ai_method') == 'LLM':
            confidence_score += 0.5
        
        if confidence_score >= 1.0:
            return 'High'
        elif confidence_score >= 0.75:
            return 'Medium'
        else:
            return 'Low'
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response that may contain markdown code blocks"""
        import re
        
        # First try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find JSON in regular code blocks
        json_match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            potential_json = json_match.group(1).strip()
            if potential_json.startswith('{') and potential_json.endswith('}'):
                return potential_json
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # If no JSON found, return original response
        return response
    
    def _assess_market_position(self, financial_metrics: Dict) -> str:
        """Assess market position based on financial metrics"""
        
        market_cap = financial_metrics.get('market_cap', 0)
        roe = financial_metrics.get('roe', 0)
        
        if market_cap > 100_000_000_000 and roe > 0.15:  # Large cap with good ROE
            return 'Strong'
        elif market_cap > 10_000_000_000 and roe > 0.10:  # Mid cap with decent ROE
            return 'Moderate'
        else:
            return 'Weak'
    
    def _assess_growth_prospects(self, financial_metrics: Dict) -> str:
        """Assess growth prospects based on financial metrics"""
        
        revenue_growth = financial_metrics.get('yearly_revenue_growth', 0)
        earnings_growth = financial_metrics.get('earnings_growth', 0)
        
        if revenue_growth > 0.20 and earnings_growth > 0.15:
            return 'High'
        elif revenue_growth > 0.10 and earnings_growth > 0.05:
            return 'Moderate'
        else:
            return 'Low'
    
    def _get_fallback_insights(self, ticker: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback insights when AI is not available"""
        return {
            'market_position': self._assess_market_position(financial_metrics),
            'growth_prospects': self._assess_growth_prospects(financial_metrics),
            'competitive_advantage': 'Moderate',
            'management_quality': 'Good',
            'industry_outlook': 'Positive',
            'key_strengths': ['Financial stability'],
            'key_risks': ['Market volatility']
        }
    

    
    def _get_fallback_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback revenue trends when AI is not available"""
        yearly_growth = financial_metrics.get('yearly_revenue_growth', 0)
        
        if yearly_growth > 0.15:
            trend_assessment = 'Strong Growth'
        elif yearly_growth > 0.05:
            trend_assessment = 'Moderate Growth'
        elif yearly_growth > -0.05:
            trend_assessment = 'Stable'
        else:
            trend_assessment = 'Declining'
        
        return {
            'trend_assessment': trend_assessment,
            'growth_rate': yearly_growth,
            'growth_consistency': 'Consistent',
            'future_outlook': 'Positive' if yearly_growth > 0 else 'Cautious'
        }
    
    def _get_fallback_recommendation(self, ai_insights: Dict, revenue_trends: Dict) -> str:
        """Fallback recommendation when price-based logic can't be used"""
        positive_factors = 0
        negative_factors = 0
        
        if ai_insights.get('market_position') == 'Strong':
            positive_factors += 2
        elif ai_insights.get('market_position') == 'Weak':
            negative_factors += 1
        
        if ai_insights.get('growth_prospects') == 'High':
            positive_factors += 2
        elif ai_insights.get('growth_prospects') == 'Low':
            negative_factors += 1
        
        if revenue_trends.get('trend_assessment') in ['Strong Growth', 'Moderate Growth']:
            positive_factors += 1
        elif revenue_trends.get('trend_assessment') == 'Declining':
            negative_factors += 2
        
        net_score = positive_factors - negative_factors
        
        if net_score >= 3:
            return 'Strong Buy'
        elif net_score >= 1:
            return 'Buy'
        elif net_score <= -3:
            return 'Strong Sell'
        elif net_score <= -1:
            return 'Sell'
        else:
            return 'Hold'
    

    
    def _identify_ai_risk_factors(self, ai_insights: Dict) -> list:
        """Identify risk factors using AI insights"""
        
        risk_factors = []
        
        if ai_insights.get('market_position') == 'Weak':
            risk_factors.append('Weak market position')
        
        if ai_insights.get('growth_prospects') == 'Low':
            risk_factors.append('Limited growth prospects')
        
        if ai_insights.get('competitive_advantage') == 'Weak':
            risk_factors.append('Weak competitive advantage')
        
        if ai_insights.get('industry_outlook') == 'Negative':
            risk_factors.append('Negative industry outlook')
        
        return risk_factors
    
    def _get_market_analysis(self, ticker: str, financial_metrics: Dict) -> Dict[str, Any]:
        """Get market analysis summary"""
        return {
            'market_cap_category': self._get_market_cap_category(financial_metrics.get('market_cap', 0)),
            'sector': financial_metrics.get('sector', 'Unknown'),
            'industry': financial_metrics.get('industry', 'Unknown'),
            'beta': financial_metrics.get('beta', 1.0)
        }
    
    def _get_market_cap_category(self, market_cap: float) -> str:
        """Categorize market cap"""
        if market_cap > 200_000_000_000:
            return 'Mega Cap'
        elif market_cap > 10_000_000_000:
            return 'Large Cap'
        elif market_cap > 2_000_000_000:
            return 'Mid Cap'
        elif market_cap > 300_000_000:
            return 'Small Cap'
        else:
            return 'Micro Cap'
    
    def _get_market_context(self, ticker: str) -> Dict[str, str]:
        """Get market-specific context for analysis"""
        ticker_lower = ticker.lower()
        
        if ticker_lower.endswith('.nz'):
            return {
                'market_name': 'New Zealand (NZX)',
                'region': 'New Zealand/Australia',
                'analysis_notes': 'Analyze relative to NZ market standards. Lower trading volumes and smaller fund sizes are normal for NZ ETFs. Focus on NZ-specific factors like currency exposure and local market dynamics.'
            }
        elif ticker_lower.endswith('.ax') or ticker_lower.endswith('.asx'):
            return {
                'market_name': 'Australian (ASX)',
                'region': 'Australia',
                'analysis_notes': 'Analyze relative to Australian market standards. Consider ASX-specific factors and regional market dynamics.'
            }
        elif ticker_lower.endswith('.l') or ticker_lower.endswith('.lon'):
            return {
                'market_name': 'London (LSE)',
                'region': 'United Kingdom/Europe',
                'analysis_notes': 'Analyze relative to UK/European market standards. Consider Brexit impacts and European market dynamics.'
            }
        else:
            return {
                'market_name': 'US Market',
                'region': 'United States',
                'analysis_notes': 'Analyze relative to US market standards with typical US ETF benchmarks for volume and fund size.'
            }
    
    def is_applicable(self, company_type: str) -> bool:
        """AI insights applicable to all company types"""
        return True
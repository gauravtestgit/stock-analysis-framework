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
            financial_metrics = data.get('financial_metrics', {})
            current_price = financial_metrics.get('current_price', 0)
            
            # Get AI insights
            ai_insights = self._get_ai_insights(ticker, financial_metrics)
            
            # Focus on AI-powered market insights and revenue analysis
            # News sentiment is now handled by dedicated NewsSentimentAnalyzer
            
            # Analyze revenue trends
            revenue_trends = self._analyze_revenue_trends(financial_metrics)
            
            # Generate AI recommendation
            ai_recommendation = self._generate_ai_recommendation(
                ai_insights, revenue_trends
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
        """Get AI-powered insights about the company"""
        
        try:
            company_name = financial_metrics.get('long_name', ticker)
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
            
            # Extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json_from_response(response)
            try:
                insights = json.loads(json_str)
                insights['ai_method'] = 'LLM'
                return insights
            except json.JSONDecodeError:
                raise Exception("Invalid JSON response from LLM")
                
        except Exception as e:
            print(f"AI insights API error: {e}")
            fallback_insights = self._get_fallback_insights(ticker, financial_metrics)
            fallback_insights['ai_method'] = 'Fallback'
            return fallback_insights
    

    
    def _analyze_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze revenue trends using AI"""
        
        try:
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
            
            # Extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json_from_response(response)
            try:
                trends = json.loads(json_str)
                trends['ai_method'] = 'LLM'
                return trends
            except json.JSONDecodeError:
                raise Exception("Invalid JSON response from LLM")
                
        except Exception as e:
            print(f"Revenue trends API error: {e}")
            fallback_trends = self._get_fallback_revenue_trends(financial_metrics)
            fallback_trends['ai_method'] = 'Fallback'
            return fallback_trends
    
    def _generate_ai_recommendation(self, ai_insights: Dict, revenue_trends: Dict) -> str:
        """Generate recommendation based on AI insights"""
        
        try:
            prompt = f"""Generate an investment recommendation based on these AI insights:

Company Analysis:
- Market Position: {ai_insights.get('market_position', 'Unknown')}
- Growth Prospects: {ai_insights.get('growth_prospects', 'Unknown')}
- Competitive Advantage: {ai_insights.get('competitive_advantage', 'Unknown')}

Revenue Analysis:
- Trend Assessment: {revenue_trends.get('trend_assessment', 'Unknown')}
- Future Outlook: {revenue_trends.get('future_outlook', 'Unknown')}

Provide recommendation as one of: Strong Buy, Buy, Hold, Sell, Strong Sell

Respond with only the recommendation text."""
            
            recommendation = self.llm_manager.generate_response(prompt).strip()
            
            # Validate recommendation
            valid_recs = ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']
            if recommendation in valid_recs:
                return recommendation
            else:
                return self._get_fallback_recommendation(ai_insights, revenue_trends)
                
        except Exception as e:
            print(f"AI recommendation API error: {e}")
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
        """Fallback recommendation when AI is not available"""
        positive_factors = 0
        negative_factors = 0
        
        if ai_insights.get('market_position') == 'Strong':
            positive_factors += 1
        elif ai_insights.get('market_position') == 'Weak':
            negative_factors += 1
        
        if ai_insights.get('growth_prospects') == 'High':
            positive_factors += 1
        elif ai_insights.get('growth_prospects') == 'Low':
            negative_factors += 1
        
        if revenue_trends.get('trend_assessment') in ['Strong Growth', 'Moderate Growth']:
            positive_factors += 1
        elif revenue_trends.get('trend_assessment') == 'Declining':
            negative_factors += 1
        
        net_score = positive_factors - negative_factors
        
        if net_score >= 2:
            return 'Strong Buy'
        elif net_score >= 1:
            return 'Buy'
        elif net_score <= -2:
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
    
    def is_applicable(self, company_type: str) -> bool:
        """AI insights applicable to all company types"""
        return True
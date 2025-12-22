from typing import Dict, Any, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...implementations.llm_providers.llm_manager import LLMManager
import json

class IndustryAnalysisAnalyzer(IAnalyzer):
    """Industry and sector-specific qualitative analysis"""
    
    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider
        self.llm_manager = LLMManager()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform industry-specific qualitative analysis"""
        try:
            financial_metrics = data.get('financial_metrics', {})
            sector = financial_metrics.get('sector', 'Unknown')
            industry = financial_metrics.get('industry', 'Unknown')
            
            if sector == 'Unknown' or industry == 'Unknown':
                return {
                    'applicable': False,
                    'reason': 'Insufficient sector/industry data for analysis'
                }
            
            # Get recent news for context
            news_data = self._get_recent_news(ticker)
            
            # Get industry analysis with news context
            industry_insights = self._analyze_industry_dynamics(ticker, sector, industry, financial_metrics, news_data)
            
            # Get competitive positioning
            competitive_analysis = self._analyze_competitive_position(ticker, sector, industry, financial_metrics)
            
            # Get market catalysts with news context
            market_catalysts = self._identify_market_catalysts(ticker, sector, industry, news_data)
            
            # Generate recommendation
            recommendation = self._generate_industry_recommendation(
                industry_insights, competitive_analysis, market_catalysts
            )
            
            return {
                'method': 'Industry Analysis',
                'applicable': True,
                'sector': sector,
                'industry': industry,
                'recommendation': recommendation['recommendation'],
                'confidence': recommendation['confidence'],
                'industry_outlook': industry_insights.get('outlook', 'Neutral'),
                'competitive_position': competitive_analysis.get('position', 'Average'),
                'market_catalysts': market_catalysts,
                'industry_insights': industry_insights,
                'competitive_analysis': competitive_analysis,
                'key_risks': self._identify_industry_risks(sector, industry),
                'analysis_type': 'industry_analysis'
            }
            
        except Exception as e:
            return {'error': f"Industry analysis failed: {str(e)}"}
    
    def _analyze_industry_dynamics(self, ticker: str, sector: str, industry: str, metrics: Dict, news_data: List = None) -> Dict:
        """Analyze industry-specific dynamics and trends"""
        
        market_cap = metrics.get('market_cap', 0)
        revenue_growth = metrics.get('yearly_revenue_growth', 0) or 0
        
        news_context = ""
        if news_data:
            news_context = f"\n\nRecent News Context:\n" + "\n".join([f"- {item}" for item in news_data[:3]])
        
        prompt = f"""Analyze the industry dynamics for {industry} sector ({sector}):

Company: {ticker}
Market Cap: ${market_cap:,.0f}
Revenue Growth: {revenue_growth:.1%}{news_context}

Provide industry analysis in JSON format:
{{
    "outlook": "Very Positive/Positive/Neutral/Negative/Very Negative",
    "growth_drivers": ["driver1", "driver2"],
    "headwinds": ["headwind1", "headwind2"],
    "market_size": "Large/Medium/Small/Niche",
    "maturity": "Emerging/Growth/Mature/Declining",
    "cyclicality": "High/Medium/Low",
    "regulatory_environment": "Favorable/Neutral/Challenging",
    "technology_disruption": "High/Medium/Low",
    "supply_demand_balance": "Oversupply/Balanced/Undersupply"
}}

Focus on:
- Current industry trends and outlook
- Key growth drivers and challenges
- Regulatory environment impact
- Technology disruption risks
- Supply/demand dynamics"""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_industry_analysis(sector, industry)
    
    def _analyze_competitive_position(self, ticker: str, sector: str, industry: str, metrics: Dict) -> Dict:
        """Analyze competitive positioning within industry"""
        
        market_cap = metrics.get('market_cap', 0)
        pe_ratio = metrics.get('pe_ratio', 0)
        revenue_growth = metrics.get('yearly_revenue_growth', 0) or 0
        
        prompt = f"""Analyze competitive position for {ticker} in {industry}:

Market Cap: ${market_cap:,.0f}
P/E Ratio: {pe_ratio}
Revenue Growth: {revenue_growth:.1%}

Provide competitive analysis in JSON format:
{{
    "position": "Market Leader/Strong Player/Average/Weak/Niche Player",
    "market_share": "High/Medium/Low/Unknown",
    "competitive_advantages": ["advantage1", "advantage2"],
    "competitive_disadvantages": ["disadvantage1", "disadvantage2"],
    "barriers_to_entry": "High/Medium/Low",
    "switching_costs": "High/Medium/Low",
    "brand_strength": "Strong/Average/Weak",
    "cost_position": "Low Cost/Average/High Cost",
    "innovation_capability": "Leading/Following/Lagging"
}}

Consider:
- Market position vs competitors
- Unique competitive advantages
- Brand strength and customer loyalty
- Cost structure advantages
- Innovation and R&D capabilities"""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            return json.loads(json_str)
        except:
            return self._get_fallback_competitive_analysis()
    
    def _identify_market_catalysts(self, ticker: str, sector: str, industry: str, news_data: List = None) -> List[str]:
        """Identify potential market catalysts for the industry"""
        
        news_context = ""
        if news_data:
            news_context = f"\n\nRecent News Context:\n" + "\n".join([f"- {item}" for item in news_data[:3]])
        
        prompt = f"""Identify key market catalysts for {industry} sector ({ticker}):{news_context}

List 3-5 potential catalysts that could drive stock performance:
- Policy/regulatory changes
- Technology developments
- Market trends
- Economic factors
- Industry-specific events

Return as simple list of strings."""
        
        try:
            response = self.llm_manager.generate_response(prompt)
            # Parse response into list
            catalysts = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('1.')):
                    catalyst = line.lstrip('-•1234567890. ').strip()
                    if catalyst:
                        catalysts.append(catalyst)
            return catalysts[:5]  # Limit to 5
        except:
            return self._get_fallback_catalysts(sector, industry)
    
    def _generate_industry_recommendation(self, industry_insights: Dict, competitive_analysis: Dict, catalysts: List) -> Dict:
        """Generate recommendation based on industry analysis"""
        
        # Score based on industry outlook
        outlook_scores = {
            'Very Positive': 2, 'Positive': 1, 'Neutral': 0, 
            'Negative': -1, 'Very Negative': -2
        }
        
        # Score based on competitive position
        position_scores = {
            'Market Leader': 2, 'Strong Player': 1, 'Average': 0,
            'Weak': -1, 'Niche Player': 0
        }
        
        outlook_score = outlook_scores.get(industry_insights.get('outlook', 'Neutral'), 0)
        position_score = position_scores.get(competitive_analysis.get('position', 'Average'), 0)
        catalyst_score = min(len(catalysts), 3) - 2  # -2 to +1 based on catalyst count
        
        total_score = outlook_score + position_score + catalyst_score
        
        if total_score >= 3:
            return {'recommendation': 'Strong Buy', 'confidence': 'High'}
        elif total_score >= 1:
            return {'recommendation': 'Buy', 'confidence': 'Medium'}
        elif total_score <= -3:
            return {'recommendation': 'Strong Sell', 'confidence': 'High'}
        elif total_score <= -1:
            return {'recommendation': 'Sell', 'confidence': 'Medium'}
        else:
            return {'recommendation': 'Hold', 'confidence': 'Medium'}
    
    def _identify_industry_risks(self, sector: str, industry: str) -> List[str]:
        """Identify key industry-specific risks"""
        
        # Common risks by sector
        sector_risks = {
            'Technology': ['Technology obsolescence', 'Regulatory changes', 'Cybersecurity threats'],
            'Healthcare': ['Regulatory approval risks', 'Patent expiration', 'Reimbursement changes'],
            'Energy': ['Commodity price volatility', 'Regulatory changes', 'Environmental concerns'],
            'Financial Services': ['Interest rate changes', 'Credit losses', 'Regulatory compliance'],
            'Consumer Cyclical': ['Economic downturn', 'Consumer spending changes', 'Supply chain disruption'],
            'Basic Materials': ['Commodity price cycles', 'Environmental regulations', 'Global demand shifts']
        }
        
        return sector_risks.get(sector, ['Market volatility', 'Competitive pressure', 'Economic uncertainty'])
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response"""
        import re
        
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
        
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return response
    
    def _get_fallback_industry_analysis(self, sector: str, industry: str) -> Dict:
        """Fallback industry analysis when LLM fails"""
        return {
            'outlook': 'Neutral',
            'growth_drivers': ['Market expansion', 'Innovation'],
            'headwinds': ['Competition', 'Regulation'],
            'market_size': 'Medium',
            'maturity': 'Mature',
            'cyclicality': 'Medium',
            'regulatory_environment': 'Neutral',
            'technology_disruption': 'Medium',
            'supply_demand_balance': 'Balanced'
        }
    
    def _get_fallback_competitive_analysis(self) -> Dict:
        """Fallback competitive analysis when LLM fails"""
        return {
            'position': 'Average',
            'market_share': 'Unknown',
            'competitive_advantages': ['Established operations'],
            'competitive_disadvantages': ['Market competition'],
            'barriers_to_entry': 'Medium',
            'switching_costs': 'Medium',
            'brand_strength': 'Average',
            'cost_position': 'Average',
            'innovation_capability': 'Following'
        }
    

    
    def _get_recent_news(self, ticker: str) -> List[str]:
        """Get recent news titles for context"""
        try:
            news_data = self.data_provider.get_news_data(ticker)
            if news_data and 'articles' in news_data:
                return [article.get('title', '') for article in news_data['articles'][:3] if article.get('title')]
            return []
        except:
            return []
    
    def _get_fallback_catalysts(self, sector: str, industry: str) -> List[str]:
        """Fallback catalysts when LLM fails"""
        return [
            'Market expansion opportunities',
            'Regulatory clarity',
            'Technology adoption',
            'Economic recovery'
        ]
    
    def is_applicable(self, company_type: str) -> bool:
        """Industry analysis applicable to all company types"""
        return True
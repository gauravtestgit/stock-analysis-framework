from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
import json
import os
from datetime import datetime, timedelta
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class AIInsightsAnalyzer(IAnalyzer):
    """AI-powered analyzer for news sentiment, revenue trends, and market insights"""
    
    def __init__(self, data_provider: IDataProvider, api_key: Optional[str] = None):
        self.data_provider = data_provider
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.llm = None
        
        try:
            if self.api_key:
                self.llm = ChatGroq(
                    groq_api_key=self.api_key,
                    model_name="llama-3.1-8b-instant",
                    temperature=0.1
                )
        except Exception as e:
            print(f"Warning: Could not initialize LLM: {e}")
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze using AI insights for news, trends, and market sentiment"""
        try:
            financial_metrics = data.get('financial_metrics', {})
            current_price = financial_metrics.get('current_price', 0)
            
            # Get AI insights
            ai_insights = self._get_ai_insights(ticker, financial_metrics)
            
            # Get news articles for analysis and user review
            news_articles = self._get_recent_news(ticker)
            
            # Analyze news sentiment
            news_sentiment = self._analyze_news_sentiment_with_articles(ticker, news_articles)
            
            # Analyze revenue trends
            revenue_trends = self._analyze_revenue_trends(financial_metrics)
            
            # Generate AI recommendation
            ai_recommendation = self._generate_ai_recommendation(
                ai_insights, news_sentiment, revenue_trends
            )
            
            # Calculate confidence based on data quality
            confidence = self._calculate_confidence(news_sentiment, revenue_trends)
            
            return {
                'method': 'AI Insights Analysis',
                'applicable': True,
                'current_price': current_price,
                'predicted_price': self._calculate_ai_target_price(current_price, ai_insights),
                'recommendation': ai_recommendation,
                'confidence': confidence,
                'ai_insights': ai_insights,
                'news_sentiment': news_sentiment,
                'news_articles': news_articles,
                'revenue_trends': revenue_trends,
                'ai_methods_used': {
                    'insights': ai_insights.get('ai_method', 'Unknown'),
                    'news_sentiment': news_sentiment.get('ai_method', 'Unknown'),
                    'revenue_trends': revenue_trends.get('ai_method', 'Unknown')
                },
                'risk_factors': self._identify_ai_risk_factors(ai_insights, news_sentiment),
                'analysis_type': 'ai_insights'
            }
            
        except Exception as e:
            return {'error': f"AI insights analysis failed: {str(e)}"}
    
    def _get_ai_insights(self, ticker: str, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered insights about the company"""
        
        if not self.llm:
            return self._get_fallback_insights(ticker, financial_metrics)
        
        try:
            company_name = financial_metrics.get('long_name', ticker)
            sector = financial_metrics.get('sector', 'Unknown')
            industry = financial_metrics.get('industry', 'Unknown')
            market_cap = financial_metrics.get('market_cap', 0)
            revenue_growth = financial_metrics.get('yearly_revenue_growth', 0)
            roe = financial_metrics.get('roe', 0) or 0
            
            prompt = ChatPromptTemplate.from_template(
                """Analyze {company_name} ({ticker}) and provide insights:
                
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
            )
            
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            insights = chain.invoke({
                "company_name": company_name,
                "ticker": ticker,
                "sector": sector,
                "industry": industry,
                "market_cap": market_cap,
                "revenue_growth": revenue_growth,
                "roe": roe
            })
            
            insights['ai_method'] = 'LLM'
            return insights
                
        except Exception as e:
            print(f"AI insights API error: {e}")
            fallback_insights = self._get_fallback_insights(ticker, financial_metrics)
            fallback_insights['ai_method'] = 'Fallback'
            return fallback_insights
    
    def _analyze_news_sentiment_with_articles(self, ticker: str, news_articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze news sentiment using provided articles"""
        
        if not self.llm or not news_articles:
            return self._get_fallback_news_sentiment()
        
        try:
            # Prepare news content for analysis
            news_content = "\n".join([
                f"Title: {article.get('title', '')}\nSummary: {article.get('summary', '')}\nDate: {article.get('publish_date', '')}"
                for article in news_articles[:5]  # Limit to 5 articles
            ])
            
            prompt = ChatPromptTemplate.from_template(
                """You are a financial analyst. Analyze the sentiment of these news articles for {ticker}.
                
                News Articles:
                {news_content}
                
                IMPORTANT: Respond ONLY with valid JSON. Do not include explanations, code, or markdown.
                
                Required JSON format:
                {{
                    "overall_sentiment": "Positive/Neutral/Negative",
                    "sentiment_score": 0.0,
                    "news_count": {news_count},
                    "key_themes": ["theme1", "theme2", "theme3"],
                    "sentiment_trend": "Improving/Stable/Deteriorating"
                }}
                
                Sentiment score: -1.0 (very negative) to 1.0 (very positive)."""
            )
            
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            sentiment = chain.invoke({
                "ticker": ticker,
                "news_content": news_content,
                "news_count": len(news_articles)
            })
            
            sentiment['ai_method'] = 'LLM'
            return sentiment
                
        except Exception as e:
            print(f"News sentiment API error: {e}")
            fallback_sentiment = self._get_fallback_news_sentiment()
            fallback_sentiment['ai_method'] = 'Fallback'
            return fallback_sentiment
    
    def _analyze_revenue_trends(self, financial_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze revenue trends using AI"""
        
        if not self.llm:
            return self._get_fallback_revenue_trends(financial_metrics)
        
        try:
            revenue_growth = financial_metrics.get('revenue_growth', 0) or 0
            yearly_growth = financial_metrics.get('yearly_revenue_growth', 0) or 0
            total_revenue = financial_metrics.get('total_revenue', 0) or 0
            
            prompt = ChatPromptTemplate.from_template(
                """Analyze revenue trends for a company with these metrics:
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
            )
            
            parser = JsonOutputParser()
            chain = prompt | self.llm | parser
            
            trends = chain.invoke({
                "revenue_growth": revenue_growth,
                "yearly_growth": yearly_growth,
                "total_revenue": total_revenue
            })
            
            trends['ai_method'] = 'LLM'
            return trends
                
        except Exception as e:
            print(f"Revenue trends API error: {e}")
            fallback_trends = self._get_fallback_revenue_trends(financial_metrics)
            fallback_trends['ai_method'] = 'Fallback'
            return fallback_trends
    
    def _generate_ai_recommendation(self, ai_insights: Dict, news_sentiment: Dict, revenue_trends: Dict) -> str:
        """Generate recommendation based on AI insights"""
        
        if not self.llm:
            return self._get_fallback_recommendation(ai_insights, news_sentiment, revenue_trends)
        
        try:
            prompt = ChatPromptTemplate.from_template(
                """Generate an investment recommendation based on these AI insights:
                
                Company Analysis:
                - Market Position: {market_position}
                - Growth Prospects: {growth_prospects}
                - Competitive Advantage: {competitive_advantage}
                
                Market Sentiment:
                - Overall Sentiment: {overall_sentiment}
                - Sentiment Trend: {sentiment_trend}
                
                Revenue Analysis:
                - Trend Assessment: {trend_assessment}
                - Future Outlook: {future_outlook}
                
                Provide recommendation as one of: Strong Buy, Buy, Hold, Sell, Strong Sell
                
                Respond with only the recommendation text."""
            )
            
            chain = prompt | self.llm
            
            recommendation = chain.invoke({
                "market_position": ai_insights.get('market_position', 'Unknown'),
                "growth_prospects": ai_insights.get('growth_prospects', 'Unknown'),
                "competitive_advantage": ai_insights.get('competitive_advantage', 'Unknown'),
                "overall_sentiment": news_sentiment.get('overall_sentiment', 'Unknown'),
                "sentiment_trend": news_sentiment.get('sentiment_trend', 'Unknown'),
                "trend_assessment": revenue_trends.get('trend_assessment', 'Unknown'),
                "future_outlook": revenue_trends.get('future_outlook', 'Unknown')
            }).content.strip()
            
            # Validate recommendation
            valid_recs = ['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell']
            if recommendation in valid_recs:
                return recommendation
            else:
                return self._get_fallback_recommendation(ai_insights, news_sentiment, revenue_trends)
                
        except Exception as e:
            print(f"AI recommendation API error: {e}")
            return self._get_fallback_recommendation(ai_insights, news_sentiment, revenue_trends)
    
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
    
    def _calculate_confidence(self, news_sentiment: Dict, revenue_trends: Dict) -> str:
        """Calculate confidence level based on data quality"""
        
        confidence_score = 0
        
        # News data quality
        news_count = news_sentiment.get('news_count', 0)
        if news_count >= 10:
            confidence_score += 1
        elif news_count >= 5:
            confidence_score += 0.5
        
        # Revenue trend consistency
        if revenue_trends.get('growth_consistency') == 'Consistent':
            confidence_score += 1
        else:
            confidence_score += 0.5
        
        if confidence_score >= 1.5:
            return 'High'
        elif confidence_score >= 1.0:
            return 'Medium'
        else:
            return 'Low'
    
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
    
    def _get_fallback_news_sentiment(self) -> Dict[str, Any]:
        """Fallback news sentiment when AI is not available"""
        return {
            'overall_sentiment': 'Neutral',
            'sentiment_score': 0.0,
            'news_count': 2,
            'key_themes': ['market conditions', 'industry trends'],
            'sentiment_trend': 'Stable'
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
    
    def _get_fallback_recommendation(self, ai_insights: Dict, news_sentiment: Dict, revenue_trends: Dict) -> str:
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
    
    def _get_recent_news(self, ticker: str) -> List[Dict[str, Any]]:
        """Get recent news articles for the ticker"""
        try:
            # Try to get news from data provider if it has news capability
            if hasattr(self.data_provider, 'get_news_data'):
                return self.data_provider.get_news_data(ticker)
            
            # Fallback: mock news data structure
            return [
                {
                    'title': f'{ticker} reports quarterly earnings',
                    'summary': 'Company reported financial results for the quarter',
                    'publish_date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'Financial News',
                    'url': f'https://finance.yahoo.com/quote/{ticker}/news'
                },
                {
                    'title': f'{ticker} announces strategic initiative',
                    'summary': 'Company announced new business strategy',
                    'publish_date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'Business Wire',
                    'url': f'https://finance.yahoo.com/quote/{ticker}/news'
                }
            ]
        except Exception as e:
            print(f"Error getting news data: {e}")
            return []
    
    def _identify_ai_risk_factors(self, ai_insights: Dict, news_sentiment: Dict) -> list:
        """Identify risk factors using AI insights"""
        
        risk_factors = []
        
        if ai_insights.get('market_position') == 'Weak':
            risk_factors.append('Weak market position')
        
        if ai_insights.get('growth_prospects') == 'Low':
            risk_factors.append('Limited growth prospects')
        
        if news_sentiment.get('overall_sentiment') == 'Negative':
            risk_factors.append('Negative market sentiment')
        
        if news_sentiment.get('sentiment_trend') == 'Deteriorating':
            risk_factors.append('Deteriorating sentiment trend')
        
        return risk_factors
    
    def is_applicable(self, company_type: str) -> bool:
        """AI insights applicable to all company types"""
        return True
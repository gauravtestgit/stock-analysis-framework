from typing import Dict, Any, Optional, List
from ...interfaces.analyzer import IAnalyzer
from ...interfaces.data_provider import IDataProvider
from ...models.news_sentiment import (
    NewsSentimentReport, NewsItem, SentimentTrend, SentimentScore, NewsCategory
)
from ...models.company import CompanyType
import requests
import json
import os
from datetime import datetime, timedelta
from ...implementations.llm_providers.llm_manager import LLMManager

class NewsSentimentAnalyzer(IAnalyzer):
    """Enhanced news sentiment analyzer with recent developments tracking"""
    
    def __init__(self, data_provider: IDataProvider):
        self.data_provider = data_provider
        self.llm_manager = LLMManager()
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news sentiment and recent developments"""
        try:
            company_info = data.get('company_info', {})
            
            # Get recent news
            news_data = self._get_recent_news(ticker, company_info)
            
            if not news_data:
                return {'error': 'Could not retrieve news data'}
            
            # Generate sentiment report
            report = self._analyze_news_sentiment(ticker, news_data)
            
            return {
                'method': 'News Sentiment Analysis',
                'applicable': True,
                'overall_sentiment_score': report.overall_sentiment_score,
                'sentiment_rating': report.sentiment_rating.value,
                'news_count': len(report.recent_news),
                'recent_news': [{
                    'title': item.title,
                    'summary': item.summary,
                    'date': item.date,
                    'source': item.source,
                    'url': getattr(item, 'url', ''),
                    'sentiment': getattr(item, 'sentiment', 'neutral'),
                    'sentiment_score': item.sentiment_score
                } for item in report.recent_news],
                'key_developments': report.key_developments,
                'sentiment_drivers': report.sentiment_drivers,
                'risk_factors': report.risk_factors,
                'overall_summary': self._generate_overall_summary(report),
                'confidence': 'Medium',
                'recommendation': self._generate_recommendation(report)
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def is_applicable(self, company_type: str) -> bool:
        """News sentiment analysis applies to most company types"""
        excluded_types = [CompanyType.ETF.value]
        return company_type not in excluded_types
    
    def _get_recent_news(self, ticker: str, company_info: Dict[str, Any]) -> Optional[List[Dict]]:
        """Get recent news using yfinance"""
        
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            
            # Get news from yfinance
            news_data = stock.news
            
            if not news_data:
                print(f"No news found for {ticker}")
                return None
            

            
            processed_news = []
            for news_item in news_data[:10]:  # Limit to 10 most recent
                # Extract content from nested structure
                content = news_item.get('content', {})
                
                # Parse date from pubDate
                pub_date = content.get('pubDate', '')
                if pub_date:
                    try:
                        # Parse ISO format date
                        news_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    except:
                        news_date = datetime.now().strftime('%Y-%m-%d')
                else:
                    news_date = datetime.now().strftime('%Y-%m-%d')
                
                # Extract provider info
                provider = content.get('provider', {})
                source = provider.get('displayName', 'Unknown')
                
                # Extract URL
                canonical_url = content.get('canonicalUrl', {})
                click_url = content.get('clickThroughUrl', {})
                url = canonical_url.get('url', '') or click_url.get('url', '')
                
                processed_news.append({
                    'title': content.get('title', 'No title'),
                    'summary': content.get('summary', content.get('description', 'No summary')),
                    'date': news_date,
                    'source': source,
                    'url': url,
                    'category': 'general',
                    'sentiment': 'neutral'
                })
            
            return processed_news
            
        except Exception as e:
            print(f"Error fetching news for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_news_sentiment(self, ticker: str, news_data: List[Dict]) -> NewsSentimentReport:
        """Analyze sentiment from news data"""
        
        # Process news items
        news_items = []
        sentiment_scores = []
        
        for news in news_data:
            # Analyze sentiment using AI (or rule-based for demo)
            sentiment_result = self._analyze_text_sentiment(news['title'], news['summary'])
            
            category = self._categorize_news(news)
            
            news_item = NewsItem(
                title=news['title'],
                summary=news['summary'],
                category=category,
                sentiment_score=sentiment_result['score'],
                confidence=sentiment_result['confidence'],
                date=news['date'],
                source=news['source'],
                url=news.get('url', ''),
                sentiment=news.get('sentiment', 'neutral')
            )
            
            news_items.append(news_item)
            sentiment_scores.append(sentiment_result['score'])
        
        # Calculate overall sentiment
        overall_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        sentiment_rating = self._determine_sentiment_rating(overall_sentiment)
        
        # Generate trends
        sentiment_trends = self._calculate_sentiment_trends(news_items)
        
        # Generate insights
        key_developments, sentiment_drivers, risk_factors = self._generate_sentiment_insights(
            news_items, overall_sentiment
        )
        
        return NewsSentimentReport(
            ticker=ticker,
            overall_sentiment_score=overall_sentiment,
            sentiment_rating=sentiment_rating,
            recent_news=news_items,
            sentiment_trends=sentiment_trends,
            key_developments=key_developments,
            sentiment_drivers=sentiment_drivers,
            risk_factors=risk_factors
        )
    
    def _analyze_text_sentiment(self, title: str, summary: str) -> Dict[str, float]:
        """Analyze sentiment of text using LangChain + Groq"""
        
        try:
            prompt = f"""Analyze the sentiment of this financial news and respond with ONLY valid JSON:

Title: {title}
Summary: {summary}

CRITICAL: Return ONLY the JSON object below, no explanations or additional text:
{{
    "sentiment_score": 0.0,
    "confidence": 0.0
}}

Sentiment score: -1.0 (very negative) to 1.0 (very positive)"""
            
            response = self.llm_manager.generate_response(prompt)
            
            # Extract JSON from response
            json_str = self._extract_json_from_response(response)
            result = json.loads(json_str)
            
            return {
                'score': result.get('sentiment_score', 0.0),
                'confidence': result.get('confidence', 0.5)
            }
            
        except Exception as e:
            print(f"LLM sentiment analysis error: {e}")
            return self._get_fallback_sentiment(title, summary)
    
    def _get_fallback_sentiment(self, title: str, summary: str) -> Dict[str, float]:
        """Fallback rule-based sentiment analysis"""
        
        positive_words = ['strong', 'growth', 'exceeded', 'innovative', 'expansion', 'improved', 'success']
        negative_words = ['decline', 'loss', 'weak', 'concern', 'risk', 'challenge', 'disappointing']
        
        text = f"{title} {summary}".lower()
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            score = min(0.8, 0.3 + (positive_count - negative_count) * 0.1)
        elif negative_count > positive_count:
            score = max(-0.8, -0.3 - (negative_count - positive_count) * 0.1)
        else:
            score = 0.0
        
        confidence = min(0.9, 0.5 + abs(positive_count - negative_count) * 0.1)
        
        return {'score': score, 'confidence': confidence}
    
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
    
    def _categorize_news(self, news: Dict) -> NewsCategory:
        """Categorize news item"""
        
        title_lower = news['title'].lower()
        summary_lower = news['summary'].lower()
        
        if any(word in title_lower for word in ['earnings', 'revenue', 'profit']):
            return NewsCategory.EARNINGS
        elif any(word in title_lower for word in ['product', 'launch', 'unveil']):
            return NewsCategory.PRODUCT_LAUNCH
        elif any(word in title_lower for word in ['ceo', 'management', 'executive']):
            return NewsCategory.MANAGEMENT_CHANGE
        elif any(word in title_lower for word in ['expansion', 'market', 'strategy']):
            return NewsCategory.MARKET_EXPANSION
        else:
            return NewsCategory.GENERAL
    
    def _determine_sentiment_rating(self, score: float) -> SentimentScore:
        """Convert numerical score to sentiment rating"""
        
        if score >= 0.6:
            return SentimentScore.VERY_POSITIVE
        elif score >= 0.2:
            return SentimentScore.POSITIVE
        elif score >= -0.2:
            return SentimentScore.NEUTRAL
        elif score >= -0.6:
            return SentimentScore.NEGATIVE
        else:
            return SentimentScore.VERY_NEGATIVE
    
    def _calculate_sentiment_trends(self, news_items: List[NewsItem]) -> List[SentimentTrend]:
        """Calculate sentiment trends over different periods"""
        
        trends = []
        
        # 7-day trend
        recent_7d = [item for item in news_items if self._is_within_days(item.date, 7)]
        if recent_7d:
            avg_sentiment = sum(item.sentiment_score for item in recent_7d) / len(recent_7d)
            trends.append(SentimentTrend(
                period="7d",
                average_sentiment=avg_sentiment,
                sentiment_direction="Improving" if avg_sentiment > 0.1 else "Stable" if avg_sentiment > -0.1 else "Declining",
                news_volume=len(recent_7d)
            ))
        
        # 30-day trend
        recent_30d = [item for item in news_items if self._is_within_days(item.date, 30)]
        if recent_30d:
            avg_sentiment = sum(item.sentiment_score for item in recent_30d) / len(recent_30d)
            trends.append(SentimentTrend(
                period="30d",
                average_sentiment=avg_sentiment,
                sentiment_direction="Improving" if avg_sentiment > 0.1 else "Stable" if avg_sentiment > -0.1 else "Declining",
                news_volume=len(recent_30d)
            ))
        
        return trends
    
    def _is_within_days(self, date_str: str, days: int) -> bool:
        """Check if date is within specified days"""
        try:
            news_date = datetime.strptime(date_str, '%Y-%m-%d')
            cutoff_date = datetime.now() - timedelta(days=days)
            return news_date >= cutoff_date
        except:
            return False
    
    def _generate_sentiment_insights(self, news_items: List[NewsItem], 
                                   overall_sentiment: float) -> tuple:
        """Generate sentiment insights"""
        
        key_developments = []
        sentiment_drivers = []
        risk_factors = []
        
        # Analyze by category
        earnings_news = [item for item in news_items if item.category == NewsCategory.EARNINGS]
        product_news = [item for item in news_items if item.category == NewsCategory.PRODUCT_LAUNCH]
        management_news = [item for item in news_items if item.category == NewsCategory.MANAGEMENT_CHANGE]
        
        # Key developments
        if earnings_news:
            avg_earnings_sentiment = sum(item.sentiment_score for item in earnings_news) / len(earnings_news)
            if avg_earnings_sentiment > 0.3:
                key_developments.append("Strong earnings performance driving positive sentiment")
            elif avg_earnings_sentiment < -0.3:
                key_developments.append("Earnings concerns impacting market sentiment")
        
        if product_news:
            key_developments.append("New product launches generating market interest")
        
        if management_news:
            key_developments.append("Management communications providing strategic clarity")
        
        # Sentiment drivers
        positive_news = [item for item in news_items if item.sentiment_score > 0.2]
        if positive_news:
            sentiment_drivers.append(f"Positive coverage in {len(positive_news)} recent news items")
        
        # Risk factors
        negative_news = [item for item in news_items if item.sentiment_score < -0.2]
        if negative_news:
            risk_factors.append(f"Negative sentiment in {len(negative_news)} recent news items")
        
        if overall_sentiment < -0.3:
            risk_factors.append("Overall negative news sentiment may impact stock performance")
        
        return key_developments, sentiment_drivers, risk_factors
    
    def _generate_overall_summary(self, report: NewsSentimentReport) -> List[str]:
        """Generate overall summary of news sentiment analysis"""
        try:
            # Prepare news titles and sentiment info for LLM
            news_info = []
            for item in report.recent_news[:5]:  # Top 5 news items
                news_info.append(f"Title: {item.title} (Sentiment: {item.sentiment_score:.2f})")
            
            news_text = "\n".join(news_info)
            
            prompt = f"""Analyze these recent news articles and provide a 3-4 bullet point summary explaining the overall sentiment score of {report.overall_sentiment_score:.2f}:

{news_text}

Provide ONLY a JSON array of bullet points:
[
    "Bullet point 1 explaining key positive/negative factors",
    "Bullet point 2 about market reactions or developments",
    "Bullet point 3 about future outlook or concerns"
]"""
            
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            summary_points = json.loads(json_str)
            
            if isinstance(summary_points, list):
                return summary_points
            else:
                return self._generate_fallback_summary(report)
                
        except Exception as e:
            print(f"Summary generation error: {e}")
            return self._generate_fallback_summary(report)
    
    def _generate_fallback_summary(self, report: NewsSentimentReport) -> List[str]:
        """Generate fallback summary when LLM fails"""
        summary = []
        
        # Sentiment assessment
        if report.overall_sentiment_score > 0.3:
            summary.append(f"Strong positive sentiment ({report.overall_sentiment_score:.2f}) driven by favorable news coverage")
        elif report.overall_sentiment_score > 0.1:
            summary.append(f"Moderately positive sentiment ({report.overall_sentiment_score:.2f}) with mixed but generally favorable news")
        elif report.overall_sentiment_score > -0.1:
            summary.append(f"Neutral sentiment ({report.overall_sentiment_score:.2f}) with balanced positive and negative coverage")
        elif report.overall_sentiment_score > -0.3:
            summary.append(f"Moderately negative sentiment ({report.overall_sentiment_score:.2f}) with concerning news developments")
        else:
            summary.append(f"Strongly negative sentiment ({report.overall_sentiment_score:.2f}) due to adverse news coverage")
        
        # News volume assessment
        news_count = len(report.recent_news)
        if news_count > 5:
            summary.append(f"High news volume ({news_count} articles) indicating significant market attention")
        elif news_count > 2:
            summary.append(f"Moderate news coverage ({news_count} articles) providing market insights")
        else:
            summary.append(f"Limited news coverage ({news_count} articles) with focused market attention")
        
        # Key developments
        if report.key_developments:
            summary.append(f"Key developments include: {', '.join(report.key_developments[:2])}")
        
        return summary[:4]  # Limit to 4 bullet points
    
    def _generate_recommendation(self, report: NewsSentimentReport) -> str:
        """Generate recommendation based on news sentiment"""
        
        if report.overall_sentiment_score >= 0.4:
            return "Buy"
        elif report.overall_sentiment_score >= 0.1:
            return "Hold"
        elif report.overall_sentiment_score >= -0.2:
            return "Hold"
        else:
            return "Sell"
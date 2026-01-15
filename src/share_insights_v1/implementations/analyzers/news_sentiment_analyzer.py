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
from ...utils.prompt_formatter import PromptFormatter
from ...utils.debug_printer import debug_print

class NewsSentimentAnalyzer(IAnalyzer):
    """Enhanced news sentiment analyzer with recent developments tracking"""
    
    def __init__(self, data_provider: IDataProvider, llm_manager=None, debug_mode: bool = False, enable_web_scraping: bool = True, max_articles: int = 5):
        self.data_provider = data_provider
        self.llm_manager = llm_manager or LLMManager()
        self.debug_mode = debug_mode
        self.enable_web_scraping = enable_web_scraping
        self.max_articles = max_articles
    
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
            
            # Debug: debug_print what enhanced facts are being returned
            recent_news_with_facts = [{
                'title': item.title,
                'summary': item.summary,
                'date': item.date,
                'source': item.source,
                'url': getattr(item, 'url', ''),
                'sentiment': getattr(item, 'sentiment', 'neutral'),
                'sentiment_score': item.sentiment_score,
                'enhanced_facts': getattr(item, 'enhanced_facts', None)
            } for item in report.recent_news]
            
            # Debug logging
            for news_item in recent_news_with_facts:
                if news_item['enhanced_facts']:
                    debug_print(f"✅ DEBUG: News item '{news_item['title'][:30]}...' has enhanced facts: {news_item['enhanced_facts']}")
                else:
                    debug_print(f"❌ DEBUG: News item '{news_item['title'][:30]}...' has NO enhanced facts")
            
            return {
                'method': 'News Sentiment Analysis',
                'applicable': True,
                'overall_sentiment_score': report.overall_sentiment_score,
                'sentiment_rating': report.sentiment_rating.value,
                'news_count': len(report.recent_news),
                'recent_news': recent_news_with_facts,
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
        """News sentiment analysis applies to all company types including ETFs"""
        return True
    
    def _get_recent_news(self, ticker: str, company_info: Dict[str, Any]) -> Optional[List[Dict]]:
        """Get recent news using yfinance"""
        
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            
            # Get news from yfinance
            news_data = stock.news
            
            if not news_data:
                debug_print(f"No news found for {ticker}")
                return None
            

            
            processed_news = []
            # Limit to configured number of articles for processing
            for news_item in news_data[:self.max_articles]:
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
                
                # Try to get full article content only if web scraping is enabled
                full_content = None
                if self.enable_web_scraping and url:
                    full_content = self._fetch_article_content(url)
                    if self.debug_mode and full_content and 'keep an eye on' in content.get('title', '').lower():
                        debug_print(f"DEBUG: Scraped {len(full_content)} chars for '{content.get('title', '')[:50]}...'")
                
                processed_news.append({
                    'title': content.get('title', 'No title'),
                    'summary': full_content or content.get('summary', content.get('description', 'No summary')),
                    'date': news_date,
                    'source': source,
                    'url': url,
                    'category': 'general',
                    'sentiment': 'neutral'
                })
            
            return processed_news
            
        except Exception as e:
            debug_print(f"Error fetching news for {ticker}: {e}")
            import traceback
            traceback.debug_print_exc()
            return None
    
    def _fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch full article content from URL"""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Try common article selectors
                article_selectors = [
                    'article', '.article-body', '.story-body', '.post-content',
                    '.entry-content', '.content', 'main', '.article-content'
                ]
                
                for selector in article_selectors:
                    article = soup.select_one(selector)
                    if article:
                        text = article.get_text(strip=True)
                        if len(text) > 200:  # Ensure we got substantial content
                            if self.debug_mode:
                                debug_print(f"DEBUG: Found article content via selector '{selector}', length: {len(text)}")
                            return text[:3000]
                
                # Fallback: get all paragraph text
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    if text:
                        return text[:3000]
                    return None
                    
        except Exception as e:
            if self.debug_mode and ('keep an eye on' in url or 'research further' in url):
                debug_print(f"Error fetching article content from {url}: {e}")
        
        return None
    
    def _extract_ticker_relevant_content(self, text: str, ticker: str) -> str:
        """Extract content around ticker mentions, prioritizing ticker-relevant sections"""
        if not ticker:
            return text[:3000]
        
        ticker_lower = ticker.lower()
        text_lower = text.lower()
        
        # Find all ticker mentions
        ticker_positions = []
        start = 0
        while True:
            pos = text_lower.find(ticker_lower, start)
            if pos == -1:
                break
            ticker_positions.append(pos)
            start = pos + 1
        
        if not ticker_positions:
            # No ticker mentions found, return first 3000 chars
            return text[:3000]
        
        # Get content around first ticker mention (1500 chars before and after)
        first_mention = ticker_positions[0]
        start_pos = max(0, first_mention - 1500)
        end_pos = min(len(text), first_mention + 1500)
        
        relevant_content = text[start_pos:end_pos]
        
        # If we have multiple mentions, try to include more context
        if len(ticker_positions) > 1 and len(relevant_content) < 2500:
            # Extend to include second mention if space allows
            second_mention = ticker_positions[1]
            extended_end = min(len(text), second_mention + 500)
            if extended_end - start_pos <= 3000:
                relevant_content = text[start_pos:extended_end]
        
        return relevant_content[:3000]  # Ensure we don't exceed limit
    
    def _analyze_news_sentiment(self, ticker: str, news_data: List[Dict]) -> NewsSentimentReport:
        """Analyze sentiment from news data"""
        
        # Process news items
        news_items = []
        sentiment_scores = []
        
        for news in news_data:
            # Analyze sentiment using AI (or rule-based for demo)
            sentiment_result = self._analyze_text_sentiment(news['title'], news['summary'], ticker)
            
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
                sentiment=news.get('sentiment', 'neutral'),
                enhanced_facts=sentiment_result.get('enhanced_facts')  # Include enhanced facts directly in constructor
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
    
    def _analyze_text_sentiment(self, title: str, summary: str, ticker: str = None) -> Dict[str, float]:
        """Analyze stock-specific sentiment from text using enhanced fact extraction"""
        
        # Use enhanced fact extraction when web scraping is enabled
        if self.enable_web_scraping:
            try:
                # Get provider name for formatting
                provider_name = PromptFormatter.get_provider_name_from_llm_manager(self.llm_manager)
                
                if ticker:
                    # Enhanced fact extraction prompt
                    fact_extraction_prompt = f"""🎯 OBJECTIVE: Extract institutional-grade "Fact Blocks" from the following news article to feed into a financial modeling engine for {ticker}.

ARTICLE DATA:
Title: {title}
Content: {summary}
URL: Available in source data

FOR THIS ARTICLE:
1. **The Lead Fact**: What is the specific event? (e.g., $50M contract win, Q3 earnings beat of 5%, CEO departure).
2. **Quantitative Evidence**: Quote exact numbers, dollar amounts, or percentages from the article.
3. **The "Why it Matters" (Mechanism)**: How does this specifically change {ticker}'s business? (e.g., "Expands gross margin by reducing supply chain lag").
4. **Verbatim Quote**: One high-impact quote for attribution (if available in content).
5. **Sentiment Score**: Rate impact on {ticker} from -1.0 (very negative) to +1.0 (very positive).

🚫 RESTRAINT: Do not provide an "opinion" or "summary." Provide only raw, structured data blocks.

Return JSON:"""
                    
                    schema = {
                        "lead_fact": "Specific event description",
                        "quantitative_evidence": "Exact numbers/amounts from article",
                        "business_mechanism": "How this changes the business",
                        "verbatim_quote": "Direct quote from article (if available)",
                        "sentiment_score": 0.0,
                        "confidence": 0.8
                    }
                    
                    prompt = fact_extraction_prompt + "\n" + PromptFormatter._format_json_schema(schema)
                    prompt = PromptFormatter.format_json_prompt(prompt, provider_name)
                else:
                    # Generic sentiment analysis for non-ticker specific
                    base_prompt = f"""Analyze the sentiment of this financial news and respond with ONLY valid JSON:

Title: {title}
Summary: {summary}

Sentiment score: -1.0 (very negative) to 1.0 (very positive)"""
                    
                    schema = {
                        "sentiment_score": 0.0,
                        "confidence": 0.0
                    }
                    
                    prompt = base_prompt + "\n" + PromptFormatter._format_json_schema(schema)
                    prompt = PromptFormatter.format_json_prompt(prompt, provider_name)
                
                response = self.llm_manager.generate_response(prompt)
                json_str = self._extract_json_from_response(response)
                result = json.loads(json_str)
                
                score = result.get('sentiment_score', 0.0)
                
                # Debug: debug_print what we got from LLM
                if self.debug_mode or ticker:  # Always debug for ticker-specific analysis
                    debug_print(f"🔍 DEBUG: LLM response for '{title[:50]}...': {result}")
                
                # Store enhanced fact data for thesis generation
                if ticker and 'lead_fact' in result:
                    # Store structured facts in the news item for later use
                    enhanced_facts = {
                        'lead_fact': result.get('lead_fact', ''),
                        'quantitative_evidence': result.get('quantitative_evidence', ''),
                        'business_mechanism': result.get('business_mechanism', ''),
                        'verbatim_quote': result.get('verbatim_quote', '')
                    }
                    debug_print(f"✅ DEBUG: Enhanced facts extracted for '{title[:30]}...': {enhanced_facts}")
                    
                    return {
                        'score': score,
                        'confidence': result.get('confidence', 0.5),
                        'enhanced_facts': enhanced_facts  # Return the structured facts
                    }
                
                return {
                    'score': score,
                    'confidence': result.get('confidence', 0.5),
                    'enhanced_facts': result if ticker and 'lead_fact' in result else None
                }
                
            except Exception as e:
                if self.debug_mode:
                    debug_print(f"Enhanced sentiment analysis error for '{title[:30]}...': {e}")
                return self._get_fallback_sentiment(title, summary, ticker)
        
        # Fallback to rule-based when web scraping disabled
        return self._get_fallback_sentiment(title, summary, ticker)

    
    def _get_fallback_sentiment(self, title: str, summary: str, ticker: str = None) -> Dict[str, float]:
        """Fallback rule-based sentiment analysis with ticker-specific focus"""
        
        text = f"{title} {summary}".lower()
        
        if ticker:
            # Extract sentences mentioning the ticker
            import re
            sentences = re.split(r'[.!?]', text)
            ticker_sentences = [s for s in sentences if ticker.lower() in s]
            
            if ticker_sentences:
                text = ' '.join(ticker_sentences)
            else:
                # If no ticker mentions found but article is in ticker's feed,
                # assume neutral relevance and analyze full text with reduced confidence
                full_text = f"{title} {summary}".lower()
                return self._analyze_full_text_sentiment(full_text, reduced_confidence=True)
        
        positive_words = ['strong', 'growth', 'exceeded', 'innovative', 'expansion', 'improved', 'success', 'positive', 'attractive', 'undervalued', 'buy', 'keep an eye on', 'eye on', 'research further', 'promising', 'opportunity']
        negative_words = ['decline', 'loss', 'weak', 'concern', 'risk', 'challenge', 'disappointing', 'cautious', 'avoid', 'sell']
        
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
    
    def _analyze_full_text_sentiment(self, text: str, reduced_confidence: bool = False) -> Dict[str, float]:
        """Analyze full text sentiment when no specific ticker mentions found"""
        
        positive_words = ['strong', 'growth', 'exceeded', 'innovative', 'expansion', 'improved', 'success', 'positive', 'attractive', 'undervalued', 'buy', 'research further']
        negative_words = ['decline', 'loss', 'weak', 'concern', 'risk', 'challenge', 'disappointing', 'cautious', 'avoid', 'sell', 'brush off']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            score = min(0.4, 0.1 + (positive_count - negative_count) * 0.05)  # Reduced impact
        elif negative_count > positive_count:
            score = max(-0.4, -0.1 - (negative_count - positive_count) * 0.05)  # Reduced impact
        else:
            score = 0.0
        
        confidence = 0.2 if reduced_confidence else min(0.6, 0.3 + abs(positive_count - negative_count) * 0.05)
        
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
            # Get provider name for formatting
            provider_name = PromptFormatter.get_provider_name_from_llm_manager(self.llm_manager)
            
            # Prepare news titles and sentiment info for LLM
            news_info = []
            for item in report.recent_news[:5]:  # Top 5 news items
                news_info.append(f"Title: {item.title} (Sentiment: {item.sentiment_score:.2f})")
            
            news_text = "\n".join(news_info)
            
            # Create universal prompt
            base_prompt = f"""Analyze these recent news articles and provide a 3-4 bullet point summary explaining the overall sentiment score of {report.overall_sentiment_score:.2f}:

{news_text}

Provide ONLY a JSON array of bullet points:"""
            
            schema = [
                "Bullet point 1 explaining key positive/negative factors",
                "Bullet point 2 about market reactions or developments",
                "Bullet point 3 about future outlook or concerns"
            ]
            
            prompt = base_prompt + "\n" + json.dumps(schema, indent=2)
            prompt = PromptFormatter.format_json_prompt(prompt, provider_name)
            
            response = self.llm_manager.generate_response(prompt)
            json_str = self._extract_json_from_response(response)
            summary_points = json.loads(json_str)
            
            if isinstance(summary_points, list):
                return summary_points
            else:
                return self._generate_fallback_summary(report)
                
        except Exception as e:
            debug_print(f"Summary generation error: {e}")
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
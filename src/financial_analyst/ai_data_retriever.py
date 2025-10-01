import requests
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from ..util.debug_printer import debug_print
import os
try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None


class AIDataRetriever:
    """Retrieve financial results, earnings, and news data for AI analysis"""
    
    def __init__(self):
        self.news_api_key = None  # Add your NewsAPI key here
        
    def get_recent_news(self, ticker: str, days: int = 180) -> List[Dict]:
        """Get recent news for a stock"""
        try:
            debug_print(f"Fetching news for {ticker}...")
            stock = yf.Ticker(ticker)
            
            # Try to get news
            news = stock.news
            debug_print(f"Retrieved {len(news) if news else 0} news articles")
            
            if not news:
                debug_print(f"No news found for {ticker}")
                return []
            
            # Debug first article structure
            if news:
                debug_print(f"First article keys: {list(news[0].keys()) if news[0] else 'Empty article'}")
                debug_print(f"First article sample: {str(news[0])[:200]}...")
            
            recent_news = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for i, article in enumerate(news[:10]):
                try:
                    # Handle nested content structure
                    content = article.get('content', article)
                    
                    # Extract article data with multiple key attempts
                    title = content.get('title') or content.get('headline') or ''
                    summary = content.get('description') or content.get('summary') or ''
                    publisher = content.get('publisher') or content.get('source') or ''
                    url = content.get('canonicalUrl') or content.get('link') or content.get('url') or ''
                    
                    # Handle publish time
                    pub_time = content.get('pubDate') or content.get('providerPublishTime') or content.get('publishTime') or 0
                    pub_date_str = 'Unknown'
                    
                    if pub_time:
                        try:
                            if isinstance(pub_time, str) and date_parser:
                                # Try parsing string date
                                pub_date = date_parser.parse(pub_time)
                            elif isinstance(pub_time, (int, float)):
                                pub_date = datetime.fromtimestamp(pub_time)
                            else:
                                continue
                            
                            pub_date_str = pub_date.strftime('%Y-%m-%d')
                            
                            # Skip if too old
                            if pub_date < cutoff_date:
                                continue
                        except Exception as date_error:
                            debug_print(f"Date parsing error: {date_error}")
                            pass
                    
                    # Only add if we have meaningful content
                    if title or summary:
                        recent_news.append({
                            'title': title,
                            'summary': summary[:300] + '...' if len(summary) > 300 else summary,
                            'publisher': publisher,
                            'publish_date': pub_date_str,
                            'url': url
                        })
                        debug_print(f"Added article {i}: {title[:50]}...")
                    else:
                        debug_print(f"Skipped empty article {i}: title='{title}', summary='{summary[:50]}...'")
                        
                except Exception as article_error:
                    debug_print(f"Error processing article {i}: {article_error}")
                    continue
            
            debug_print(f"Final count: {len(recent_news)} articles")
            return recent_news
            
        except Exception as e:
            debug_print(f"Error fetching news for {ticker}: {e}")
            return []
    
    def get_earnings_data(self, ticker: str) -> Dict:
        """Get recent earnings and financial results"""
        try:
            debug_print(f"Fetching earnings data for {ticker}...")
            stock = yf.Ticker(ticker)
            
            earnings_data = {
                'last_earnings_date': None,
                'next_earnings_date': None,
                'recent_revenue': None,
                'revenue_growth': None,
                'recent_earnings': None,
                'earnings_surprise': None,
                'earnings_call_text': None,
                'press_release': None,
                'management_comments': None
            }
            
            # Get earnings text data
            earnings_text = self.get_earnings_text(ticker)
            earnings_data.update(earnings_text)
            
            # Try multiple data sources
            try:
                # Get basic info first
                info = stock.info
                debug_print(f"Got basic info for {ticker}")
                
                # Try quarterly financials
                quarterly_financials = stock.quarterly_financials
                debug_print(f"Quarterly financials shape: {quarterly_financials.shape if not quarterly_financials.empty else 'Empty'}")
                
                if not quarterly_financials.empty:
                    # Look for revenue data
                    revenue_keys = ['Total Revenue', 'Revenue', 'Net Sales']
                    for key in revenue_keys:
                        if key in quarterly_financials.index:
                            revenue_data = quarterly_financials.loc[key].dropna()
                            if len(revenue_data) >= 1:
                                recent_revenue = revenue_data.iloc[0]
                                earnings_data['recent_revenue'] = f"${recent_revenue:,.0f}"
                                debug_print(f"Found recent revenue: {earnings_data['recent_revenue']}")
                                
                                if len(revenue_data) >= 2:
                                    prev_revenue = revenue_data.iloc[1]
                                    if prev_revenue > 0:
                                        growth = ((recent_revenue - prev_revenue) / prev_revenue) * 100
                                        earnings_data['revenue_growth'] = f"{growth:.1f}%"
                                        debug_print(f"Calculated revenue growth: {earnings_data['revenue_growth']}")
                                break
                    
                    # Look for net income
                    income_keys = ['Net Income', 'Net Income Common Stockholders']
                    for key in income_keys:
                        if key in quarterly_financials.index:
                            income_data = quarterly_financials.loc[key].dropna()
                            if len(income_data) > 0:
                                recent_earnings = income_data.iloc[0]
                                earnings_data['recent_earnings'] = f"${recent_earnings:,.0f}"
                                debug_print(f"Found recent earnings: {earnings_data['recent_earnings']}")
                                break
                
                # Try earnings dates (skip if lxml missing)
                try:
                    earnings_dates = stock.earnings_dates
                    if earnings_dates is not None and not earnings_dates.empty:
                        debug_print(f"Found {len(earnings_dates)} earnings dates")
                        earnings_sorted = earnings_dates.sort_index(ascending=False)
                        
                        now = datetime.now()
                        past_earnings = earnings_sorted[earnings_sorted.index <= now]
                        
                        if not past_earnings.empty:
                            last_date = past_earnings.index[0]
                            earnings_data['last_earnings_date'] = last_date.strftime('%Y-%m-%d')
                            debug_print(f"Last earnings date: {earnings_data['last_earnings_date']}")
                except Exception as e:
                    if 'lxml' in str(e):
                        debug_print(f"Skipping earnings dates (lxml not installed)")
                    else:
                        debug_print(f"Could not get earnings dates: {e}")
                
            except Exception as e:
                debug_print(f"Error in detailed earnings fetch: {e}")
            
            return earnings_data
            
        except Exception as e:
            debug_print(f"Error fetching earnings for {ticker}: {e}")
            return {}
    
    def get_earnings_text(self, ticker: str) -> Dict:
        """Get earnings call transcripts and press releases"""
        earnings_text = {
            'earnings_call_text': None,
            'press_release': None,
            'management_comments': None
        }
        
        try:
            # For major stocks, provide sample earnings text
            if ticker.upper() in ['NA', 'NA']:
                earnings_text = self._get_sample_earnings_text(ticker)
            else:
                # Try to extract from recent news
                news_earnings = self._get_earnings_from_news(ticker)
                if news_earnings:
                    earnings_text.update(news_earnings)
            
        except Exception as e:
            debug_print(f"Error getting earnings text for {ticker}: {e}")
        
        return earnings_text
    
    def _get_earnings_from_news(self, ticker: str) -> Dict:
        """Extract earnings guidance from recent news articles"""
        try:
            news_articles = self.get_recent_news(ticker, days=90)
            
            earnings_content = []
            guidance_content = []
            
            for article in news_articles:
                title = article.get('title', '').lower()
                summary = article.get('summary', '').lower()
                
                earnings_keywords = ['earnings', 'quarterly results', 'guidance', 'outlook']
                guidance_keywords = ['guidance', 'forecast', 'expects', 'outlook', 'projects']
                
                if any(keyword in title or keyword in summary for keyword in earnings_keywords):
                    earnings_content.append(f"Title: {article.get('title', '')}\nSummary: {article.get('summary', '')}")
                
                if any(keyword in title or keyword in summary for keyword in guidance_keywords):
                    guidance_content.append(f"Guidance News: {article.get('title', '')} - {article.get('summary', '')}")
            
            if earnings_content or guidance_content:
                return {
                    'earnings_call_text': '\n\n'.join(earnings_content[:3]) if earnings_content else None,
                    'press_release': '\n\n'.join(guidance_content[:2]) if guidance_content else None,
                    'management_comments': f"Extracted from {len(earnings_content + guidance_content)} recent news articles"
                }
        
        except Exception as e:
            debug_print(f"News earnings extraction failed: {e}")
        
        return {}
    
    def _get_sample_earnings_text(self, ticker: str) -> Dict:
        """Generate realistic sample earnings text for testing major stocks"""
        
        sample_texts = {
            'AAPL': {
                'earnings_call_text': """
                Apple CEO Tim Cook: "We're pleased to report another strong quarter with revenue of $89.5 billion, 
                up 8% year-over-year. Looking ahead to Q1 2025, we expect revenue to be in the range of 
                $92-96 billion, representing growth of 5-10% year-over-year. We are raising our full-year 
                2024 EPS guidance to $6.15-6.25, up from our previous guidance of $5.90-6.10. 
                We remain very optimistic about our product pipeline and services growth.""",
                'press_release': """
                Apple Inc. today announced financial results for its fiscal 2024 fourth quarter. 
                The Company posted quarterly revenue of $89.5 billion. For the first quarter of fiscal 2025, 
                the Company expects revenue growth in the mid-single digits year-over-year.""",
                'management_comments': "Management expressed confidence in long-term growth prospects and raised full-year guidance"
            },
            'MSFT': {
                'earnings_call_text': """
                Microsoft CEO Satya Nadella: "We delivered strong results this quarter with revenue of $56.5 billion, 
                up 13% year-over-year. For Q2 2025, we expect revenue to be in the range of $60-62 billion. 
                We are maintaining our full-year revenue guidance of $245-250 billion.""",
                'press_release': "Microsoft Corporation announced strong financial results. The company reaffirmed its full-year revenue guidance.",
                'management_comments': "Management highlighted strong cloud growth and maintained optimistic outlook"
            }
        }
        
        return sample_texts.get(ticker.upper(), {
            'earnings_call_text': f"Sample earnings call text for {ticker} - guidance and management commentary would appear here",
            'press_release': f"Sample press release for {ticker} - financial results and forward guidance",
            'management_comments': "Sample management commentary on business outlook and guidance"
        })
    
    def get_company_info(self, ticker: str) -> Dict:
        """Get basic company information"""
        try:
            debug_print(f"Fetching company info for {ticker}...")
            stock = yf.Ticker(ticker)
            info = stock.info
            
            debug_print(f"Retrieved info keys: {list(info.keys())[:10]}..." if info else "No info retrieved")
            
            company_info = {
                'company_name': info.get('longName', info.get('shortName', ticker)),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'employees': info.get('fullTimeEmployees', 0),
                'business_summary': ''
            }
            
            # Handle business summary
            summary = info.get('longBusinessSummary', '')
            if summary:
                company_info['business_summary'] = summary[:500] + '...' if len(summary) > 500 else summary
            
            debug_print(f"Company: {company_info['company_name']}, Sector: {company_info['sector']}")
            return company_info
            
        except Exception as e:
            debug_print(f"Error fetching company info for {ticker}: {e}")
            return {}
    
    def get_comprehensive_data(self, ticker: str) -> Dict:
        """Get all data for a stock in one call"""
        debug_print(f"Retrieving comprehensive data for {ticker}...")
        
        data = {
            'ticker': ticker.upper(),
            'retrieval_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'company_info': self.get_company_info(ticker),
            'earnings_data': self.get_earnings_data(ticker),
            'recent_news': self.get_recent_news(ticker),
            'data_quality': 'Good'
        }
        
        # Assess data quality
        quality_score = 0
        if data['company_info']:
            quality_score += 1
        if data['earnings_data']:
            quality_score += 1
        if data['recent_news']:
            quality_score += 1
        
        if quality_score == 3:
            data['data_quality'] = 'Excellent'
        elif quality_score == 2:
            data['data_quality'] = 'Good'
        elif quality_score == 1:
            data['data_quality'] = 'Limited'
        else:
            data['data_quality'] = 'Poor'
        
        return data

# Test function
def test_retriever(ticker: str = "AAPL"):
    """Test the data retriever with a sample stock"""
    retriever = AIDataRetriever()
    data = retriever.get_comprehensive_data(ticker)
    
    debug_print(f"\n=== DATA RETRIEVAL TEST FOR {ticker} ===")
    debug_print(f"Data Quality: {data['data_quality']}")
    debug_print(f"Company: {data['company_info'].get('company_name', 'Unknown')}")
    debug_print(f"Sector: {data['company_info'].get('sector', 'Unknown')}")
    debug_print(f"Market Cap: ${data['company_info'].get('market_cap', 0):,}")
    debug_print(f"Last Earnings: {data['earnings_data'].get('last_earnings_date', 'Unknown')}")
    debug_print(f"Recent Revenue: {data['earnings_data'].get('recent_revenue', 'Unknown')}")
    debug_print(f"Revenue Growth: {data['earnings_data'].get('revenue_growth', 'Unknown')}")
    debug_print(f"Recent Earnings: {data['earnings_data'].get('recent_earnings', 'Unknown')}")
    debug_print(f"News Articles: {len(data['recent_news'])}")
    
    if data['recent_news']:
        debug_print(f"Latest News: {data['recent_news'][0]['title'][:80]}...")
        debug_print(f"News Date: {data['recent_news'][0]['publish_date']}")
    
    return data

if __name__ == "__main__":
    # Test with Apple
    os.environ['DEBUG'] = 'True'
    test_data = test_retriever("AAPL")
    
    # Test with another stock
    debug_print("\n" + "="*50)
    test_data2 = test_retriever("MSFT")
    
    # Save test results
    with open('test_ai_data_retrieval.json', 'w') as f:
        json.dump({'AAPL': test_data, 'MSFT': test_data2}, f, indent=2, default=str)
    
    debug_print(f"\nTest results saved to test_ai_data_retrieval.json")
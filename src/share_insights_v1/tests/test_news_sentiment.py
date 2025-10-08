#!/usr/bin/env python3

from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
from ..implementations.analyzers.news_sentiment_analyzer import NewsSentimentAnalyzer
from ..implementations.classifier import CompanyClassifier

def test_news_sentiment_analysis():
    """Test enhanced news sentiment analysis"""
    
    print("Testing News Sentiment Analysis...")
    
    # Initialize providers
    data_provider = YahooFinanceProvider()
    analyzer = NewsSentimentAnalyzer(data_provider)
    
    # Test companies with different news profiles
    test_cases = [
        ("MSFT", "Large Tech - Stable News Flow"),
        ("TSLA", "Growth Tech - High News Volume"),
        ("AAPL", "Consumer Tech - Product Focus"),
        ("JPM", "Financial Services - Earnings Focus"),
        ("NFLX", "Entertainment - Content Strategy")
    ]
    
    for ticker, description in test_cases:
        print(f"\n{'='*60}")
        print(f"News Sentiment Analysis: {ticker} ({description})")
        print(f"{'='*60}")
        
        try:
            # Get company data for context
            financial_data = data_provider.get_financial_metrics(ticker=ticker)
            company_info = {
                'sector': financial_data.get('sector', ''),
                'industry': financial_data.get('industry', ''),
                'long_name': financial_data.get('long_name', ticker)
            }
            company_classifier = CompanyClassifier()
            company_type = company_classifier.classify(ticker=ticker, metrics=financial_data)
            
            if not financial_data:
                print(f"[ERROR] Could not get financial data for {ticker}")
                continue
            
            # Prepare analysis data
            analysis_data = {
                'financial_metrics': financial_data,
                'company_info': company_info,
                'company_type': company_type
            }
            
            # Run analysis
            result = analyzer.analyze(ticker, analysis_data)
            
            if 'error' in result:
                print(f"[ERROR] Error: {result['error']}")
                continue
            
            print(f"[SUCCESS] Analysis completed for {ticker}")
            print(f"Overall Sentiment Score: {result.get('overall_sentiment_score', 0):.2f} (-1 to 1)")
            print(f"Sentiment Rating: {result.get('sentiment_rating', 'N/A')}")
            print(f"News Items Analyzed: {result.get('news_count', 0)}")
            print(f"Recommendation: {result.get('recommendation', 'N/A')}")
            print(f"Overall Summary: {result.get('overall_summary','N/A')}")
            # Show key developments
            if result.get('key_developments'):
                print(f"\nKey Developments:")
                for development in result['key_developments']:
                    print(f"  • {development}")
            
            # Show sentiment drivers
            if result.get('sentiment_drivers'):
                print(f"\nSentiment Drivers:")
                for driver in result['sentiment_drivers']:
                    print(f"  + {driver}")
            
            # Show risk factors
            if result.get('risk_factors'):
                print(f"\nRisk Factors:")
                for risk in result['risk_factors']:
                    print(f"  - {risk}")
            
            # Show recent news with links
            if result.get('recent_news'):
                print(f"\nRecent News ({len(result['recent_news'])} articles):")
                for i, news in enumerate(result['recent_news'][:5], 1):  # Show top 5
                    print(f"  {i}. {news.get('title', 'No title')[:80]}...")
                    print(f"     Source: {news.get('source', 'Unknown')} | Date: {news.get('date', 'N/A')}")
                    print(f"     URL: {news.get('url', 'No URL')}")
                    print(f"     Sentiment: {news.get('sentiment_score', 0):.2f}")
                    print()
            
        except Exception as e:
            print(f"[ERROR] Error analyzing {ticker}: {e}")

if __name__ == "__main__":
    test_news_sentiment_analysis()
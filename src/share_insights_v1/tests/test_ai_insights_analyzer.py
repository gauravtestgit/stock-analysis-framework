#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider
import json

def test_ai_insights_analyzer():
    """Test the AI insights analyzer"""
    
    # Initialize components
    data_provider = YahooFinanceProvider()
    ai_analyzer = AIInsightsAnalyzer(data_provider)
    
    # Test with different tickers
    test_tickers = ['AAPL', 'TSLA', 'MSFT']
    
    results = {}
    
    for ticker in test_tickers:
        print(f"\nTesting AI insights analysis for {ticker}...")
        
        # Get financial data first
        financial_metrics = data_provider.get_financial_metrics(ticker)
        
        if 'error' in financial_metrics:
            print(f"Error getting financial data: {financial_metrics['error']}")
            continue
        
        # Prepare analysis data
        analysis_data = {
            'financial_metrics': financial_metrics,
            'company_info': {
                'sector': financial_metrics.get('sector', ''),
                'industry': financial_metrics.get('industry', ''),
            },
            'current_price': financial_metrics.get('current_price', 0),
            'quality_grade': 'B'  # Mock quality grade
        }
        
        # Run AI insights analysis
        result = ai_analyzer.analyze(ticker, analysis_data)
        
        if 'error' not in result:
            print(f"AI Recommendation: {result.get('recommendation', 'N/A')}")
            print(f"Confidence: {result.get('confidence', 'N/A')}")
            print(f"Target Price: ${result.get('predicted_price', 0):.2f}")
            
            # Print AI insights
            ai_insights = result.get('ai_insights', {})
            print(f"Market Position: {ai_insights.get('market_position', 'N/A')}")
            print(f"Growth Prospects: {ai_insights.get('growth_prospects', 'N/A')}")
            
            # Print news sentiment
            news_sentiment = result.get('news_sentiment', {})
            print(f"News Sentiment: {news_sentiment.get('overall_sentiment', 'N/A')}")
            print(f"Sentiment Score: {news_sentiment.get('sentiment_score', 0):.2f}")
            
            # Print revenue trends
            revenue_trends = result.get('revenue_trends', {})
            print(f"Revenue Trend: {revenue_trends.get('trend_assessment', 'N/A')}")
            print(f"Future Outlook: {revenue_trends.get('future_outlook', 'N/A')}")
            
            # Print risk factors
            risk_factors = result.get('risk_factors', [])
            if risk_factors:
                print(f"Risk Factors: {', '.join(risk_factors)}")
            
            results[ticker] = result
        else:
            print(f"Error: {result['error']}")
    
    # Save results
    with open('ai_insights_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nAI insights analysis test completed. Results saved to ai_insights_results.json")

if __name__ == "__main__":
    test_ai_insights_analyzer()
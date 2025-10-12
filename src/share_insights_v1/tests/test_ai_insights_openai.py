#!/usr/bin/env python3

import sys
import os
# sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ..implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
from ..implementations.llm_providers.llm_manager import LLMManager
from ..implementations.llm_providers.openai_provider import OpenAIProvider
from ..implementations.data_providers.yahoo_provider import YahooFinanceProvider

def test_ai_insights_with_openai():
    """Test AI insights analyzer with OpenAI as primary provider"""
    
    # Initialize LLM manager and register OpenAI
    llm_manager = LLMManager()
    llm_manager.register_provider(OpenAIProvider())
    
    # Set OpenAI as primary provider
    llm_manager.set_primary_provider("OpenAI")
    
    print(f"Primary provider: {llm_manager.get_primary_provider().get_provider_name()}")
    print(f"Available providers: {llm_manager.get_available_providers()}")
    
    # Initialize AI insights analyzer (it creates its own LLM manager)
    # We'll need to pass a mock data provider
    data_provider = YahooFinanceProvider()    
    
    analyzer = AIInsightsAnalyzer(data_provider=data_provider)
    
    # Replace the analyzer's LLM manager with our configured one
    analyzer.llm_manager = llm_manager
    
    
    # Test with AAPL
    ticker = "AAPL"
    print(f"\n=== Testing AI Insights for {ticker} with OpenAI ===")
    
    # Mock financial metrics
    financial_metrics = data_provider.get_financial_metrics(ticker)
    analysis_data = {
            'financial_metrics': financial_metrics,
            'company_info': {
                'sector': financial_metrics.get('sector', ''),
                'industry': financial_metrics.get('industry', ''),
            },
            'current_price': financial_metrics.get('current_price', 0),
            'quality_grade': 'B'  # Mock quality grade
        }
    try:
        result = analyzer.analyze(ticker, analysis_data)
        
        print(f"\nAnalysis Result:")
        print(f"Recommendation: {result.get('recommendation')}")
        print(f"Predicted Price: ${result.get('predicted_price', 0):.2f}")
        print(f"Confidence: {result.get('confidence')}")
        
        ai_insights = result.get('ai_insights', {})
        print(f"\nAI Insights:")
        print(f"Market Position: {ai_insights.get('market_position')}")
        print(f"Growth Prospects: {ai_insights.get('growth_prospects')}")
        print(f"Competitive Advantage: {ai_insights.get('competitive_advantage')}")
        
        strengths = ai_insights.get('key_strengths', [])
        if strengths:
            print(f"\nKey Strengths:")
            for strength in strengths:
                print(f"• {strength}")
        
        risks = ai_insights.get('key_risks', [])
        if risks:
            print(f"\nKey Risks:")
            for risk in risks:
                print(f"• {risk}")
        
        print(f"\n✅ AI Insights analysis completed successfully with OpenAI!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_insights_with_openai()
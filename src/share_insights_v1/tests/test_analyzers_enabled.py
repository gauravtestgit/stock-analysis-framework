#!/usr/bin/env python3

"""
Quick test to verify AI_INSIGHTS and NEWS_SENTIMENT analyzers are enabled by default
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.share_insights_v1.api.service import AnalysisService
from src.share_insights_v1.services.batch.batch_analysis_service import BatchAnalysisService
from src.share_insights_v1.models.analysis_result import AnalysisType

def test_api_service_analyzers():
    """Test that API service has AI_INSIGHTS and NEWS_SENTIMENT enabled"""
    print("🔍 Testing API Service Analyzers...")
    
    service = AnalysisService(save_to_db=False, debug_mode=True)
    orchestrator = service._setup_orchestrator()
    
    registered_analyzers = list(orchestrator.analyzers.keys())
    analyzer_names = [analyzer.value for analyzer in registered_analyzers]
    
    print(f"📊 API Service registered analyzers: {analyzer_names}")
    
    # Check for key analyzers
    has_ai_insights = AnalysisType.AI_INSIGHTS in registered_analyzers
    has_news_sentiment = AnalysisType.NEWS_SENTIMENT in registered_analyzers
    
    print(f"✅ AI_INSIGHTS enabled: {has_ai_insights}")
    print(f"✅ NEWS_SENTIMENT enabled: {has_news_sentiment}")
    
    return has_ai_insights and has_news_sentiment

def test_batch_service_analyzers():
    """Test that Batch service has AI_INSIGHTS and NEWS_SENTIMENT enabled"""
    print("\n🔍 Testing Batch Service Analyzers...")
    
    service = BatchAnalysisService(save_to_db=False)
    
    registered_analyzers = list(service.orchestrator.analyzers.keys())
    analyzer_names = [analyzer.value for analyzer in registered_analyzers]
    
    print(f"📊 Batch Service registered analyzers: {analyzer_names}")
    
    # Check for key analyzers
    has_ai_insights = AnalysisType.AI_INSIGHTS in registered_analyzers
    has_news_sentiment = AnalysisType.NEWS_SENTIMENT in registered_analyzers
    
    print(f"✅ AI_INSIGHTS enabled: {has_ai_insights}")
    print(f"✅ NEWS_SENTIMENT enabled: {has_news_sentiment}")
    
    return has_ai_insights and has_news_sentiment

def test_single_analysis():
    """Test running a single analysis to verify analyzers work"""
    print("\n🧪 Testing Single Stock Analysis...")
    
    try:
        service = AnalysisService(save_to_db=False, debug_mode=True)
        orchestrator = service._setup_orchestrator()
        
        # Test with a simple ticker
        result = orchestrator.analyze_stock("AAPL")
        
        if 'error' in result:
            print(f"❌ Analysis failed: {result['error']}")
            return False
        
        analyses = result.get('analyses', {})
        print(f"📈 Analysis completed for AAPL with {len(analyses)} methods")
        
        # Check if AI_INSIGHTS and NEWS_SENTIMENT ran
        ai_insights_ran = 'ai_insights' in analyses
        news_sentiment_ran = 'news_sentiment' in analyses
        
        print(f"🤖 AI_INSIGHTS analysis ran: {ai_insights_ran}")
        print(f"📰 NEWS_SENTIMENT analysis ran: {news_sentiment_ran}")
        
        if ai_insights_ran:
            ai_result = analyses['ai_insights']
            print(f"   AI_INSIGHTS result: {ai_result.get('recommendation', 'N/A')} (confidence: {ai_result.get('confidence', 'N/A')})")
        
        if news_sentiment_ran:
            news_result = analyses['news_sentiment']
            print(f"   NEWS_SENTIMENT result: {news_result.get('recommendation', 'N/A')} (confidence: {news_result.get('confidence', 'N/A')})")
        
        return ai_insights_ran and news_sentiment_ran
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Analyzer Enablement in Backend Services")
    print("=" * 60)
    
    # Test analyzer registration
    api_ok = test_api_service_analyzers()
    batch_ok = test_batch_service_analyzers()
    
    # Test actual analysis
    analysis_ok = test_single_analysis()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print(f"   API Service Analyzers: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"   Batch Service Analyzers: {'✅ PASS' if batch_ok else '❌ FAIL'}")
    print(f"   Single Analysis Test: {'✅ PASS' if analysis_ok else '❌ FAIL'}")
    
    if api_ok and batch_ok and analysis_ok:
        print("\n🎉 ALL TESTS PASSED - AI_INSIGHTS and NEWS_SENTIMENT are enabled by default!")
    else:
        print("\n⚠️  Some tests failed - check the output above for details")
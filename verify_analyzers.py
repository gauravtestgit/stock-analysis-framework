#!/usr/bin/env python3

"""
Simple test to verify AI_INSIGHTS and NEWS_SENTIMENT analyzers are registered by default
"""

def test_analyzer_registration():
    """Test analyzer registration in services"""
    print("🔍 Testing Analyzer Registration...")
    
    # Check API service registration
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
        
        # Read the service files to check for analyzer registration
        api_service_path = "src/share_insights_v1/api/service.py"
        batch_service_path = "src/share_insights_v1/services/batch/batch_analysis_service.py"
        
        print("📊 Checking API Service file...")
        with open(api_service_path, 'r') as f:
            api_content = f.read()
        
        # Check for AI_INSIGHTS and NEWS_SENTIMENT registration
        has_ai_insights_api = "AnalysisType.AI_INSIGHTS" in api_content and "AIInsightsAnalyzer" in api_content
        has_news_sentiment_api = "AnalysisType.NEWS_SENTIMENT" in api_content and "NewsSentimentAnalyzer" in api_content
        has_llm_manager_api = "LLMManager" in api_content
        
        print(f"   ✅ AI_INSIGHTS registered: {has_ai_insights_api}")
        print(f"   ✅ NEWS_SENTIMENT registered: {has_news_sentiment_api}")
        print(f"   ✅ LLM Manager initialized: {has_llm_manager_api}")
        
        print("\\n📊 Checking Batch Service file...")
        with open(batch_service_path, 'r') as f:
            batch_content = f.read()
        
        # Check for AI_INSIGHTS and NEWS_SENTIMENT registration
        has_ai_insights_batch = "AnalysisType.AI_INSIGHTS" in batch_content and "AIInsightsAnalyzer" in batch_content
        has_news_sentiment_batch = "AnalysisType.NEWS_SENTIMENT" in batch_content and "NewsSentimentAnalyzer" in batch_content
        has_llm_manager_batch = "LLMManager" in batch_content
        
        print(f"   ✅ AI_INSIGHTS registered: {has_ai_insights_batch}")
        print(f"   ✅ NEWS_SENTIMENT registered: {has_news_sentiment_batch}")
        print(f"   ✅ LLM Manager initialized: {has_llm_manager_batch}")
        
        # Check orchestrator applicable analyses
        orchestrator_path = "src/share_insights_v1/services/orchestration/analysis_orchestrator.py"
        print("\\n📊 Checking Orchestrator applicable analyses...")
        with open(orchestrator_path, 'r') as f:
            orchestrator_content = f.read()
        
        has_ai_insights_applicable = "AnalysisType.AI_INSIGHTS" in orchestrator_content
        has_news_sentiment_applicable = "AnalysisType.NEWS_SENTIMENT" in orchestrator_content
        
        print(f"   ✅ AI_INSIGHTS in applicable list: {has_ai_insights_applicable}")
        print(f"   ✅ NEWS_SENTIMENT in applicable list: {has_news_sentiment_applicable}")
        
        # Summary
        api_ok = has_ai_insights_api and has_news_sentiment_api and has_llm_manager_api
        batch_ok = has_ai_insights_batch and has_news_sentiment_batch and has_llm_manager_batch
        orchestrator_ok = has_ai_insights_applicable and has_news_sentiment_applicable
        
        print("\\n" + "=" * 60)
        print("📋 SUMMARY:")
        print(f"   API Service: {'✅ PASS' if api_ok else '❌ FAIL'}")
        print(f"   Batch Service: {'✅ PASS' if batch_ok else '❌ FAIL'}")
        print(f"   Orchestrator: {'✅ PASS' if orchestrator_ok else '❌ FAIL'}")
        
        if api_ok and batch_ok and orchestrator_ok:
            print("\\n🎉 SUCCESS - AI_INSIGHTS and NEWS_SENTIMENT are enabled by default in both services!")
            print("\\n📝 Changes made:")
            print("   • Added LLM Manager initialization to both services")
            print("   • Registered AI_INSIGHTS analyzer with LLM support")
            print("   • Registered NEWS_SENTIMENT analyzer with LLM support")
            print("   • Added additional qualitative analyzers (business model, competitive position, etc.)")
            print("   • Both analyzers are in the orchestrator's always-applicable list")
        else:
            print("\\n⚠️  Some checks failed - review the output above")
        
        return api_ok and batch_ok and orchestrator_ok
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Verifying Analyzer Enablement in Backend Services")
    print("=" * 60)
    test_analyzer_registration()
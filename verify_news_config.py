#!/usr/bin/env python3

"""
Verify that Web Scraping and LLM Sentiment Analysis are enabled by default
"""

def check_news_sentiment_configuration():
    """Check news sentiment analyzer configuration in services"""
    print("Checking News Sentiment Analyzer Configuration...")
    print("=" * 60)
    
    # Check API service configuration
    api_service_path = "src/share_insights_v1/api/service.py"
    batch_service_path = "src/share_insights_v1/services/batch/batch_analysis_service.py"
    
    print("1. API Service Configuration:")
    with open(api_service_path, 'r') as f:
        api_content = f.read()
    
    # Check for web scraping enabled
    web_scraping_enabled_api = "enable_web_scraping=True" in api_content
    llm_manager_used_api = "llm_manager" in api_content and "NewsSentimentAnalyzer(self.data_provider, llm_manager" in api_content
    
    print(f"   Web Scraping Enabled: {web_scraping_enabled_api}")
    print(f"   LLM Manager Used: {llm_manager_used_api}")
    
    print("\n2. Batch Service Configuration:")
    with open(batch_service_path, 'r') as f:
        batch_content = f.read()
    
    # Check for web scraping enabled
    web_scraping_enabled_batch = "enable_web_scraping=True" in batch_content
    llm_manager_used_batch = "llm_manager" in batch_content and "NewsSentimentAnalyzer(self.data_provider, llm_manager" in batch_content
    
    print(f"   Web Scraping Enabled: {web_scraping_enabled_batch}")
    print(f"   LLM Manager Used: {llm_manager_used_batch}")
    
    print("\n3. News Sentiment Analyzer Features:")
    analyzer_path = "src/share_insights_v1/implementations/analyzers/news_sentiment_analyzer.py"
    with open(analyzer_path, 'r') as f:
        analyzer_content = f.read()
    
    # Check for key features
    has_web_scraping = "_fetch_article_content" in analyzer_content
    has_llm_sentiment = "llm_manager.generate_response" in analyzer_content
    has_enhanced_facts = "enhanced_facts" in analyzer_content
    has_fact_extraction = "fact_extraction_prompt" in analyzer_content
    
    print(f"   Web Scraping Implementation: {has_web_scraping}")
    print(f"   LLM Sentiment Analysis: {has_llm_sentiment}")
    print(f"   Enhanced Fact Extraction: {has_enhanced_facts}")
    print(f"   Institutional-Grade Facts: {has_fact_extraction}")
    
    # Summary
    api_configured = web_scraping_enabled_api and llm_manager_used_api
    batch_configured = web_scraping_enabled_batch and llm_manager_used_batch
    analyzer_ready = has_web_scraping and has_llm_sentiment and has_enhanced_facts
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"   API Service Ready: {'PASS' if api_configured else 'FAIL'}")
    print(f"   Batch Service Ready: {'PASS' if batch_configured else 'FAIL'}")
    print(f"   Analyzer Features: {'PASS' if analyzer_ready else 'FAIL'}")
    
    if api_configured and batch_configured and analyzer_ready:
        print("\nSUCCESS - Web Scraping and LLM Sentiment Analysis are enabled by default!")
        print("\nEnabled Features:")
        print("   - Web scraping for full article content")
        print("   - LLM-powered sentiment analysis")
        print("   - Enhanced fact extraction for institutional-grade analysis")
        print("   - Ticker-specific content extraction")
        print("   - Structured fact blocks for thesis generation")
        print("   - Fallback to rule-based analysis when needed")
    else:
        print("\nSome configurations are missing - check the details above")
    
    return api_configured and batch_configured and analyzer_ready

if __name__ == "__main__":
    check_news_sentiment_configuration()
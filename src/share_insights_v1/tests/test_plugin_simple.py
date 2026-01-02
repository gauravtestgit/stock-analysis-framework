#!/usr/bin/env python3
"""Simple test to isolate plugin system issue"""

import sys
import os
sys.path.append('src')

def test_plugin_system():
    """Test plugin system initialization"""
    print("Testing Plugin System...")
    
    try:
        from src.share_insights_v1.implementations.llm_providers.plugin_manager import LLMPluginManager
        from src.share_insights_v1.implementations.llm_providers.llm_manager import LLMManager
        
        print("1. Creating LLMPluginManager...")
        plugin_manager = LLMPluginManager()
        print(f"   Plugin manager available: {plugin_manager.is_available()}")
        
        print("2. Creating LLMManager with plugin system...")
        llm_manager = LLMManager(use_plugin_system=True)
        print(f"   LLM manager created successfully")
        print(f"   Available providers: {llm_manager.get_available_providers()}")
        
        print("3. Testing AIInsightsAnalyzer...")
        from src.share_insights_v1.implementations.analyzers.ai_insights_analyzer import AIInsightsAnalyzer
        from src.share_insights_v1.implementations.data_providers.yahoo_provider import YahooFinanceProvider
        
        data_provider = YahooFinanceProvider()
        analyzer = AIInsightsAnalyzer(data_provider, llm_manager)
        print("   AIInsightsAnalyzer created successfully")
        
        print("✅ All tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_plugin_system()
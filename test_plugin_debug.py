#!/usr/bin/env python3
"""Debug test for plugin manager to check available providers and models"""

import sys
import os
sys.path.append('src')

def test_plugin_manager_debug():
    """Debug plugin manager provider creation"""
    print("🔍 Plugin Manager Debug Test")
    print("=" * 50)
    
    try:
        from src.share_insights_v1.implementations.llm_providers.plugin_manager import LLMPluginManager
        from src.share_insights_v1.implementations.llm_providers.llm_manager import LLMManager
        
        # Test plugin manager
        print("1. Creating LLMPluginManager...")
        plugin_manager = LLMPluginManager()
        print(f"   Available: {plugin_manager.is_available()}")
        
        # Check available providers
        print("\n2. Available providers:")
        providers = plugin_manager.get_available_providers()
        for provider in providers:
            print(f"   - {provider}")
        
        # Check available models for Groq
        print("\n3. Available models for 'groq':")
        groq_models = plugin_manager.get_available_models("groq")
        for model in groq_models:
            print(f"   - {model}")
        
        # Test creating default Groq provider
        print("\n4. Creating default Groq provider...")
        try:
            groq_default = plugin_manager.create_provider("groq")
            print(f"   Success: {groq_default.get_provider_name()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test creating Groq provider with specific model
        print("\n5. Creating Groq provider with openai/gpt-oss-20b...")
        try:
            groq_20b = plugin_manager.create_provider("groq", "openai/gpt-oss-20b")
            print(f"   Success: {groq_20b.get_provider_name()}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Test LLM Manager with plugin system
        print("\n6. Testing LLM Manager with plugin system...")
        try:
            llm_manager = LLMManager(use_plugin_system=True)
            print(f"   Available providers: {llm_manager.get_available_providers()}")
            
            # Try to register the new provider
            if 'groq_20b' in locals():
                print("\n7. Registering new Groq 20B provider...")
                llm_manager.register_provider(groq_20b)
                print(f"   Updated providers: {llm_manager.get_available_providers()}")
                
                # Try to set as primary
                print("\n8. Setting as primary provider...")
                llm_manager.set_primary_provider("Groq (openai/gpt-oss-20b)")
                print(f"   Primary: {llm_manager.get_primary_provider().get_provider_name()}")
            
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Plugin manager test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_plugin_manager_debug()
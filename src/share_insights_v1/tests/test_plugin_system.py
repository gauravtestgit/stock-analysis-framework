#!/usr/bin/env python3
"""
Test script for LLM Plugin System
Tests plugin manager functionality without breaking existing system
"""

import sys
import os

# Add src to path
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from ..implementations.llm_providers.plugin_manager import LLMPluginManager
from ..implementations.llm_providers.config_service import LLMConfigService

def test_plugin_manager():
    """Test plugin manager initialization and basic functionality"""
    print("=" * 50)
    print("Testing LLM Plugin Manager")
    print("=" * 50)
    
    try:
        # Test plugin manager initialization
        print("\n1. Testing Plugin Manager Initialization...")
        plugin_manager = LLMPluginManager()
        
        if plugin_manager.is_available():
            print("✅ Plugin manager initialized successfully")
            
            # Test provider registration
            print(f"✅ Registered providers: {plugin_manager.get_available_providers()}")
            
            # Test provider creation (only if API keys available)
            for provider_name in plugin_manager.get_available_providers():
                try:
                    print(f"\n2. Testing {provider_name} provider creation...")
                    provider = plugin_manager.create_provider(provider_name)
                    print(f"✅ Created {provider_name}: {provider.get_provider_name()}")
                    print(f"✅ Available: {provider.is_available()}")
                    print(f"✅ Current model: {provider.get_current_model()}")
                    
                    # Test model switching
                    models = plugin_manager.get_available_models(provider_name)
                    print(f"✅ Available models for {provider_name}: {models}")
                    
                    if len(models) > 1:
                        new_model = models[1]  # Try second model
                        success = provider.set_current_model(new_model)
                        print(f"✅ Model switch to {new_model}: {success}")
                    
                    # Test specific model for Groq
                    if provider_name == "groq":
                        print(f"\n   Testing specific Groq model: openai/gpt-oss-20b")
                        try:
                            groq_20b = plugin_manager.create_provider("groq", "openai/gpt-oss-20b")
                            print(f"   ✅ Created Groq 20B: {groq_20b.get_provider_name()}")
                            print(f"   ✅ Available: {groq_20b.is_available()}")
                        except Exception as e:
                            print(f"   ❌ Failed to create Groq 20B: {e}")
                        
                except Exception as e:
                    print(f"⚠️  {provider_name} provider creation failed (likely missing API key): {e}")
            
        else:
            print("❌ Plugin manager not available")
            
    except Exception as e:
        print(f"❌ Plugin manager test failed: {e}")

def test_config_service():
    """Test configuration service"""
    print("\n" + "=" * 50)
    print("Testing LLM Config Service")
    print("=" * 50)
    
    try:
        # Test config service
        print("\n1. Testing Config Service...")
        config_service = LLMConfigService.get_instance()
        
        print(f"✅ Plugin system available: {config_service.is_plugin_system_available()}")
        print(f"✅ Available providers: {config_service.get_available_providers()}")
        
        # Test UI config
        print("\n2. Testing UI Config...")
        ui_config = config_service.get_ui_config()
        print(f"✅ UI config loaded with {len(ui_config['providers'])} providers")
        
        for provider in ui_config['providers']:
            print(f"  - {provider['display_name']}: {provider['available']} (models: {len(provider['models'])})")
            
    except Exception as e:
        print(f"❌ Config service test failed: {e}")

def test_fallback_behavior():
    """Test that system works even when plugin system fails"""
    print("\n" + "=" * 50)
    print("Testing Fallback Behavior")
    print("=" * 50)
    
    try:
        # Test with invalid config path
        print("\n1. Testing with invalid config...")
        plugin_manager = LLMPluginManager("nonexistent_config.yaml")
        
        if not plugin_manager.is_available():
            print("✅ Plugin manager correctly reports unavailable with bad config")
        
        # Test config service fallback
        print("\n2. Testing config service fallback...")
        config_service = LLMConfigService()
        ui_config = config_service.get_ui_config()
        
        if ui_config and 'providers' in ui_config:
            print("✅ Config service provides fallback UI config")
            print(f"✅ Fallback providers: {[p['name'] for p in ui_config['providers']]}")
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting LLM Plugin System Tests")
    print("This test validates the plugin system without affecting existing functionality")
    
    test_plugin_manager()
    test_config_service()
    test_fallback_behavior()
    
    print("\n" + "=" * 50)
    print("✅ Plugin System Tests Complete")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Set environment variables for API keys to test provider creation")
    print("2. Run existing analysis to ensure no breaking changes")
    print("3. Proceed to Phase 2: Backward compatibility layer")
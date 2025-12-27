import os
from typing import Dict, Any, List, Optional
from .plugin_manager import LLMPluginManager

class LLMConfigService:
    """Service for accessing LLM configuration across the application"""
    
    _instance = None
    _plugin_manager = None
    
    @classmethod
    def get_instance(cls) -> 'LLMConfigService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize config service"""
        try:
            self._plugin_manager = LLMPluginManager()
            print(f"[CONFIG_DEBUG] LLM Config Service initialized successfully")
        except Exception as e:
            print(f"[CONFIG_DEBUG] LLM Config Service initialization failed: {e}")
            self._plugin_manager = None
    
    def get_ui_config(self) -> Dict[str, Any]:
        """Get configuration formatted for UI consumption"""
        if self._plugin_manager and self._plugin_manager.is_available():
            return self._plugin_manager.get_ui_config()
        
        # Fallback to hardcoded config if plugin system fails
        return self._get_fallback_ui_config()
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        if self._plugin_manager and self._plugin_manager.is_available():
            return self._plugin_manager.get_available_providers()
        
        # Fallback
        return ["groq", "openai", "xai"]
    
    def get_available_models(self, provider_name: str) -> List[str]:
        """Get available models for a provider"""
        if self._plugin_manager and self._plugin_manager.is_available():
            return self._plugin_manager.get_available_models(provider_name)
        
        # Fallback model lists
        fallback_models = {
            "groq": ["llama-3.1-8b-instant", "llama-3.1-70b-versatile"],
            "openai": ["gpt-3.5-turbo", "gpt-4"],
            "xai": ["grok-beta"]
        }
        return fallback_models.get(provider_name, [])
    
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for specific provider"""
        if self._plugin_manager and self._plugin_manager.is_available():
            return self._plugin_manager.get_provider_config(provider_name)
        return None
    
    def is_plugin_system_available(self) -> bool:
        """Check if plugin system is available"""
        return self._plugin_manager is not None and self._plugin_manager.is_available()
    
    def _get_fallback_ui_config(self) -> Dict[str, Any]:
        """Fallback UI config when plugin system is not available"""
        return {
            "providers": [
                {
                    "name": "groq",
                    "display_name": "Groq",
                    "description": "Fast inference with Llama models",
                    "icon": "🚀",
                    "available": bool(os.getenv("GROQ_API_KEY")),
                    "default_model": "llama-3.1-8b-instant",
                    "models": [
                        {
                            "name": "llama-3.1-8b-instant",
                            "display_name": "Llama 3.1 8B (Fast)",
                            "description": "Fastest model, good for most tasks"
                        }
                    ]
                },
                {
                    "name": "openai",
                    "display_name": "OpenAI",
                    "description": "Industry standard GPT models",
                    "icon": "🤖",
                    "available": bool(os.getenv("OPENAI_API_KEY")),
                    "default_model": "gpt-3.5-turbo",
                    "models": [
                        {
                            "name": "gpt-3.5-turbo",
                            "display_name": "GPT-3.5 Turbo",
                            "description": "Fast and cost-effective"
                        }
                    ]
                }
            ]
        }
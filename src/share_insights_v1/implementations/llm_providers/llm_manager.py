from typing import List, Optional
import os
import time
import threading
from ...interfaces.llm_provider import ILLMProvider
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .xai_provider import XAIProvider
from .plugin_manager import LLMPluginManager
from .config_service import LLMConfigService
from ...utils.debug_printer import debug_print
class LLMManager:
    """Manages multiple LLM providers with fallback and plugin support"""
    
    def __init__(self, use_plugin_system: bool = None, providers: List[ILLMProvider] = None):
        self.providers: List[ILLMProvider] = []
        self.plugin_manager = None
        
        # Determine if plugin system should be used
        if use_plugin_system is None:
            use_plugin_system = os.getenv("USE_LLM_PLUGIN_SYSTEM", "false").lower() == "true"
        
        self.use_plugin_system = use_plugin_system
        
        debug_print(f"[LLM_DEBUG] Initializing LLM Manager (plugin_system: {use_plugin_system})...")
        
        # If providers are explicitly provided, use them
        if providers:
            self.providers = providers
            debug_print(f"[LLM_DEBUG] Using provided providers: {[p.get_provider_name() for p in providers]}")
        elif use_plugin_system:
            self._setup_via_plugin_system()
        else:
            self._setup_providers_legacy()
    
    def _setup_via_plugin_system(self):
        """Setup providers using plugin system with fallback to legacy"""
        try:
            debug_print("[LLM_DEBUG] Attempting to use plugin system...")
            self.plugin_manager = LLMPluginManager()
            
            if self.plugin_manager.is_available():
                # Get available providers from plugin system
                available_providers = self.plugin_manager.get_available_providers()
                debug_print(f"[LLM_DEBUG] Plugin system found providers: {available_providers}")
                
                # Create providers that have API keys
                for provider_name in available_providers:
                    try:
                        provider = self.plugin_manager.create_provider(provider_name)
                        if provider.is_available():
                            self.providers.append(provider)
                            debug_print(f"[LLM_DEBUG] Added plugin provider: {provider.get_provider_name()}")
                        else:
                            debug_print(f"[LLM_DEBUG] Plugin provider {provider_name} not available (missing API key)")
                    except Exception as e:
                        debug_print(f"[LLM_DEBUG] Failed to create plugin provider {provider_name}: {e}")
                
                if self.providers:
                    debug_print(f"[LLM_DEBUG] Plugin system setup successful with {len(self.providers)} providers")
                    return
            
            debug_print("[LLM_DEBUG] Plugin system not available, falling back to legacy")
            
        except Exception as e:
            debug_print(f"[LLM_DEBUG] Plugin system failed: {e}, falling back to legacy")
        
        # Fallback to legacy system
        self._setup_providers_legacy()
    
    def _setup_providers_legacy(self):
        """Setup default LLM provider (legacy method - Groq only)"""
        debug_print("[LLM_DEBUG] Using legacy provider setup...")
        
        # Add Groq provider (primary)
        try:
            groq = GroqProvider()
            debug_print(f"[LLM_DEBUG] Groq provider initialized, available: {groq.is_available()}")
            if groq.is_available():
                self.providers.append(groq)
        except Exception as e:
            debug_print(f"[LLM_DEBUG] Groq provider failed: {e}")
        
        debug_print(f"[LLM_DEBUG] Legacy setup complete: {len(self.providers)} providers")
        for provider in self.providers:
            debug_print(f"[LLM_DEBUG] - {provider.get_provider_name()}")
    
    def register_provider(self, provider: ILLMProvider):
        """Register an additional LLM provider"""
        if provider.is_available():
            self.providers.append(provider)
            debug_print(f"[LLM_DEBUG] Registered provider: {provider.get_provider_name()}")
        else:
            debug_print(f"[LLM_DEBUG] Provider {provider.get_provider_name()} not available, skipping registration")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using first available provider"""
        if not self.providers:
            raise Exception("No LLM providers available")
        
        debug_print(f"[LLM_DEBUG] Starting LLM call with {len(self.providers)} providers...")
        
        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                debug_print(f"[LLM_DEBUG] Attempting provider {i+1}/{len(self.providers)}: {provider.get_provider_name()}")
                start_time = time.time()
                response = provider.generate_response(prompt, **kwargs)
                end_time = time.time()
                debug_print(f"[LLM_DEBUG] Provider {provider.get_provider_name()} succeeded in {end_time-start_time:.2f}s")
                return response
            except Exception as e:
                last_error = e
                debug_print(f"[LLM_DEBUG] Provider {provider.get_provider_name()} failed: {type(e).__name__}: {e}")
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    debug_print(f"[LLM_DEBUG] HTTP Status: {e.response.status_code}")
                if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                    rate_limit_headers = {k: v for k, v in e.response.headers.items() if 'rate' in k.lower() or 'limit' in k.lower()}
                    if rate_limit_headers:
                        debug_print(f"[LLM_DEBUG] Rate limit headers: {rate_limit_headers}")
                continue
        
        debug_print(f"[LLM_DEBUG] All providers failed. Last error: {type(last_error).__name__}: {last_error}")
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [provider.get_provider_name() for provider in self.providers]
    
    def get_primary_provider(self) -> Optional[ILLMProvider]:
        """Get primary (first) provider"""
        return self.providers[0] if self.providers else None
    
    def get_provider_by_name(self, name: str) -> Optional[ILLMProvider]:
        """Get specific provider by name"""
        for provider in self.providers:
            if provider.get_provider_name() == name:
                return provider
        return None
    
    def generate_response_with_provider(self, prompt: str, provider_name: str, **kwargs) -> str:
        """Generate response using specific provider"""
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not available")
        
        return provider.generate_response(prompt, **kwargs)
    
    def set_primary_provider(self, provider_name: str, model_name: str = None):
        """Set a specific provider as primary, auto-instantiating if needed"""
        provider = self.get_provider_by_name(provider_name)
        
        if not provider:
            # Provider doesn't exist, create it
            base_name = provider_name.lower().split('(')[0].strip()
            provider = self.create_provider_by_name(base_name, model_name)
            if not provider:
                raise Exception(f"Could not create provider {base_name}")
            if not provider.is_available():
                raise Exception(f"Provider {base_name} not available (missing API key)")
            self.providers.insert(0, provider)
            debug_print(f"[LLM_DEBUG] Created and set new provider {provider.get_provider_name()} as primary")
        else:
            # Provider exists, optionally change model
            if model_name and hasattr(provider, 'set_current_model'):
                provider.set_current_model(model_name)
                debug_print(f"[LLM_DEBUG] Changed model to {model_name} on provider {provider_name}")
            
            # Move to primary position
            self.providers.remove(provider)
            self.providers.insert(0, provider)
            debug_print(f"[LLM_DEBUG] Set existing provider {provider_name} as primary")
    
    def create_provider_by_name(self, provider_name: str, model_name: str = None) -> Optional[ILLMProvider]:
        """Create a new provider instance by name (plugin system method)"""
        if self.plugin_manager and self.plugin_manager.is_available():
            try:
                return self.plugin_manager.create_provider(provider_name, model_name)
            except Exception as e:
                debug_print(f"[LLM_DEBUG] Plugin provider creation failed: {e}")
        
        # Fallback to legacy creation
        return self._create_provider_legacy(provider_name, model_name)
    
    def _create_provider_legacy(self, provider_name: str, model_name: str = None) -> Optional[ILLMProvider]:
        """Create provider using legacy method"""
        provider_map = {
            "groq": GroqProvider,
            "openai": OpenAIProvider,
            "xai": XAIProvider
        }
        
        if provider_name.lower() in provider_map:
            provider_class = provider_map[provider_name.lower()]
            try:
                if model_name:
                    return provider_class(model_name)
                else:
                    return provider_class()
            except Exception as e:
                debug_print(f"[LLM_DEBUG] Legacy provider creation failed: {e}")
        
        return None
    
    def get_config_service(self) -> Optional[LLMConfigService]:
        """Get configuration service for UI integration"""
        return LLMConfigService.get_instance()
    
    def get_ui_config(self) -> dict:
        """Get UI configuration for provider/model selection"""
        config_service = self.get_config_service()
        if config_service:
            return config_service.get_ui_config()
        
        # Fallback UI config
        return {
            "providers": [
                {
                    "name": "groq",
                    "display_name": "Groq",
                    "available": bool(os.getenv("GROQ_API_KEY")),
                    "models": [{"name": "llama-3.1-8b-instant", "display_name": "Llama 3.1 8B"}]
                }
            ]
        }
    
    def set_provider_priority(self, provider_names: List[str]):
        """Set provider priority order by names"""
        new_providers = []
        
        # Add providers in specified order
        for name in provider_names:
            provider = self.get_provider_by_name(name)
            if provider:
                new_providers.append(provider)
            else:
                debug_print(f"[LLM_DEBUG] Provider {name} not found, skipping")
        
        # Add any remaining providers not in the list
        for provider in self.providers:
            if provider not in new_providers:
                new_providers.append(provider)
        
        self.providers = new_providers
        debug_print(f"[LLM_DEBUG] Updated provider priority: {[p.get_provider_name() for p in self.providers]}")
    
    def is_plugin_system_enabled(self) -> bool:
        """Check if plugin system is enabled"""
        return self.use_plugin_system and self.plugin_manager is not None
    
    def get_system_info(self) -> dict:
        """Get information about the LLM system configuration"""
        return {
            "plugin_system_enabled": self.is_plugin_system_enabled(),
            "plugin_system_available": self.plugin_manager.is_available() if self.plugin_manager else False,
            "total_providers": len(self.providers),
            "available_providers": self.get_available_providers(),
            "primary_provider": self.get_primary_provider().get_provider_name() if self.get_primary_provider() else None
        }
from typing import List, Optional
import time
import threading
from ...interfaces.llm_provider import ILLMProvider
from .groq_provider import GroqProvider
from .openai_provider import OpenAIProvider
from .xai_provider import XAIProvider

class LLMManager:
    """Manages multiple LLM providers with fallback"""
    
    def __init__(self):
        self.providers: List[ILLMProvider] = []
        print("[LLM_DEBUG] Initializing LLM Manager...")
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup default LLM provider (Groq only)"""
        # Add Groq provider (primary)
        try:
            groq = GroqProvider()
            print(f"[LLM_DEBUG] Groq provider initialized, available: {groq.is_available()}")
            if groq.is_available():
                self.providers.append(groq)
        except Exception as e:
            print(f"[LLM_DEBUG] Groq provider failed: {e}")
        
        print(f"[LLM_DEBUG] Total providers initialized: {len(self.providers)}")
        for provider in self.providers:
            print(f"[LLM_DEBUG] - {provider.get_provider_name()}")
    
    def register_provider(self, provider: ILLMProvider):
        """Register an additional LLM provider"""
        if provider.is_available():
            self.providers.append(provider)
            print(f"[LLM_DEBUG] Registered provider: {provider.get_provider_name()}")
        else:
            print(f"[LLM_DEBUG] Provider {provider.get_provider_name()} not available, skipping registration")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using first available provider"""
        if not self.providers:
            raise Exception("No LLM providers available")
        
        print(f"[LLM_DEBUG] Starting LLM call with {len(self.providers)} providers...")
        
        last_error = None
        for i, provider in enumerate(self.providers):
            try:
                print(f"[LLM_DEBUG] Attempting provider {i+1}/{len(self.providers)}: {provider.get_provider_name()}")
                start_time = time.time()
                response = provider.generate_response(prompt, **kwargs)
                end_time = time.time()
                print(f"[LLM_DEBUG] Provider {provider.get_provider_name()} succeeded in {end_time-start_time:.2f}s")
                return response
            except Exception as e:
                last_error = e
                print(f"[LLM_DEBUG] Provider {provider.get_provider_name()} failed: {type(e).__name__}: {e}")
                if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    print(f"[LLM_DEBUG] HTTP Status: {e.response.status_code}")
                if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                    rate_limit_headers = {k: v for k, v in e.response.headers.items() if 'rate' in k.lower() or 'limit' in k.lower()}
                    if rate_limit_headers:
                        print(f"[LLM_DEBUG] Rate limit headers: {rate_limit_headers}")
                continue
        
        print(f"[LLM_DEBUG] All providers failed. Last error: {type(last_error).__name__}: {last_error}")
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
    
    def set_primary_provider(self, provider_name: str):
        """Set a specific provider as primary (first in priority)"""
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            raise Exception(f"Provider {provider_name} not found")
        
        # Remove provider from current position and insert at beginning
        self.providers.remove(provider)
        self.providers.insert(0, provider)
        print(f"[LLM_DEBUG] Set {provider_name} as primary provider")
    
    def set_provider_priority(self, provider_names: List[str]):
        """Set provider priority order by names"""
        new_providers = []
        
        # Add providers in specified order
        for name in provider_names:
            provider = self.get_provider_by_name(name)
            if provider:
                new_providers.append(provider)
            else:
                print(f"[LLM_DEBUG] Provider {name} not found, skipping")
        
        # Add any remaining providers not in the list
        for provider in self.providers:
            if provider not in new_providers:
                new_providers.append(provider)
        
        self.providers = new_providers
        print(f"[LLM_DEBUG] Updated provider priority: {[p.get_provider_name() for p in self.providers]}")
from typing import List, Optional
import time
from ...interfaces.llm_provider import ILLMProvider
from .groq_provider import GroqProvider

class LLMManager:
    """Manages multiple LLM providers with fallback"""
    
    def __init__(self):
        self.providers: List[ILLMProvider] = []
        self._setup_providers()
    
    def _setup_providers(self):
        """Setup available LLM providers in order of preference"""
        # Add Groq provider
        groq = GroqProvider()
        if groq.is_available():
            self.providers.append(groq)
        
        # Add other providers here as needed
        # openai = OpenAIProvider()
        # if openai.is_available():
        #     self.providers.append(openai)
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using first available provider"""
        if not self.providers:
            raise Exception("No LLM providers available")
        
        # Add delay to prevent rate limiting
        time.sleep(2)
        
        last_error = None
        for provider in self.providers:
            try:
                return provider.generate_response(prompt, **kwargs)
            except Exception as e:
                last_error = e
                print(f"Provider {provider.get_provider_name()} failed: {e}")
                continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return [provider.get_provider_name() for provider in self.providers]
    
    def get_primary_provider(self) -> Optional[ILLMProvider]:
        """Get primary (first) provider"""
        return self.providers[0] if self.providers else None
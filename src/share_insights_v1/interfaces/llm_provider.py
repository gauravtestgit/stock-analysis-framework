from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# Shared across every provider implementation - none of them passed an explicit
# max_tokens, so each silently fell back to whatever default its API applies
# when the parameter is omitted. Confirmed directly against Groq's
# openai/gpt-oss-20b: that default is 2048, and reasoning models like this one
# spend a chunk of it on internal reasoning tokens before writing the visible
# answer (915 of 2048 in one captured call), leaving well under half the
# budget for actual output. Several analyzer prompts in this app ask for
# verbose, multi-field JSON (Industry Analysis's Porter's Five Forces,
# Business Model's competitive differentiation, Thesis Generation's narrative)
# that can exceed that silent default and get cut off mid-response with
# finish_reason: 'length' - confirmed directly on a live call. This constant
# raises the ceiling; it does not force responses to use it - the model still
# stops on its own once a response is complete.
MAX_COMPLETION_TOKENS = 8000

class ILLMProvider(ABC):
    """Interface for LLM providers"""
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass
    
    @abstractmethod
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information"""
        pass
    
    @abstractmethod
    def get_current_model(self) -> str:
        """Get currently selected model name"""
        pass
    
    @abstractmethod
    def set_current_model(self, model: str) -> bool:
        """Set current model, returns success status"""
        pass
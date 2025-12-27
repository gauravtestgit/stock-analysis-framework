from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

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
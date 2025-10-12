import os
import requests
from typing import Optional
from ...interfaces.llm_provider import ILLMProvider

class XAIProvider(ILLMProvider):
    """XAI (Grok) LLM provider"""
    
    def __init__(self):
        self.api_key = os.getenv('XAI_API_KEY')
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-beta"
        print(f"[XAI_DEBUG] API key found: {bool(self.api_key)}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using XAI Grok"""
        if not self.api_key:
            print("XAI API Key not found")
            raise Exception("XAI API key not found")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "model": self.model,
                "temperature": 0.1,
                "max_tokens": 2000
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"XAI API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise Exception(f"XAI generation failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if XAI provider is available"""
        available = self.api_key is not None
        print(f"[XAI_DEBUG] is_available: {available}, api_key: {self.api_key is not None}")
        return available
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "XAI (Grok)"
    
    def get_rate_limit_info(self) -> Optional[dict]:
        """Get rate limit information"""
        return {
            "requests_per_minute": 60,
            "tokens_per_minute": 10000,
            "requests_per_day": 1000
        }
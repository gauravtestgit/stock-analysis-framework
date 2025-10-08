import os
import time
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from ...interfaces.llm_provider import ILLMProvider

class GroqProvider(ILLMProvider):
    """Groq LLM provider with rate limiting"""
    
    def __init__(self, model_name: str = "llama-3.1-8b-instant", max_retries: int = 3):
        self.model_name = model_name
        self.max_retries = max_retries
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
        
        try:
            self.llm = ChatGroq(
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name=model_name,
                temperature=0.1
            )
        except Exception as e:
            self.llm = None
            print(f"Failed to initialize Groq: {e}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response with rate limiting and retries"""
        if not self.llm:
            raise Exception("Groq provider not available")
        
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_request_interval:
                    sleep_time = self.min_request_interval - time_since_last
                    time.sleep(sleep_time)
                
                # Make request
                prompt_template = ChatPromptTemplate.from_template("{prompt}")
                chain = prompt_template | self.llm
                response = chain.invoke({"prompt": prompt})
                self.last_request_time = time.time()
                
                return response.content
                
            except Exception as e:
                error_msg = str(e).lower()
                if "rate limit" in error_msg and attempt < self.max_retries - 1:
                    # Extract wait time from error message
                    wait_time = self._extract_wait_time(str(e))
                    print(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise e
        
        raise Exception(f"Failed after {self.max_retries} attempts")
    
    def _extract_wait_time(self, error_message: str) -> float:
        """Extract wait time from rate limit error message"""
        try:
            # Look for "try again in X.Xs" pattern
            import re
            match = re.search(r'try again in (\d+\.?\d*)s', error_message)
            if match:
                return float(match.group(1)) + 1  # Add 1 second buffer
        except:
            pass
        return 5.0  # Default wait time
    
    def is_available(self) -> bool:
        """Check if Groq is available"""
        return self.llm is not None and os.getenv("GROQ_API_KEY") is not None
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"Groq ({self.model_name})"
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information"""
        return {
            "provider": "Groq",
            "model": self.model_name,
            "tokens_per_minute": 6000,
            "requests_per_minute": 30,
            "min_request_interval": self.min_request_interval
        }
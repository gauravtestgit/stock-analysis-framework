import os
import time
import threading
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from ...interfaces.llm_provider import ILLMProvider
from ...utils.debug_printer import debug_print
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
            debug_print(f"Failed to initialize Groq: {e}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response with rate limiting and retries"""
        if not self.llm:
            raise Exception("Groq provider not available")
        
        debug_print(f"[GROQ_DEBUG] Starting Groq request, attempt 1/{self.max_retries}")
        
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                if time_since_last < self.min_request_interval:
                    sleep_time = self.min_request_interval - time_since_last
                    debug_print(f"[GROQ_DEBUG] Rate limiting: sleeping {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                
                # Make request
                debug_print(f"[GROQ_DEBUG] Making API request to {self.model_name}")
                request_start = time.time()
                prompt_template = ChatPromptTemplate.from_template("{prompt}")
                chain = prompt_template | self.llm
                response = chain.invoke({"prompt": prompt})
                request_end = time.time()
                self.last_request_time = time.time()
                
                debug_print(f"[GROQ_DEBUG] Request successful in {request_end-request_start:.2f}s")
                return response.content
                
            except Exception as e:
                debug_print(f"[GROQ_DEBUG] Attempt {attempt+1} failed: {type(e).__name__}: {e}")
                
                # Check for rate limit specific errors
                error_msg = str(e).lower()
                if "rate limit" in error_msg or "429" in str(e):
                    if attempt < self.max_retries - 1:
                        wait_time = self._extract_wait_time(str(e))
                        debug_print(f"[GROQ_DEBUG] Rate limit detected, waiting {wait_time}s before retry {attempt + 2}")
                        time.sleep(wait_time)
                        continue
                    else:
                        debug_print(f"[GROQ_DEBUG] Rate limit on final attempt, giving up")
                        raise e
                else:
                    debug_print(f"[GROQ_DEBUG] Non-rate-limit error, giving up: {e}")
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
    
    def get_current_model(self) -> str:
        """Get currently selected model name"""
        return self.model_name
    
    def set_current_model(self, model: str) -> bool:
        """Set current model, returns success status"""
        try:
            self.model_name = model
            self.llm = ChatGroq(
                groq_api_key=os.getenv("GROQ_API_KEY"),
                model_name=model,
                temperature=0.1
            )
            return True
        except Exception as e:
            debug_print(f"Failed to switch to model {model}: {e}")
            return False
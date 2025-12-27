import os
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ...interfaces.llm_provider import ILLMProvider

class OpenAIProvider(ILLMProvider):
    """OpenAI LLM provider using LangChain"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.llm = None
        print(f"[OPENAI_DEBUG] API key found: {bool(self.api_key)}")
        if self.api_key:
            try:
                self.llm = ChatOpenAI(
                    model=model_name,
                    temperature=0.1,
                    api_key=self.api_key
                )
                print(f"[OPENAI_DEBUG] LLM initialized successfully with model {model_name}")
            except Exception as e:
                print(f"[OPENAI_DEBUG] Failed to initialize OpenAI: {e}")
        else:
            print(f"[OPENAI_DEBUG] No API key found")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI"""
        if not self.llm:
            raise Exception("OpenAI provider not initialized")
        
        try:
            # Create prompt template
            prompt_template = ChatPromptTemplate.from_messages([
                ("human", prompt)
            ])
            
            # Create chain and invoke
            chain = prompt_template | self.llm
            response = chain.invoke({})
            
            return response.content
            
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if OpenAI provider is available"""
        available = self.llm is not None and self.api_key is not None
        print(f"[OPENAI_DEBUG] is_available: {available}, llm: {self.llm is not None}, api_key: {self.api_key is not None}")
        return available
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"OpenAI ({self.model_name})"
    
    def get_rate_limit_info(self) -> Optional[dict]:
        """Get rate limit information"""
        return {
            "provider": "OpenAI",
            "model": self.model_name,
            "requests_per_minute": 3500,
            "tokens_per_minute": 90000,
            "requests_per_day": 10000
        }
    
    def get_current_model(self) -> str:
        """Get currently selected model name"""
        return self.model_name
    
    def set_current_model(self, model: str) -> bool:
        """Set current model, returns success status"""
        try:
            self.model_name = model
            self.llm = ChatOpenAI(
                model=model,
                temperature=0.1,
                api_key=self.api_key
            )
            print(f"[OPENAI_DEBUG] Switched to model {model}")
            return True
        except Exception as e:
            print(f"Failed to switch to model {model}: {e}")
            return False
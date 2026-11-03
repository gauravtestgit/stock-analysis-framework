import os
from typing import Dict, Any, Optional
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from ...interfaces.llm_provider import ILLMProvider, MAX_COMPLETION_TOKENS
from ...utils.debug_printer import debug_print
class ClaudeProvider(ILLMProvider):
    """Anthropic Claude LLM provider using LangChain"""

    def __init__(self, model_name: str = "claude-sonnet-5-5"):
        self.model_name = model_name
        self.api_key = os.getenv('CLAUDE_API_KEY')
        self.llm = None
        debug_print(f"[CLAUDE_DEBUG] API key found: {bool(self.api_key)}, model: {model_name}")
        if self.api_key:
            try:
                self.llm = ChatAnthropic(
                    model=model_name,
                    temperature=0.1,
                    api_key=self.api_key,
                    max_tokens=MAX_COMPLETION_TOKENS
                )
                debug_print(f"[CLAUDE_DEBUG] LLM initialized successfully with model {model_name}")
            except Exception as e:
                debug_print(f"[CLAUDE_DEBUG] Failed to initialize Claude: {e}")
        else:
            debug_print("[CLAUDE_DEBUG] No API key found")

    def generate_response(self, prompt: str, temperature: Optional[float] = None, **kwargs) -> str:
        """Generate response using Claude.

        temperature overrides this provider's construction-time default
        (0.1) for just this call, via LangChain's .bind() - matches
        GroqProvider's signature so callers (e.g. BusinessModelAnalyzer)
        can request temperature=0 without a second provider instance.
        """
        if not self.llm:
            raise Exception("Claude provider not initialized")

        try:
            prompt_template = ChatPromptTemplate.from_messages([
                ("human", "{prompt}")
            ])
            llm = self.llm.bind(temperature=temperature) if temperature is not None else self.llm
            chain = prompt_template | llm
            response = chain.invoke({"prompt": prompt})

            return response.content

        except Exception as e:
            raise Exception(f"Claude generation failed: {str(e)}")

    def is_available(self) -> bool:
        """Check if Claude provider is available"""
        available = self.llm is not None and self.api_key is not None
        debug_print(f"[CLAUDE_DEBUG] is_available: {available}, llm: {self.llm is not None}, api_key: {self.api_key is not None}")
        return available

    def get_provider_name(self) -> str:
        """Get provider name"""
        return f"Claude ({self.model_name})"

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information"""
        return {
            "provider": "Claude",
            "model": self.model_name,
            "requests_per_minute": 50,
            "tokens_per_minute": 40000,
            "requests_per_day": 1000
        }

    def get_current_model(self) -> str:
        """Get currently selected model name"""
        return self.model_name

    def set_current_model(self, model: str) -> bool:
        """Set current model, returns success status"""
        try:
            self.model_name = model
            self.llm = ChatAnthropic(
                model=model,
                temperature=0.1,
                api_key=self.api_key,
                max_tokens=MAX_COMPLETION_TOKENS
            )
            debug_print(f"[CLAUDE_DEBUG] Switched to model {model}")
            return True
        except Exception as e:
            debug_print(f"Failed to switch to model {model}: {e}")
            return False

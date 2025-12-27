"""
Universal prompt formatter for cross-provider compatibility
"""
import re
from typing import Dict, Any

class PromptFormatter:
    """Formats prompts to work consistently across different LLM providers"""
    
    @staticmethod
    def format_json_prompt(prompt: str, provider_name: str = None) -> str:
        """
        Format prompts containing JSON examples for cross-provider compatibility
        
        Args:
            prompt: The original prompt with JSON examples
            provider_name: Optional provider name for specific formatting
            
        Returns:
            Formatted prompt that works across all providers
        """
        # For OpenAI/LangChain providers, escape curly braces in JSON examples
        if provider_name and "OpenAI" in provider_name:
            return PromptFormatter._escape_json_braces(prompt)
        
        # For other providers (Groq, XAI), use original format
        return prompt
    
    @staticmethod
    def _escape_json_braces(prompt: str) -> str:
        """Escape JSON curly braces for LangChain ChatPromptTemplate compatibility"""
        # Find JSON blocks and escape their braces
        # Pattern: Look for { followed by content that looks like JSON
        json_pattern = r'(\{[^{}]*(?:"[^"]*"[^{}]*)*\})'
        
        def escape_json_block(match):
            json_block = match.group(1)
            # Double the braces to escape them
            return json_block.replace('{', '{{').replace('}', '}}')
        
        # Apply escaping to JSON-like blocks
        escaped = re.sub(json_pattern, escape_json_block, prompt, flags=re.DOTALL)
        return escaped
    
    @staticmethod
    def create_analysis_prompt(
        company_info: Dict[str, Any],
        analysis_type: str,
        json_schema: Dict[str, Any],
        provider_name: str = None
    ) -> str:
        """
        Create standardized analysis prompt with proper JSON formatting
        
        Args:
            company_info: Company data (name, sector, metrics, etc.)
            analysis_type: Type of analysis (insights, revenue_trends, etc.)
            json_schema: Expected JSON response schema
            provider_name: LLM provider name for formatting
            
        Returns:
            Properly formatted prompt
        """
        # Build base prompt
        prompt = f"""Analyze {company_info.get('name', 'the company')} and provide {analysis_type}:

Company Details:"""
        
        # Add company information
        for key, value in company_info.items():
            if key != 'name' and value is not None:
                prompt += f"\n- {key.replace('_', ' ').title()}: {value}"
        
        # Add JSON schema
        prompt += f"\n\nProvide analysis in JSON format:\n"
        prompt += PromptFormatter._format_json_schema(json_schema)
        
        # Apply provider-specific formatting
        return PromptFormatter.format_json_prompt(prompt, provider_name)
    
    @staticmethod
    def _format_json_schema(schema: Dict[str, Any]) -> str:
        """Format JSON schema as example"""
        import json
        return json.dumps(schema, indent=4)
    
    @staticmethod
    def get_provider_name_from_llm_manager(llm_manager) -> str:
        """Extract provider name from LLM manager for formatting"""
        try:
            primary_provider = llm_manager.get_primary_provider()
            if primary_provider:
                return primary_provider.get_provider_name()
        except:
            pass
        return "Unknown"

# Convenience functions for common prompt patterns
def create_company_insights_prompt(company_info: Dict[str, Any], provider_name: str = None) -> str:
    """Create company insights analysis prompt"""
    schema = {
        "market_position": "Strong/Moderate/Weak",
        "growth_prospects": "High/Moderate/Low", 
        "competitive_advantage": "Strong/Moderate/Weak",
        "management_quality": "Excellent/Good/Average/Poor",
        "industry_outlook": "Very Positive/Positive/Neutral/Negative",
        "key_strengths": ["strength1", "strength2"],
        "key_risks": ["risk1", "risk2"]
    }
    
    return PromptFormatter.create_analysis_prompt(
        company_info, "company insights", schema, provider_name
    )

def create_revenue_trends_prompt(company_info: Dict[str, Any], provider_name: str = None) -> str:
    """Create revenue trends analysis prompt"""
    schema = {
        "trend_assessment": "Strong Growth/Moderate Growth/Stable/Declining",
        "growth_rate": 0.0,
        "growth_consistency": "Consistent/Variable/Volatile",
        "future_outlook": "Very Positive/Positive/Neutral/Cautious/Negative"
    }
    
    return PromptFormatter.create_analysis_prompt(
        company_info, "revenue trends", schema, provider_name
    )

def create_etf_insights_prompt(etf_info: Dict[str, Any], provider_name: str = None) -> str:
    """Create ETF-specific insights prompt"""
    schema = {
        "market_position": "Strong/Moderate/Weak",
        "growth_prospects": "High/Moderate/Low", 
        "competitive_advantage": "Strong/Moderate/Weak",
        "management_quality": "Excellent/Good/Average/Poor",
        "industry_outlook": "Very Positive/Positive/Neutral/Negative",
        "key_strengths": ["Low expense ratio", "Diversified holdings", "Good liquidity"],
        "key_risks": ["Market concentration risk", "Tracking error", "Currency risk"]
    }
    
    return PromptFormatter.create_analysis_prompt(
        etf_info, "ETF analysis focusing on ETF-specific factors", schema, provider_name
    )

def create_sentiment_analysis_prompt(news_info: Dict[str, Any], provider_name: str = None) -> str:
    """Create news sentiment analysis prompt"""
    schema = {
        "sentiment_score": 0.0,
        "confidence": 0.8
    }
    
    return PromptFormatter.create_analysis_prompt(
        news_info, "sentiment analysis", schema, provider_name
    )

def create_news_summary_prompt(summary_info: Dict[str, Any], provider_name: str = None) -> str:
    """Create news summary analysis prompt"""
    # For news summary, we return a list instead of a dict
    base_prompt = f"""Analyze these recent news articles and provide a 3-4 bullet point summary explaining the overall sentiment score of {summary_info.get('sentiment_score', 0.0):.2f}:

{summary_info.get('news_text', '')}

Provide ONLY a JSON array of bullet points:
[
    "Bullet point 1 explaining key positive/negative factors",
    "Bullet point 2 about market reactions or developments",
    "Bullet point 3 about future outlook or concerns"
]"""
    
    return PromptFormatter.format_json_prompt(base_prompt, provider_name)
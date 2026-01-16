"""
Prompt loader utility for thesis generation templates
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ThesisPromptLoader:
    """Loads and manages thesis generation prompt templates"""
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent / "prompts" / "thesis_generation"
        self._prompt_cache = {}
        self._file_timestamps = {}  # Track file modification times
    
    def load_prompt(self, prompt_type: str) -> str:
        """
        Load a specific prompt template
        
        Args:
            prompt_type: Type of prompt (e.g., 'bull_case', 'bear_case', 'objective')
            
        Returns:
            Prompt template string
        """
        # Auto-detect filename pattern
        prompt_file = self.prompts_dir / f"{prompt_type}_prompt.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        # Check if file has been modified since last cache
        current_mtime = prompt_file.stat().st_mtime
        cached_mtime = self._file_timestamps.get(prompt_type, 0)
        
        # Load from cache only if file hasn't been modified
        if prompt_type in self._prompt_cache and current_mtime <= cached_mtime:
            return self._prompt_cache[prompt_type]
        
        # File is new or modified, reload it
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
        
        # Update cache and timestamp
        self._prompt_cache[prompt_type] = prompt_template
        self._file_timestamps[prompt_type] = current_mtime
        
        return prompt_template
    
    def format_prompt(self, prompt_type: str, **kwargs) -> str:
        """
        Load and format a prompt template with provided data
        
        Args:
            prompt_type: Type of prompt to load
            **kwargs: Data to format into the prompt
            
        Returns:
            Formatted prompt string
        """
        template = self.load_prompt(prompt_type)
        
        # Handle missing keys gracefully
        safe_kwargs = self._prepare_safe_kwargs(kwargs)
        
        try:
            # Use regular format method
            return template.format(**safe_kwargs)
        except KeyError as e:
            print(f"KeyError in prompt formatting: Missing key {e}")
            raise ValueError(f"Missing required prompt parameter: {e}")
        except ValueError as e:
            print(f"ValueError in prompt formatting: {e}")
            # Debug: Print problematic values
            print("DEBUG: Checking for dict/list values in kwargs:")
            for key, value in safe_kwargs.items():
                if isinstance(value, (dict, list, tuple)):
                    print(f"  {key}: {type(value)} = {value}")
            # Try simple string replacement as fallback
            result = template
            for key, value in safe_kwargs.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
    
    def _prepare_safe_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare kwargs with safe defaults for missing values"""
        
        # Default values for common prompt parameters
        defaults = {
            'ticker': 'UNKNOWN',
            'company_type': 'Unknown',
            'analysis_type': 'Investment Analysis',
            'target_price': 0.0,
            'current_price_str': '$0.00',
            'focus_instructions': 'Provide balanced analysis',
            'price_expectation': 'explain price relationship',
            'market_cap': 0,
            'enterprise_value': 0,
            'beta': 'N/A',
            'pe_ratio': 'N/A',
            'ps_ratio': 'N/A',
            'pb_ratio': 'N/A',
            'ev_ebitda_multiple': 'N/A',
            'gross_margin': 0.0,
            'operating_margin': 0.0,
            'net_margin': 0.0,
            'roe': 0.0,
            'roa': 0.0,
            'revenue_growth': 0.0,
            'earnings_growth': 0.0,
            'debt_to_equity': 'N/A',
            'current_ratio': 'N/A',
            'quick_ratio': 'N/A',
            'free_cash_flow': 0,
            'cash_per_share': 'N/A',
            'book_value_per_share': 'N/A',
            'dividend_yield': 'N/A',
            'payout_ratio': 'N/A',
            'total_revenue': 0,
            'latest_net_income': 0,
            'latest_operating_income': 0,
            'latest_gross_profit': 0,
            'latest_operating_cf': 0,
            'latest_capital_expenditures': 0,
            'trailing_eps': 'N/A',
            'forward_eps': 'N/A',
            'shares_outstanding': 0,
            'float_shares': 0,
            'industry': 'N/A',
            'sector': 'N/A',
            'segment_info': '',
            'net_income_growth': 0.0,
            'operating_cf_growth': 0.0,
            'dcf_calculation_details': '',
            'startup_calculation_details': '',
            'average_target': 0.0,
            'consensus_strength': 'Medium',
            'method_agreement': 'Mixed',
            'strengths': 'No strengths identified',
            'risks': 'No risks identified',
            'key_developments': 'No recent developments',
            'sentiment_rating': 'Neutral',
            'news_count': 0,
            'news_sources_with_urls': 'No news sources available',
            'industry_outlook': 'Neutral',
            'competitive_position': 'Average',
            'regulatory_risk': 'Medium',
            'esg_score': 5.0,
            'business_segments': 'No segment data available',
            'revenue_breakdown': 'No revenue breakdown available',
            'data_source': 'N/A',
            'revenue_diversification': 'N/A',
            'thesis_type_lower': 'balanced',
            'financial_emphasis': 'provide balanced assessment',
            'financial_focus': 'overall financial health',
            'probability_assessment': 'balanced probability assessment',
            'value_risk_factors': 'value and risk factors',
            'news_focus': 'provide balanced news analysis',
            'news_impact': 'affect investment outlook',
            'industry_emphasis': 'balance opportunities and challenges',
            'regulatory_impact': 'affect investment attractiveness',
            'portfolio_emphasis': 'provide balanced portfolio assessment',
            'segment_analysis': 'both opportunities and challenges',
            'concentration_analysis': 'both benefits and risks',
            'valuation_scenario': 'balanced scenario modeling',
            'valuation_explanation': 'valuation relationship',
            'risk_return_calculation': 'balanced risk-return calculations',
            'risk_mitigation': 'risk mitigation and assessment',
            'expected_value_scenario': 'probability-weighted scenarios',
            'position_sizing': 'balanced position sizing',
            'recommendation_logic': 'balanced assessment leads to recommendation',
            'validation_emphasis': 'balanced case validation required',
            'financial_data_section': '',
            'methodology_section': '',
            'validation_results_section': '',
            'news_sentiment_section': '',
            'industry_context_section': '',
            'segment_revenue_section': '',
            'revenue_breakdown_section': '',
            'calculation_validation_section': ''
        }
        
        # Merge provided kwargs with defaults
        safe_kwargs = {**defaults, **kwargs}
        
        # Convert non-numeric values to strings, keep numbers as numbers for format specifiers
        for key, value in safe_kwargs.items():
            if isinstance(value, (list, tuple)):
                # Convert lists/tuples to comma-separated strings
                safe_kwargs[key] = ', '.join(str(item) for item in value)
            elif isinstance(value, dict):
                # Convert dicts to string representation
                safe_kwargs[key] = str(value)
            elif value is None:
                safe_kwargs[key] = 'N/A'
            elif isinstance(value, (int, float)):
                # Keep numeric values as numbers for format specifiers like :.2f, :,.0f
                safe_kwargs[key] = value
            else:
                safe_kwargs[key] = str(value)
        
        return safe_kwargs
    
    def list_available_prompts(self) -> list:
        """List all available prompt templates by scanning directory"""
        if not self.prompts_dir.exists():
            return []
        
        prompts = []
        for file in self.prompts_dir.glob("*_prompt.txt"):
            # Convert filename to prompt type (e.g., bull_case_prompt.txt -> bull_case)
            prompt_type = file.stem.replace('_prompt', '')
            prompts.append(prompt_type)
        
        return sorted(prompts)
    
    def clear_cache(self):
        """Clear the prompt cache to force reload of all prompts"""
        self._prompt_cache.clear()
        self._file_timestamps.clear()
    
    def get_prompt_info(self, prompt_type: str) -> Dict[str, Any]:
        """Get information about a specific prompt template"""
        prompt_file = self.prompts_dir / f"{prompt_type}_prompt.txt"
        
        if not prompt_file.exists():
            return {}
        
        stat = prompt_file.stat()
        
        return {
            'file_path': str(prompt_file),
            'file_size': stat.st_size,
            'modified_time': stat.st_mtime,
            'exists': True
        }

# Convenience functions for backward compatibility
def load_thesis_prompt(prompt_type: str) -> str:
    """Load a thesis prompt template"""
    loader = ThesisPromptLoader()
    return loader.load_prompt(prompt_type)

def format_thesis_prompt(prompt_type: str, **kwargs) -> str:
    """Format a thesis prompt template with data"""
    loader = ThesisPromptLoader()
    return loader.format_prompt(prompt_type, **kwargs)

def get_available_thesis_prompts() -> list:
    """Get list of available thesis prompt types"""
    loader = ThesisPromptLoader()
    return loader.list_available_prompts()
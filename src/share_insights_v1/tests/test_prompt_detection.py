#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.share_insights_v1.utils.prompt_loader import ThesisPromptLoader

def test_prompt_detection():
    loader = ThesisPromptLoader()
    available_prompts = loader.list_available_prompts()
    
    print("Available prompts detected:")
    for prompt in available_prompts:
        print(f"  - {prompt}")
    
    print(f"\nTotal prompts found: {len(available_prompts)}")
    
    # Test loading the new prompt
    try:
        qualitative_prompt = loader.load_prompt('qualitative_validation')
        print(f"\nQualitative validation prompt loaded successfully!")
        print(f"Length: {len(qualitative_prompt)} characters")
    except Exception as e:
        print(f"\nError loading qualitative_validation prompt: {e}")

if __name__ == "__main__":
    test_prompt_detection()
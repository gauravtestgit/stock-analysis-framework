#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'financial_analyst'))

from ai_analyzer import AIAnalyzer
import json

def test_guidance_extraction():
    """Test the guidance extraction functionality"""
    
    # Create sample earnings data with guidance information
    sample_earnings_data = {
        'earnings_call_text': """
        Management Commentary:
        We are pleased to report strong Q3 results. For Q4 2024, we expect revenue 
        to be in the range of $95-100 billion, representing growth of 8-12% year-over-year.
        We are raising our full-year 2024 EPS guidance to $6.15-6.25, up from our 
        previous guidance of $5.90-6.10. We remain optimistic about our market position
        and confident in our ability to deliver strong results. The outlook for 2025
        looks very promising with several new product launches planned.
        """,
        'revenue_growth': '12%',
        'earnings_surprise': '5%'
    }
    
    # Test the AI analyzer
    analyzer = AIAnalyzer()
    
    print("=== TESTING GUIDANCE EXTRACTION ===\n")
    
    # Test guidance extraction directly
    guidance_analysis = analyzer.extract_company_guidance(sample_earnings_data)
    print("Guidance Analysis:")
    print(json.dumps(guidance_analysis, indent=2))
    
    # Test full earnings analysis
    print("\n=== FULL EARNINGS ANALYSIS ===")
    earnings_analysis = analyzer.analyze_earnings_performance(sample_earnings_data)
    print("Earnings Analysis with Guidance:")
    print(json.dumps(earnings_analysis, indent=2))
    
    # Test guidance summary
    guidance_summary = analyzer._summarize_guidance(guidance_analysis)
    print(f"\nGuidance Summary: {guidance_summary}")
    
    # Test with comprehensive data
    print("\n=== COMPREHENSIVE AI INSIGHTS ===")
    comprehensive_data = {
        'ticker': 'TEST',
        'company_info': {'company_name': 'Test Company'},
        'earnings_data': sample_earnings_data,
        'financial_metrics': {
            'yearly_revenue_growth': 0.12,
            'quarterly_revenue_growth': 0.08,
            'current_revenue': '$85.5B'
        },
        'recent_news': [
            {
                'title': 'Company beats earnings expectations',
                'summary': 'Strong quarterly results exceed analyst forecasts',
                'publish_date': '2024-01-15'
            }
        ]
    }
    
    ai_insights = analyzer.generate_ai_insights(comprehensive_data)
    
    print("AI Insights with Guidance:")
    print(f"Ticker: {ai_insights['ticker']}")
    print(f"Overall Assessment: {ai_insights['overall_assessment']['summary']}")
    print(f"Confidence: {ai_insights['overall_assessment']['confidence_level']}")
    
    if 'guidance_analysis' in ai_insights['earnings_analysis']:
        print(f"\nGuidance Details:")
        guidance = ai_insights['earnings_analysis']['guidance_analysis']
        print(f"  Management Tone: {guidance.get('management_tone', 'Unknown')}")
        print(f"  Guidance Changes: {guidance.get('guidance_changes', [])}")
        print(f"  Revenue Guidance: {guidance.get('revenue_guidance', 'Not specified')}")
        print(f"  Earnings Guidance: {guidance.get('earnings_guidance', 'Not specified')}")
    
    if ai_insights.get('risk_flags'):
        print(f"\nRisk Flags: {', '.join(ai_insights['risk_flags'])}")
    
    if ai_insights.get('recommendation_adjustments'):
        adjustments = ai_insights['recommendation_adjustments']
        if adjustments.get('growth_rate_modifications'):
            print(f"\nGuidance-Based Adjustments:")
            for adj in adjustments['growth_rate_modifications']:
                print(f"  - {adj}")
    
    # Save full results
    with open('guidance_test_results.json', 'w') as f:
        json.dump(ai_insights, f, indent=2, default=str)
    
    print(f"\nFull results saved to guidance_test_results.json")

if __name__ == "__main__":
    test_guidance_extraction()
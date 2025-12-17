#!/usr/bin/env python3

import sys
import os
from datetime import datetime

from ..services.batch.batch_comparison_service import BatchComparisonService

def test_batch_comparison():
    """Test batch comparison service with sample CSV"""
    
    # Initialize comparison service
    comparison_service = BatchComparisonService()
    
    # Define paths
    input_csv = "./src/share_insights_v1/resources/stock_analyses/nzx_20251214191648_analysis.csv"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("🚀 Testing Batch Comparison Service...")
    
    # Test: Multi-Method Analyst Alignment Analysis
    print("\n📊 Multi-Method Analyst Alignment Analysis")
    output_path = f"./src/share_insights_v1/resources/stock_analyses/alignment/analyst_alignment_{timestamp}.csv"
    
    results = comparison_service.analyze_batch_csv(
        input_csv_path=input_csv,
        output_csv_path=output_path,
        # sample_size=100  # Test with first 100 stocks
    )
    
    print(f"✅ Analysis completed!")
    print(f"📁 Report saved")
    
    # Show method summary
    if results and 'method_summary' in results:
        print("\n📋 Method Summary:")
        for method, stats in results['method_summary'].items():
            print(f"  {method.upper()}: {stats['alignment_rate']:.1f}% alignment ({stats['total_comparisons']} comparisons)")
    
    # Show sample results
    if results and 'dcf_results' in results and results['dcf_results']:
        print("\n📊 Sample DCF Result:")
        sample = results['dcf_results'][0]
        print(f"  Ticker: {sample['ticker']}")
        print(f"  Our upside: {sample['our_upside']:+.1f}%")
        print(f"  Analyst upside: {sample['analyst_upside']:+.1f}%")
        print(f"  Alignment: {sample['alignment']}")
        print(f"  Deviation: {sample['deviation_score']:.1f}%")
    
    print("\n🎉 Test completed successfully!")

def test_alignment_calculation():
    """Test alignment calculation methods"""
    
    print("\n🧪 Testing Alignment Calculation...")
    
    comparison_service = BatchComparisonService()
    
    # Test alignment calculation
    test_cases = [
        # Investment aligned case (both bullish)
        {'our_upside': 25, 'analyst_upside': 30, 'expected': 'Investment_Aligned'},
        # Precise aligned case (close agreement)
        {'our_upside': 15, 'analyst_upside': 18, 'expected': 'Precise_Aligned'},
        # Moderate aligned case (within 25%)
        {'our_upside': 10, 'analyst_upside': 30, 'expected': 'Moderate_Aligned'},
        # Divergent case
        {'our_upside': 5, 'analyst_upside': 40, 'expected': 'Divergent'}
    ]
    
    for i, case in enumerate(test_cases, 1):
        alignment = comparison_service.determine_alignment(
            case['our_upside'], case['analyst_upside']
        )
        print(f"  Test {i}: {alignment} (expected: {case['expected']})")
        assert alignment == case['expected'], f"Test {i} failed: got {alignment}, expected {case['expected']}"
    
    print("✅ All alignment calculation tests passed!")

if __name__ == "__main__":
    test_batch_comparison()
    test_alignment_calculation()
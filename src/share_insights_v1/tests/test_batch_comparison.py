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
    input_csv = "./src/share_insights_v1/resources/stock_analyses/nasdaq_20251004124045.csv"
    output_csv = f"./src/share_insights_v1/resources/stock_analyses/nasdaq_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Analyze batch results
    print("Starting batch comparison analysis...")
    results = comparison_service.analyze_batch_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv
    )
    
    print(f"Comparison analysis completed for {len(results)} stocks")
    print(f"Results saved to {output_csv}")

if __name__ == "__main__":
    test_batch_comparison()
#!/usr/bin/env python3

import sys
import os
from datetime import datetime
# sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ..services.batch.batch_analysis_service import BatchAnalysisService

def test_batch_analysis():
    """Test batch analysis service with sample CSV"""
    
    # Initialize batch service
    batch_service = BatchAnalysisService()
    
    # Define paths
    filename = "asx"
    input_csv_dir = "./src/share_insights_v1/resources/stock_dump/"  # Assuming this exists in the root directory
    output_csv_dir = "./src/share_insights_v1/resources/stock_analyses/"
    date = datetime.now().strftime("%Y%m%d%H%M%S")
    input_csv = os.path.join(input_csv_dir, f"{filename}.csv")
    output_csv = os.path.join(output_csv_dir, f"{filename}_{date}_analysis.csv")
    
    # Process first 10 stocks as test
    print("Starting batch analysis...")
    results = batch_service.process_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        # max_stocks=10  # Limit for testing
    )
    
    print(f"Processed {len(results)} stocks")
    print(f"Results saved to {output_csv}")

if __name__ == "__main__":
    test_batch_analysis()
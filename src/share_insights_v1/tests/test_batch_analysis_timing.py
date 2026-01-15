#!/usr/bin/env python3

import sys
import os
from datetime import datetime
# sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ..services.batch.batch_analysis_service_quant import BatchAnalysisService

def test_batch_analysis():
    """Test batch analysis service with sample CSV"""
    os.environ['DEBUG'] = 'true'
    # Initialize batch service
    batch_service = BatchAnalysisService(save_to_db=True, enable_detailed_news_analysis=False)
    
    # Define paths
    filename = "single"
    input_csv_dir = "./src/share_insights_v1/resources/stock_dump/"  # Assuming this exists in the root directory
    output_csv_dir = "./src/share_insights_v1/resources/stock_analyses/"
    date = datetime.now().strftime("%Y%m%d%H%M%S")
    input_csv = os.path.join(input_csv_dir, f"{filename}.csv")
    output_csv = os.path.join(output_csv_dir, f"{filename}_{date}_analysis.csv")
    
    # Process first 10 stocks as test
    print("Starting batch analysis...")
    # batch_service.enable_detailed_news_analysis = False
    batch_service.process_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        # max_stocks=10  # Limit for testing
    )
    
    print(f"Results saved to {output_csv}")
    
    # Count processed stocks from output CSV
    import pandas as pd
    if os.path.exists(output_csv):
        df = pd.read_csv(output_csv)
        print(f"Processed {len(df)} stocks")
    else:
        print("No output file found")

if __name__ == "__main__":
    test_batch_analysis()
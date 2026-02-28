#!/usr/bin/env python3

import sys
import os
import argparse
from datetime import datetime

from ..services.batch.batch_analysis_service_quant import BatchAnalysisService

def test_batch_analysis(filename="single", max_workers=4):
    """Test batch analysis service with sample CSV"""
    
    # Initialize batch service with thread count
    batch_service = BatchAnalysisService(
        save_to_db=True, 
        enable_detailed_news_analysis=False,
        max_workers=max_workers
    )
    
    # Define paths
    input_csv_dir = "./src/share_insights_v1/resources/stock_dump/"
    output_csv_dir = "./src/share_insights_v1/resources/stock_analyses/"
    date = datetime.now().strftime("%Y%m%d%H%M%S")
    input_csv = os.path.join(input_csv_dir, f"{filename}.csv")
    output_csv = os.path.join(output_csv_dir, f"{filename}_{date}_analysis.csv")
    
    print(f"Starting batch analysis with {max_workers} threads...")
    batch_service.process_csv(
        input_csv_path=input_csv,
        output_csv_path=output_csv,
        exchange=filename.upper(),
        created_by="batch_user"
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
    parser = argparse.ArgumentParser(description='Batch stock analysis')
    parser.add_argument('filename', nargs='?', default='single', help='CSV filename (without .csv)')
    parser.add_argument('--threads', '-t', type=int, default=4, help='Number of threads (default: 4)')
    
    args = parser.parse_args()
    
    print(f"Running batch analysis on {args.filename} with {args.threads} threads")
    test_batch_analysis(args.filename, args.threads)
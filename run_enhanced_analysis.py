#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from batch_analyzer import process_file_in_batches
import pandas as pd

def main():
    """Run the enhanced batch analysis with analyst integration"""
    
    print("Starting Enhanced Stock Analysis with Professional Analyst Integration")
    print("=" * 70)
    
    # File paths
    input_file = "financial_analyst/resources/stock_analysis1.csv"
    output_file = "financial_analyst/resources/batch_analysis_results.csv"
    
    try:
        # Run batch analysis
        results = process_file_in_batches(input_file, batch_size=20)
        
        # Save results
        results_df = pd.DataFrame(results)
        results_df.to_csv(output_file, mode='a', header=False, index=False)
        
        print(f"\nAnalysis Complete!")
        print(f"Processed {len(results)} batches")
        print(f"Results saved to: {output_file}")
        
        # Display summary
        print("\nBatch Summary:")
        for result in results:
            print(f"Batch {result['Batch_Number']}: {result['Total_Stocks']} stocks, "
                  f"Avg Consensus Deviation: {result['Avg_Consensus_Deviation']}, "
                  f"Contrarian Ops: {result['High_Divergence_Count']}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
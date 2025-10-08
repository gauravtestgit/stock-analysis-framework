import sys
import os


from ..services.batch.bullish_convergence_service import BullishConvergenceService

def test_bullish_convergence_consolidation():
    """Test the bullish convergence consolidation service"""
    
    service = BullishConvergenceService()
    
    # Use current directory for output files
    base_dir = "./src/share_insights_v1/resources/stock_analyses/alignment/"
    
    print("Testing Bullish Convergence Consolidation Service...")
    print(f"Looking for method-specific files in: {base_dir}")
    
    # Run consolidation
    result_df = service.consolidate_bullish_convergent_stocks(base_dir)
    
    if result_df is not None:
        print("\nConsolidation Results:")
        print(f"Total stocks found: {len(result_df)}")
        print(f"Multi-method stocks: {len(result_df[result_df['methods_count'] > 1])}")
        
        print("\nTop 10 consolidated stocks:")
        print(result_df.head(10))
        
        # Show method distribution
        print("\nMethod distribution:")
        for method in ['DCF', 'TECHNICAL', 'COMPARABLE', 'STARTUP']:
            count = len(result_df[result_df[method] != ''])
            print(f"  {method}: {count} stocks")
    else:
        print("No bullish convergent files found. Run batch comparison analysis first.")

if __name__ == "__main__":
    test_bullish_convergence_consolidation()
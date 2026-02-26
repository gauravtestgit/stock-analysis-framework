#!/usr/bin/env python3
"""Debug script to test bulk analysis data retrieval"""

from src.share_insights_v1.services.storage.historical_analysis_service import HistoricalAnalysisService

def debug_bulk_analysis():
    service = HistoricalAnalysisService()
    
    print("Testing get_available_exchanges()...")
    try:
        exchanges = service.get_available_exchanges()
        print(f"SUCCESS - Exchanges: {exchanges}")
    except Exception as e:
        print(f"ERROR in get_available_exchanges: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting get_batch_jobs_by_exchange()...")
    try:
        batch_jobs = service.get_batch_jobs_by_exchange()
        print(f"SUCCESS - Found {len(batch_jobs)} batch jobs")
        for job in batch_jobs[:3]:  # Show first 3
            print(f"  - {job['batch_name']}: {job['total_stocks']} stocks ({job['completed_at']})")
    except Exception as e:
        print(f"ERROR in get_batch_jobs_by_exchange: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTesting get_bulk_analysis_data()...")
    try:
        bulk_data = service.get_bulk_analysis_data()
        print(f"SUCCESS - Bulk data keys: {bulk_data.keys() if bulk_data else 'Empty'}")
        if bulk_data:
            print(f"   Total analyses: {bulk_data.get('total_analyses', 0)}")
            if 'latest_run_info' in bulk_data:
                print(f"   Latest run: {bulk_data['latest_run_info']}")
            if 'convergence_analysis' in bulk_data:
                conv_data = bulk_data['convergence_analysis']
                print(f"   Convergent stocks: {len(conv_data)}")
                if conv_data:
                    print(f"   Sample convergent stock: {conv_data[0]}")
    except Exception as e:
        print(f"ERROR in get_bulk_analysis_data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_bulk_analysis()

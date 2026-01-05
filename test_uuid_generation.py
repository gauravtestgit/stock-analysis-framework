#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def test_uuid_generation():
    """Test if UUID generation is working in storage service"""
    try:
        from src.share_insights_v1.services.storage.analysis_storage_service import AnalysisStorageService
        
        # Create mock analysis results
        mock_results = {
            'analyses': {
                'dcf': {
                    'recommendation': 'Buy',
                    'predicted_price': 100.0,
                    'confidence': 'High'
                }
            },
            'final_recommendation': {
                'recommendation': 'Buy',
                'target_price': 100.0,
                'confidence': 'High'
            },
            'company_type': 'Large Cap',
            'financial_metrics': {
                'current_price': 90.0
            }
        }
        
        # Test storage service
        storage_service = AnalysisStorageService()
        stock_analysis_id = storage_service.store_comprehensive_analysis('TEST', mock_results)
        
        print(f"SUCCESS: UUID generated: {stock_analysis_id}")
        print(f"SUCCESS: UUID length: {len(stock_analysis_id)}")
        print(f"SUCCESS: UUID format valid: {'-' in stock_analysis_id}")
        
        return stock_analysis_id
        
    except Exception as e:
        print(f"ERROR: UUID generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_uuid_generation()
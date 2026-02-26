#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

def test_batch_analysis_id():
    """Test if batch_analysis_id generation is working"""
    try:
        # Test just the UUID generation part
        import uuid
        test_id = str(uuid.uuid4())
        print(f"Generated batch_analysis_id: {test_id}")
        print(f"Length: {len(test_id)}")
        print(f"Format valid: {len(test_id) == 36 and test_id.count('-') == 4}")
        
        # Test that we can import the storage service (without running it)
        try:
            from src.share_insights_v1.services.storage.analysis_storage_service import AnalysisStorageService
            print("Storage service import: SUCCESS")
        except Exception as e:
            print(f"Storage service import: FAILED - {e}")
        
        return test_id
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    test_batch_analysis_id()
"""
Validation script for Phase 2 - Thesis Database Storage
Tests thesis storage and retrieval functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.share_insights_v1.services.storage.thesis_storage_service import ThesisStorageService
from src.share_insights_v1.models.database import create_tables

def validate_db_storage():
    """Validate thesis database storage functionality"""
    
    print("🔍 Validating Thesis Database Storage...")
    
    # Ensure tables exist
    create_tables()
    print("✅ Database tables created/verified")
    
    # Initialize storage service
    storage_service = ThesisStorageService()
    
    # Test data
    test_ticker = "AAPL"
    test_thesis = "This is a test bull case thesis for Apple Inc. The company shows strong fundamentals..."
    test_type = "bull_case"
    
    # Test 1: Store thesis
    print(f"\n📝 Test 1: Storing thesis for {test_ticker}")
    thesis_id = storage_service.store_thesis(
        ticker=test_ticker,
        thesis_type=test_type,
        content=test_thesis,
        llm_provider="openai",
        llm_model="gpt-4",
        prompt_template="bull_case_prompt.txt"
    )
    
    if thesis_id:
        print(f"✅ Thesis stored successfully (ID: {thesis_id})")
    else:
        print("❌ Failed to store thesis")
        return False
    
    # Test 2: Retrieve latest thesis
    print(f"\n📖 Test 2: Retrieving latest thesis for {test_ticker}")
    latest = storage_service.get_latest_thesis(test_ticker, test_type)
    
    if latest and latest['content'] == test_thesis:
        print("✅ Latest thesis retrieved successfully")
        print(f"   - Type: {latest['thesis_type']}")
        print(f"   - LLM: {latest['llm_provider']} - {latest['llm_model']}")
    else:
        print("❌ Failed to retrieve latest thesis")
        return False
    
    # Test 3: Get thesis history
    print(f"\n📚 Test 3: Getting thesis history for {test_ticker}")
    history = storage_service.get_thesis_history(test_ticker)
    
    if history and len(history) > 0:
        print(f"✅ Thesis history retrieved ({len(history)} entries)")
        for i, thesis in enumerate(history[:2]):
            print(f"   {i+1}. {thesis['thesis_type']} - {thesis['created_at']}")
    else:
        print("❌ No thesis history found")
        return False
    
    # Test 4: Store chained thesis
    print(f"\n🔗 Test 4: Storing chained thesis")
    chained_thesis = "This is a follow-up bear case analysis based on previous bull case..."
    chained_id = storage_service.store_thesis(
        ticker=test_ticker,
        thesis_type="bear_case",
        content=chained_thesis,
        llm_provider="anthropic",
        llm_model="claude-3",
        prompt_template="bear_case_prompt.txt",
        previous_thesis_id=thesis_id
    )
    
    if chained_id:
        print(f"✅ Chained thesis stored successfully (ID: {chained_id})")
    else:
        print("❌ Failed to store chained thesis")
        return False
    
    print(f"\n🎉 All validation tests passed!")
    print(f"📊 Summary:")
    print(f"   - Stored 2 theses for {test_ticker}")
    print(f"   - Retrieved latest thesis successfully")
    print(f"   - Retrieved thesis history successfully")
    print(f"   - Chaining functionality working")
    
    return True

if __name__ == "__main__":
    success = validate_db_storage()
    if not success:
        sys.exit(1)
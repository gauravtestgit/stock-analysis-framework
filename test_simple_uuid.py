#!/usr/bin/env python3

import uuid

def test_simple_uuid():
    """Test basic UUID generation"""
    try:
        # Test UUID generation
        test_uuid = str(uuid.uuid4())
        print(f"Generated UUID: {test_uuid}")
        print(f"UUID length: {len(test_uuid)}")
        print(f"UUID format valid: {'-' in test_uuid and len(test_uuid) == 36}")
        
        # Test multiple UUIDs are unique
        uuid1 = str(uuid.uuid4())
        uuid2 = str(uuid.uuid4())
        print(f"UUIDs are unique: {uuid1 != uuid2}")
        
        return test_uuid
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None

if __name__ == "__main__":
    test_simple_uuid()
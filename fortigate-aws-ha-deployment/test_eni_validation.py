#!/usr/bin/env python3
"""
Test ENI ID validation function
"""

import re

def validate_eni_id(eni_id: str) -> bool:
    """Validate ENI ID format: eni-xxxxxxxxxxxxxxxxx"""
    if not eni_id:
        return True  # Empty is valid (optional)
    pattern = r'^eni-[0-9a-f]{17}$'
    return bool(re.match(pattern, eni_id))


def test_eni_validation():
    """Test ENI ID validation"""
    
    # Valid ENI IDs
    assert validate_eni_id("") == True, "Empty string should be valid"
    assert validate_eni_id("eni-0123456789abcdef0") == True, "Valid ENI ID should pass"
    assert validate_eni_id("eni-abcdef0123456789a") == True, "Valid ENI ID with letters should pass"
    assert validate_eni_id("eni-00000000000000000") == True, "Valid ENI ID with all zeros should pass"
    assert validate_eni_id("eni-fffffffffffffffff") == True, "Valid ENI ID with all f's should pass"
    
    # Invalid ENI IDs
    assert validate_eni_id("eni-") == False, "ENI ID without hex digits should fail"
    assert validate_eni_id("eni-123") == False, "ENI ID with too few digits should fail"
    assert validate_eni_id("eni-0123456789abcdef") == False, "ENI ID with 16 digits should fail"
    assert validate_eni_id("eni-0123456789abcdef00") == False, "ENI ID with 18 digits should fail"
    assert validate_eni_id("eni-0123456789ABCDEF0") == False, "ENI ID with uppercase should fail"
    assert validate_eni_id("eni-0123456789abcdefg") == False, "ENI ID with invalid character should fail"
    assert validate_eni_id("en-0123456789abcdef0") == False, "Invalid prefix should fail"
    assert validate_eni_id("0123456789abcdef0") == False, "Missing prefix should fail"
    assert validate_eni_id("eni 0123456789abcdef0") == False, "Space instead of dash should fail"
    
    print("✅ All ENI validation tests passed!")


if __name__ == "__main__":
    test_eni_validation()

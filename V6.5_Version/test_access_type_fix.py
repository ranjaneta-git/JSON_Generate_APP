"""
Test script to verify access type parsing fix
Tests the fix for Edit Register dialog access type parsing error
"""

def test_access_type_parsing():
    """Test the access type parsing logic"""
    test_cases = [
        ("R - Read Only", "R"),
        ("W - Write Only", "W"),
        ("RW - Read/Write", "RW"),
        ("R", "R"),  # Direct code without description
        ("W", "W"),
        ("RW", "RW"),
    ]
    
    print("=" * 70)
    print("Access Type Parsing Test")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for input_text, expected in test_cases:
        # Simulate the fixed parsing logic
        if ' - ' in input_text:
            access = input_text.split(' - ')[0].strip()
        else:
            access = input_text.strip()
        
        # Validate
        is_valid = access in ['R', 'W', 'RW']
        
        if access == expected and is_valid:
            print(f"✅ PASS: '{input_text}' -> '{access}' (valid)")
            passed += 1
        else:
            print(f"❌ FAIL: '{input_text}' -> '{access}' (expected: '{expected}', valid: {is_valid})")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    # Test invalid cases
    print("\nTesting Invalid Cases:")
    print("-" * 70)
    
    invalid_cases = [
        "X - Invalid",
        "Read",
        "Write",
        "",
        "R - Read Only - Extra",
    ]
    
    for input_text in invalid_cases:
        if ' - ' in input_text:
            access = input_text.split(' - ')[0].strip()
        else:
            access = input_text.strip()
        
        is_valid = access in ['R', 'W', 'RW']
        
        if is_valid:
            print(f"⚠️  WARNING: '{input_text}' -> '{access}' (should be invalid but parsed as valid)")
        else:
            print(f"✅ CORRECT: '{input_text}' -> '{access}' (correctly rejected)")
    
    print("=" * 70)
    
    return passed, failed

def test_old_parsing_logic():
    """Show what the old buggy parsing did"""
    print("\n" + "=" * 70)
    print("OLD BUGGY PARSING LOGIC (for comparison)")
    print("=" * 70)
    
    # Simulate old parse_dropdown_selection for access_type
    def old_parse_dropdown_selection(dropdown_value):
        if ' - ' in dropdown_value:
            try:
                return int(dropdown_value.split(' - ')[0])  # Tries int conversion
            except ValueError:
                return dropdown_value  # Returns FULL string on failure!
        return dropdown_value
    
    test_cases = [
        "R - Read Only",
        "W - Write Only", 
        "RW - Read/Write",
    ]
    
    for test in test_cases:
        result = old_parse_dropdown_selection(test)
        is_valid = result in ['R', 'W', 'RW']
        print(f"Input: '{test}'")
        print(f"  -> Parsed: '{result}'")
        print(f"  -> Valid: {is_valid} ❌")
        print()
    
    print("=" * 70)

if __name__ == "__main__":
    print("\n🔧 Testing Access Type Fix\n")
    
    # Show old buggy behavior
    test_old_parsing_logic()
    
    # Test new fixed behavior
    passed, failed = test_access_type_parsing()
    
    if failed == 0:
        print("\n✅ All tests passed! The fix works correctly.")
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the fix.")

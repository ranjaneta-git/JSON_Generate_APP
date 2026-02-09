"""
Test script to verify Lua Buffer fields are now saved/loaded correctly after the bug fix.

Run this after making changes in the GUI to verify fields are preserved.
"""

import json
import sys

def test_lua_fields_in_json(json_file):
    """Check if Lua Buffer fields exist in exported JSON"""
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    registers = data.get('registers', [])
    print(f"\n{'='*70}")
    print(f"Testing: {json_file}")
    print(f"Total registers: {len(registers)}")
    print(f"{'='*70}\n")
    
    # Check for Lua Buffer fields
    lua_fields = ['in_lua_buffer', 'lua_category', 'lbi_position', 'lbi_data_type', 'lua_buffer_note']
    transparent_fields = ['packet_num', 'packet_sa', 'packet_nrt', 'parameter_type']
    
    # Sample first 3 registers
    for i, reg in enumerate(registers[:3]):
        print(f"\n📝 Register {i+1} (Param ID: {reg.get('param_id')})")
        print(f"   Basic: Slave={reg.get('slave_id')}, FC={reg.get('fc')}, Addr={reg.get('address')}")
        
        # Check Lua fields
        lua_present = [field for field in lua_fields if field in reg]
        transparent_present = [field for field in transparent_fields if field in reg]
        
        if lua_present:
            print(f"   ✅ Lua Buffer fields: {lua_present}")
            for field in lua_present:
                print(f"      - {field}: {reg[field]}")
        else:
            print(f"   ❌ Lua Buffer fields: MISSING!")
        
        if transparent_present:
            print(f"   ✅ Transparent fields: {transparent_present}")
        else:
            print(f"   ⚠️ Transparent fields: MISSING")
    
    # Summary
    print(f"\n{'='*70}")
    registers_with_lua = sum(1 for reg in registers if any(field in reg for field in lua_fields))
    print(f"Summary: {registers_with_lua}/{len(registers)} registers have Lua Buffer fields")
    
    if registers_with_lua == len(registers):
        print("✅ SUCCESS: All registers have Lua Buffer fields!")
    elif registers_with_lua > 0:
        print("⚠️ PARTIAL: Some registers have Lua Buffer fields")
    else:
        print("❌ FAILURE: No registers have Lua Buffer fields (BUG NOT FIXED)")
    print(f"{'='*70}\n")
    
    return registers_with_lua == len(registers)

if __name__ == "__main__":
    # Test the user's original file (before fix)
    print("\n🔍 BEFORE FIX (Expected: MISSING fields):")
    test_lua_fields_in_json("c:\\Users\\DELL\\Downloads\\register_config_test_file.json")
    
    print("\n" + "="*70)
    print("\n📋 INSTRUCTIONS TO TEST THE FIX:")
    print("="*70)
    print("1. Run the Tkinter application (modbus_tkinter_app_v6.6_complete.py)")
    print("2. Import the test file OR add some registers manually")
    print("3. Set Lua Buffer fields (In Lua Buffer=Yes, Category=Equipment, etc.)")
    print("4. Export to a new JSON file (e.g., test_export_after_fix.json)")
    print("5. Run: python test_save_load_fix.py test_export_after_fix.json")
    print("6. Verify: The exported JSON should now have all Lua Buffer fields!")
    print("="*70)
    
    # If additional file provided as argument, test it
    if len(sys.argv) > 1:
        print("\n\n🔍 AFTER FIX (Testing user-provided file):")
        test_lua_fields_in_json(sys.argv[1])

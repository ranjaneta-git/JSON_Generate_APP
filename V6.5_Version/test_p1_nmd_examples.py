"""
Test P1.NMD Calculation with Examples 2-6
Verifies firmware-confirmed Σ(units×keys) formula
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from forward_engine import ForwardTransformationEngine

def calculate_expected_nmd(jka_list):
    """Calculate expected P1.NMD using firmware formula"""
    total = 0
    for jka in jka_list:
        if len(jka) >= 3:
            units = len(jka[1])
            keys = len(jka[2])
            total += units * keys
    return total

def test_example(example_name, expected_nmd):
    """Test a single example"""
    print(f"\n{'='*60}")
    print(f"Testing {example_name}")
    print(f"{'='*60}")
    
    try:
        # Load Register_Config
        reg_path = f"../Import_Examples/{example_name}/Register_Config.json"
        with open(reg_path, 'r') as f:
            reg_config = json.load(f)
        
        # Transform using forward engine
        engine = ForwardTransformationEngine()
        modbus_json, paramap_json = engine.transform(reg_config)
        
        # Check P1.NMD
        actual_nmd = paramap_json['P1']['NMD']
        jka_count = len(paramap_json['JKY']['JKA'])
        
        print(f"JKA Entries: {jka_count}")
        print(f"Expected P1.NMD: {expected_nmd}")
        print(f"Actual P1.NMD: {actual_nmd}")
        
        # Calculate verification
        calculated_nmd = calculate_expected_nmd(paramap_json['JKY']['JKA'])
        print(f"Calculated Σ(units×keys): {calculated_nmd}")
        
        # Show breakdown
        print("\nJKA Breakdown:")
        for i, jka in enumerate(paramap_json['JKY']['JKA'][:5], 1):  # First 5
            units = len(jka[1])
            keys = len(jka[2])
            print(f"  {i}. {jka[0]}: {units} units × {keys} keys = {units*keys}")
        if jka_count > 5:
            print(f"  ... ({jka_count - 5} more entries)")
        
        # Verify
        if actual_nmd == expected_nmd == calculated_nmd:
            print(f"\n✅ PASS: P1.NMD matches expected value ({expected_nmd})")
            return True
        else:
            print(f"\n❌ FAIL: P1.NMD mismatch")
            print(f"   Expected: {expected_nmd}")
            print(f"   Actual: {actual_nmd}")
            print(f"   Calculated: {calculated_nmd}")
            return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("P1.NMD Calculation Test Suite")
    print("Firmware Formula: Σ(JKeysNum × JEqNmNum)")
    print("="*60)
    
    tests = [
        ("Example2_163params", 97),
        ("Example3_25params", 20),
        ("Example4_56params", 42),
        ("Example5_25params_8E1", 21),
        ("Example6_21params", 13),
    ]
    
    results = []
    for example_name, expected_nmd in tests:
        passed = test_example(example_name, expected_nmd)
        results.append((example_name, passed))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for example_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {example_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

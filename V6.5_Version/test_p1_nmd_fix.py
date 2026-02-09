"""Test P1.NMD calculation fix with Examples 2-6"""
import json
import sys
from forward_engine import ForwardTransformationEngine

def test_example(example_name, expected_nmd):
    """Test P1.NMD calculation for an example"""
    print(f"\n{'='*60}")
    print(f"Testing {example_name}")
    print(f"{'='*60}")
    
    try:
        # Load Register_Config
        reg_config_path = f"../Import_Examples/{example_name}/Register_Config.json"
        with open(reg_config_path, 'r') as f:
            reg_config = json.load(f)
        
        # Transform using updated forward engine
        engine = ForwardTransformationEngine()
        modbus_json, paramap_json = engine.transform(reg_config)
        
        # Check P1.NMD
        actual_nmd = paramap_json["P1"]["NMD"]
        jka_count = len(paramap_json["JKY"]["JKA"])
        
        print(f"\nP1.NMD = {actual_nmd}")
        print(f"JKA count = {jka_count}")
        
        # Calculate expected NMD using firmware formula
        total_keys = 0
        print(f"\nJKA Breakdown:")
        for idx, jka in enumerate(paramap_json['JKY']['JKA'], 1):
            units = len(jka[1])
            keys = len(jka[2])
            product = units * keys
            total_keys += product
            print(f"  [{idx}] {jka[0]}: {units} units × {keys} keys = {product}")
        
        print(f"\nCalculated NMD (Σ units×keys) = {total_keys}")
        print(f"Expected NMD from example = {expected_nmd}")
        
        # Check results
        if actual_nmd == expected_nmd == total_keys:
            print(f"✅ PASS: P1.NMD matches expected value and firmware formula")
            return True
        elif actual_nmd == expected_nmd:
            print(f"⚠️  PARTIAL: P1.NMD matches expected but formula gives {total_keys}")
            return False
        elif actual_nmd == total_keys:
            print(f"⚠️  PARTIAL: P1.NMD matches formula but expected was {expected_nmd}")
            return False
        else:
            print(f"❌ FAIL: P1.NMD={actual_nmd}, expected={expected_nmd}, formula={total_keys}")
            return False
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Testing P1.NMD Calculation Fix")
    print("Firmware formula: P1.NMD = Σ(JKeysNum × JEqNmNum)")
    print("Confirmed by: Com_Lib.cpp:525")
    
    tests = [
        ("Example2_163params", 97),
        ("Example3_25params", 20),
        ("Example4_56params", 42),
        ("Example5_25params_8E1", 21),
        ("Example6_21params", 13),
    ]
    
    results = []
    for example, expected in tests:
        passed = test_example(example, expected)
        results.append((example, passed))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for example, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {example}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! P1.NMD calculation is correct.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

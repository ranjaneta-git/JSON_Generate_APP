"""
Comprehensive NMD Logic Verification
Tests both calculation and validation against firmware examples
"""

import json
from pathlib import Path

def calculate_nmd_from_jka(jka_list):
    """Calculate P1.NMD using firmware formula: Σ(units × keys)"""
    total = 0
    breakdown = []
    for idx, jka in enumerate(jka_list, 1):
        if len(jka) >= 3:
            name = jka[0]
            units = len(jka[1])
            keys = len(jka[2])
            product = units * keys
            total += product
            breakdown.append({
                'index': idx,
                'name': name,
                'units': units,
                'keys': keys,
                'product': product
            })
    return total, breakdown

def verify_example(example_path):
    """Verify NMD calculation for a firmware example"""
    paramap_path = Path(example_path) / "ParamMap_Config.json"
    
    if not paramap_path.exists():
        return None, f"File not found: {paramap_path}"
    
    try:
        with open(paramap_path, 'r') as f:
            data = json.load(f)
        
        # Extract data
        p1_nmd = data.get('P1', {}).get('NMD', 0)
        jka_list = data.get('JKY', {}).get('JKA', [])
        jka_count = len(jka_list)
        
        # Calculate expected NMD
        calculated_nmd, breakdown = calculate_nmd_from_jka(jka_list)
        
        # Verify
        is_correct = (p1_nmd == calculated_nmd)
        
        result = {
            'example': example_path.name,
            'p1_nmd': p1_nmd,
            'jka_count': jka_count,
            'calculated_nmd': calculated_nmd,
            'is_correct': is_correct,
            'breakdown': breakdown
        }
        
        return result, None
        
    except Exception as e:
        return None, str(e)

def print_verification_result(result):
    """Pretty print verification result"""
    print(f"\n{'='*70}")
    print(f"Example: {result['example']}")
    print(f"{'='*70}")
    print(f"JKA Entries:     {result['jka_count']}")
    print(f"P1.NMD (actual): {result['p1_nmd']}")
    print(f"Calculated NMD:  {result['calculated_nmd']}")
    
    if result['is_correct']:
        print(f"✅ CORRECT: P1.NMD matches Σ(units × keys)")
    else:
        print(f"❌ ERROR: P1.NMD does NOT match calculated value!")
    
    # Show breakdown (first 5 and last 2)
    print(f"\nJKA Breakdown (showing first 5 + last 2):")
    breakdown = result['breakdown']
    show_items = breakdown[:5]
    if len(breakdown) > 7:
        show_items.extend(breakdown[-2:])
        skipped = len(breakdown) - 7
    else:
        show_items = breakdown
        skipped = 0
    
    for item in show_items:
        if skipped > 0 and item['index'] == breakdown[-2]['index']:
            print(f"  ... ({skipped} more entries)")
        print(f"  {item['index']:2d}. {item['name']:25s} : "
              f"{item['units']} units × {item['keys']} keys = {item['product']}")
    
    print(f"\nTotal: Σ(units × keys) = {result['calculated_nmd']}")

def main():
    """Run comprehensive NMD verification"""
    print("="*70)
    print("NMD LOGIC VERIFICATION")
    print("Firmware Formula: P1.NMD = Σ(JKeysNum × JEqNmNum)")
    print("Reference: Com_Lib.cpp:525")
    print("="*70)
    
    # Test examples
    examples_dir = Path("../Import_Examples")
    examples = [
        "Example2_163params",
        "Example3_25params",
        "Example4_56params",
        "Example5_25params_8E1",
        "Example6_21params",
    ]
    
    results = []
    errors = []
    
    for example_name in examples:
        example_path = examples_dir / example_name
        result, error = verify_example(example_path)
        
        if error:
            errors.append((example_name, error))
        else:
            results.append(result)
            print_verification_result(result)
    
    # Summary
    print(f"\n{'='*70}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*70}")
    
    correct_count = sum(1 for r in results if r['is_correct'])
    total_count = len(results)
    
    for result in results:
        status = "✅ PASS" if result['is_correct'] else "❌ FAIL"
        print(f"{status}: {result['example']:25s} | "
              f"JKA={result['jka_count']:2d} → NMD={result['p1_nmd']:3d} "
              f"(calc={result['calculated_nmd']:3d})")
    
    if errors:
        print(f"\n❌ Errors:")
        for name, error in errors:
            print(f"  {name}: {error}")
    
    print(f"\n{'='*70}")
    if correct_count == total_count and not errors:
        print(f"🎉 ALL TESTS PASSED ({correct_count}/{total_count})")
        print("✅ NMD calculation logic is CORRECT")
        print("✅ Firmware formula: P1.NMD = Σ(units × keys) for all JKA entries")
    else:
        print(f"⚠️  TESTS: {correct_count}/{total_count} passed")
        if errors:
            print(f"⚠️  ERRORS: {len(errors)} examples failed to load")
    print(f"{'='*70}")
    
    # Firmware verification note
    print("\n📋 FIRMWARE VERIFICATION:")
    print("   Formula verified against Com_Lib.cpp:525")
    print("   MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum")
    print("   Where:")
    print("     - p_JKeysNum = len(JKA[1]) = number of units")
    print("     - p_JEqNmNum = len(JKA[2]) = number of keys")
    print("     - P1.NMD = total keys across ALL JKA entries")

if __name__ == "__main__":
    main()

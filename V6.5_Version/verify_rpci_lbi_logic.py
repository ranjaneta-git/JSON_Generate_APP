"""
Comprehensive RPCI and P3.LBI Verification
Tests against firmware examples to verify logic correctness
"""

import json
from pathlib import Path

def analyze_example(example_path):
    """Analyze RPCI and P3.LBI in a firmware example"""
    paramap_path = Path(example_path) / "ParamMap_Config.json"
    
    if not paramap_path.exists():
        return None, f"File not found: {paramap_path}"
    
    try:
        with open(paramap_path, 'r') as f:
            data = json.load(f)
        
        # Extract P2 data
        p2 = data.get('P2', {})
        p2_lbi = p2.get('LBI', [])
        p2_mpi = p2.get('MPI', [])
        p2_rpci = p2.get('RPCI', [])
        
        # Extract P3 data
        p3 = data.get('P3', {})
        p3_mdi = p3.get('MDI', [])
        p3_mpi = p3.get('MPI', [])
        p3_lbi = p3.get('LBI', [])
        
        # Extract P1 data
        p1 = data.get('P1', {})
        p1_nlb = p1.get('NLB', 0)
        
        result = {
            'example': example_path.name,
            'p1_nlb': p1_nlb,
            'p2_lbi': p2_lbi,
            'p2_mpi': p2_mpi,
            'p2_rpci': p2_rpci,
            'p3_mdi': p3_mdi,
            'p3_mpi': p3_mpi,
            'p3_lbi': p3_lbi,
        }
        
        return result, None
        
    except Exception as e:
        return None, str(e)

def verify_p2_logic(result):
    """Verify P2 logic"""
    print(f"\n{'='*70}")
    print(f"P2 (Lua Buffer) Analysis: {result['example']}")
    print(f"{'='*70}")
    
    p2_lbi = result['p2_lbi']
    p2_mpi = result['p2_mpi']
    p2_rpci = result['p2_rpci']
    p1_nlb = result['p1_nlb']
    
    print(f"P1.NLB (Total Lua Buffer): {p1_nlb}")
    print(f"P2.LBI (Sequential):       {p2_lbi}")
    print(f"  Length: {len(p2_lbi)}")
    print(f"P2.MPI (Equipment Params): {p2_mpi}")
    print(f"  Length: {len(p2_mpi)}")
    print(f"P2.RPCI (User Variables):  {p2_rpci}")
    print(f"  Length: {len(p2_rpci)}")
    
    # Verification checks
    errors = []
    warnings = []
    
    # Check 1: P2.LBI should be sequential [1, 2, 3, ...]
    expected_lbi = list(range(1, len(p2_lbi) + 1))
    if p2_lbi != expected_lbi:
        errors.append(f"P2.LBI is not sequential! Expected {expected_lbi[:5]}..., got {p2_lbi[:5]}...")
    else:
        print(f"✅ P2.LBI is sequential: [1..{len(p2_lbi)}]")
    
    # Check 2: len(P2.LBI) should equal len(P2.MPI) + len(P2.RPCI)
    expected_lbi_count = len(p2_mpi) + len(p2_rpci)
    if len(p2_lbi) != expected_lbi_count:
        errors.append(f"P2.LBI count mismatch! len(LBI)={len(p2_lbi)} but MPI+RPCI={expected_lbi_count}")
    else:
        print(f"✅ P2.LBI count matches MPI+RPCI: {len(p2_lbi)} = {len(p2_mpi)}+{len(p2_rpci)}")
    
    # Check 3: P1.NLB should equal len(P2.LBI)
    if p1_nlb != len(p2_lbi):
        errors.append(f"P1.NLB ({p1_nlb}) != len(P2.LBI) ({len(p2_lbi)})")
    else:
        print(f"✅ P1.NLB matches P2.LBI count: {p1_nlb}")
    
    # Check 4: P2.MPI should come first (LBI 1 to len(MPI))
    # Check 5: P2.RPCI should come after (LBI len(MPI)+1 to end)
    print(f"\n📊 Lua Buffer Layout:")
    print(f"  LBI 1-{len(p2_mpi)}: Equipment Parameters (P2.MPI)")
    if p2_rpci:
        print(f"  LBI {len(p2_mpi)+1}-{len(p2_lbi)}: User Variables (P2.RPCI)")
    else:
        print(f"  No User Variables (P2.RPCI is empty)")
    
    return errors, warnings

def verify_p3_logic(result):
    """Verify P3 logic"""
    print(f"\n{'='*70}")
    print(f"P3 (Cloud Output) Analysis: {result['example']}")
    print(f"{'='*70}")
    
    p3_mdi = result['p3_mdi']
    p3_mpi = result['p3_mpi']
    p3_lbi = result['p3_lbi']
    
    print(f"P3.MDI (Sequential):       {p3_mdi[:10]}{'...' if len(p3_mdi) > 10 else ''}")
    print(f"  Length: {len(p3_mdi)}")
    print(f"P3.MPI (Modbus Params):    {p3_mpi[:10]}{'...' if len(p3_mpi) > 10 else ''}")
    print(f"  Length: {len(p3_mpi)}")
    print(f"P3.LBI (Lua Calculated):   {p3_lbi}")
    print(f"  Length: {len(p3_lbi)}")
    
    # Verification checks
    errors = []
    warnings = []
    
    # Check 1: P3.MDI should be sequential [1, 2, 3, ...]
    expected_mdi = list(range(1, len(p3_mdi) + 1))
    if p3_mdi != expected_mdi:
        warnings.append(f"P3.MDI is not sequential! Expected {expected_mdi[:5]}..., got {p3_mdi[:5]}...")
    else:
        print(f"✅ P3.MDI is sequential: [1..{len(p3_mdi)}]")
    
    # Check 2: len(P3.MDI) should equal len(P3.MPI) + len(P3.LBI)
    # CRITICAL: This is the firmware requirement!
    expected_mdi_count = len(p3_mpi) + len(p3_lbi)
    if len(p3_mdi) != expected_mdi_count:
        errors.append(f"P3.MDI count mismatch! len(MDI)={len(p3_mdi)} but MPI+LBI={expected_mdi_count}")
    else:
        print(f"✅ P3.MDI count matches MPI+LBI: {len(p3_mdi)} = {len(p3_mpi)}+{len(p3_lbi)}")
    
    # Check 3: P3.LBI analysis
    if p3_lbi:
        print(f"\n⚠️  P3.LBI is NOT empty: {p3_lbi}")
        print(f"   This means some cloud outputs are Lua-calculated, not direct Modbus reads")
        # Check that LBI values reference valid P2.LBI positions
        p2_lbi = result['p2_lbi']
        for lbi_val in p3_lbi:
            if lbi_val < 1 or lbi_val > len(p2_lbi):
                errors.append(f"P3.LBI contains invalid reference: {lbi_val} (P2.LBI range is 1-{len(p2_lbi)})")
        if not errors:
            print(f"   ✅ All P3.LBI values reference valid P2.LBI positions")
    else:
        print(f"✅ P3.LBI is empty (all cloud outputs from direct Modbus reads)")
    
    # Check 4: Firmware interpretation
    print(f"\n📋 Firmware Interpretation:")
    print(f"   - First {len(p3_mpi)} MDI entries → P3.MPI (direct Modbus parameter reads)")
    if p3_lbi:
        print(f"   - Last {len(p3_lbi)} MDI entries → P3.LBI (Lua-calculated values from P2 buffer)")
    else:
        print(f"   - No Lua-calculated outputs")
    
    return errors, warnings

def main():
    """Run comprehensive RPCI and P3.LBI verification"""
    print("="*70)
    print("RPCI AND P3.LBI LOGIC VERIFICATION")
    print("Verifying against firmware examples")
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
    load_errors = []
    
    for example_name in examples:
        example_path = examples_dir / example_name
        result, error = analyze_example(example_path)
        
        if error:
            load_errors.append((example_name, error))
        else:
            results.append(result)
    
    # Analyze each example
    all_errors = []
    all_warnings = []
    
    for result in results:
        p2_errors, p2_warnings = verify_p2_logic(result)
        p3_errors, p3_warnings = verify_p3_logic(result)
        
        if p2_errors or p3_errors:
            all_errors.extend([(result['example'], e) for e in p2_errors + p3_errors])
        if p2_warnings or p3_warnings:
            all_warnings.extend([(result['example'], w) for w in p2_warnings + p3_warnings])
    
    # Summary
    print(f"\n{'='*70}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*70}")
    
    if load_errors:
        print(f"\n❌ Load Errors:")
        for name, error in load_errors:
            print(f"  {name}: {error}")
    
    if all_errors:
        print(f"\n❌ ERRORS FOUND ({len(all_errors)}):")
        for example, error in all_errors:
            print(f"  [{example}] {error}")
    else:
        print(f"✅ No errors found!")
    
    if all_warnings:
        print(f"\n⚠️  WARNINGS ({len(all_warnings)}):")
        for example, warning in all_warnings:
            print(f"  [{example}] {warning}")
    
    # Final verdict
    print(f"\n{'='*70}")
    if not all_errors and not load_errors:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print("✅ RPCI logic is CORRECT")
        print("✅ P3.LBI logic is CORRECT")
        print(f"{'='*70}")
        print("\n📋 KEY FINDINGS:")
        print("   P2.RPCI: User Variable parameters in Lua Buffer")
        print("   P2.MPI:  Equipment parameters in Lua Buffer")
        print("   P2.LBI:  Sequential index [1..N] for both MPI and RPCI")
        print("   P1.NLB:  Total Lua Buffer size = len(MPI) + len(RPCI)")
        print("")
        print("   P3.MPI:  Direct Modbus parameter reads for cloud output")
        print("   P3.LBI:  Lua-calculated values for cloud output (usually empty)")
        print("   P3.MDI:  Sequential index [1..M] for both MPI and LBI")
        print("   Formula: len(P3.MDI) = len(P3.MPI) + len(P3.LBI)")
    else:
        print("⚠️  VERIFICATION ISSUES FOUND - Review errors above")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

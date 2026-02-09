"""
Comprehensive P2.MPI and P3.MPI Logic Analysis
Verifies population logic against firmware examples
"""

import json
from pathlib import Path

def analyze_mpi_logic(example_path):
    """Analyze P2.MPI and P3.MPI in firmware example"""
    paramap_path = Path(example_path) / "ParamMap_Config.json"
    
    try:
        with open(paramap_path, 'r') as f:
            data = json.load(f)
        
        p2 = data.get('P2', {})
        p3 = data.get('P3', {})
        p2_mpi = p2.get('MPI', [])
        p2_rpci = p2.get('RPCI', [])
        p3_mpi = p3.get('MPI', [])
        p3_lbi = p3.get('LBI', [])
        
        print(f"\n{'='*80}")
        print(f"Example: {example_path.name}")
        print(f"{'='*80}")
        
        # P2.MPI Analysis
        print(f"\n📋 P2.MPI (Lua Buffer - Equipment Parameters):")
        print(f"   Length: {len(p2_mpi)}")
        print(f"   Values: {p2_mpi[:10]}{'...' if len(p2_mpi) > 10 else ''}")
        print(f"   Purpose: Equipment parameters for Lua Buffer processing")
        print(f"   LBI Positions: 1 to {len(p2_mpi)}")
        
        # P2.RPCI Analysis
        print(f"\n📋 P2.RPCI (Lua Buffer - User Variables):")
        print(f"   Length: {len(p2_rpci)}")
        print(f"   Values: {p2_rpci}")
        if p2_rpci:
            print(f"   LBI Positions: {len(p2_mpi)+1} to {len(p2_mpi)+len(p2_rpci)}")
        
        # P3.MPI Analysis
        print(f"\n📋 P3.MPI (Cloud Output - Equipment Parameters):")
        print(f"   Length: {len(p3_mpi)}")
        print(f"   Values: {p3_mpi[:10]}{'...' if len(p3_mpi) > 10 else ''}")
        print(f"   Purpose: Equipment parameters sent to cloud")
        
        # P3.LBI Analysis
        print(f"\n📋 P3.LBI (Cloud Output - User Variables):")
        print(f"   Length: {len(p3_lbi)}")
        print(f"   Values: {p3_lbi}")
        if p3_lbi:
            print(f"   Purpose: User Variable LBI positions sent to cloud")
        
        # Relationship Analysis
        print(f"\n🔍 RELATIONSHIP ANALYSIS:")
        
        # Check if P3.MPI is subset of P2.MPI
        p2_mpi_set = set(p2_mpi)
        p3_mpi_set = set(p3_mpi)
        
        p3_in_p2 = p3_mpi_set.issubset(p2_mpi_set)
        p3_not_in_p2 = p3_mpi_set - p2_mpi_set
        p2_not_in_p3 = p2_mpi_set - p3_mpi_set
        
        print(f"\n1. P3.MPI vs P2.MPI:")
        print(f"   Are ALL P3.MPI params in P2.MPI? {'✅ YES' if p3_in_p2 else '❌ NO'}")
        
        if not p3_in_p2:
            print(f"   P3.MPI params NOT in P2.MPI: {sorted(p3_not_in_p2)[:10]}")
        
        if p2_not_in_p3:
            print(f"   P2.MPI params NOT in P3.MPI: {len(p2_not_in_p3)} params")
            print(f"   ℹ️  These are Lua Buffer params that DON'T go to cloud")
        
        # Check if P3.LBI matches P2.RPCI positions
        print(f"\n2. P3.LBI vs P2.RPCI:")
        if p3_lbi and p2_rpci:
            expected_lbi = list(range(len(p2_mpi)+1, len(p2_mpi)+len(p2_rpci)+1))
            if p3_lbi == expected_lbi:
                print(f"   ✅ P3.LBI matches ALL P2.RPCI positions: {p3_lbi}")
            else:
                print(f"   ⚠️  P3.LBI = {p3_lbi}")
                print(f"   Expected: {expected_lbi}")
        elif not p3_lbi and not p2_rpci:
            print(f"   ✅ No User Variables (both empty)")
        elif not p3_lbi and p2_rpci:
            print(f"   ⚠️  P2.RPCI exists but P3.LBI empty (User Vars not sent to cloud)")
        
        # Totals
        print(f"\n3. Totals:")
        print(f"   Lua Buffer Total: {len(p2_mpi)} Equipment + {len(p2_rpci)} User Vars = {len(p2_mpi)+len(p2_rpci)}")
        print(f"   Cloud Output Total: {len(p3_mpi)} Equipment + {len(p3_lbi)} User Vars = {len(p3_mpi)+len(p3_lbi)}")
        
        return {
            'example': example_path.name,
            'p2_mpi_count': len(p2_mpi),
            'p2_rpci_count': len(p2_rpci),
            'p3_mpi_count': len(p3_mpi),
            'p3_lbi_count': len(p3_lbi),
            'p3_in_p2': p3_in_p2,
            'p3_not_in_p2_count': len(p3_not_in_p2),
            'p2_not_in_p3_count': len(p2_not_in_p3),
        }
        
    except Exception as e:
        print(f"\n❌ Error analyzing {example_path.name}: {e}")
        return None

def main():
    print("="*80)
    print("P2.MPI AND P3.MPI LOGIC ANALYSIS")
    print("="*80)
    
    examples_dir = Path("../Import_Examples")
    examples = [
        "Example2_163params",
        "Example3_25params",
        "Example4_56params",
        "Example5_25params_8E1",
        "Example6_21params",
    ]
    
    results = []
    
    for example_name in examples:
        result = analyze_mpi_logic(examples_dir / example_name)
        if result:
            results.append(result)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY TABLE")
    print(f"{'='*80}")
    print(f"{'Example':<25} {'P2.MPI':<10} {'P2.RPCI':<10} {'P3.MPI':<10} {'P3.LBI':<10} {'P3⊆P2':<8}")
    print(f"{'-'*80}")
    
    for r in results:
        subset_mark = '✅' if r['p3_in_p2'] else '❌'
        print(f"{r['example']:<25} {r['p2_mpi_count']:<10} {r['p2_rpci_count']:<10} {r['p3_mpi_count']:<10} {r['p3_lbi_count']:<10} {subset_mark:<8}")
    
    # Key Findings
    print(f"\n{'='*80}")
    print("KEY FINDINGS")
    print(f"{'='*80}")
    
    print("""
🎯 P2.MPI (Lua Buffer - Equipment):
   - Contains param IDs of Equipment parameters
   - Parameters marked: in_lua_buffer=Yes AND lua_buffer_category=Equipment
   - Used by Lua script for control logic
   - Positions: LBI 1 to len(P2.MPI)
   - ALL parameters in Lua Buffer (both cloud and non-cloud)

🎯 P2.RPCI (Lua Buffer - User Variables):
   - Contains param IDs of User Variable parameters
   - Parameters marked: in_lua_buffer=Yes AND lua_buffer_category=User Variable
   - Used by Lua script for custom calculations
   - Positions: LBI len(P2.MPI)+1 to len(P2.MPI)+len(P2.RPCI)
   - ALL User Variables in Lua Buffer

🎯 P3.MPI (Cloud Output - Equipment):
   - Contains param IDs of Equipment parameters for cloud
   - SUBSET of P2.MPI (only those with cloud=Yes)
   - Direct Modbus parameter reads
   - Firmware reads these from Modbus, processes in Lua, sends to cloud
   - Parameters may or may not be in Lua Buffer

🎯 P3.LBI (Cloud Output - User Variables):
   - Contains LBI POSITIONS (not param IDs!) of User Variables
   - Points to P2.RPCI positions in Lua Buffer
   - User Variables calculated by Lua script, sent to cloud
   - Values: [len(P2.MPI)+1, len(P2.MPI)+2, ...]

📊 RELATIONSHIP:
   P2.MPI ⊇ P3.MPI (P2 has all Lua Buffer params, P3 has cloud-only subset)
   P3.LBI → P2.RPCI positions (if User Variables need cloud output)
   
   Lua Buffer Total = P2.MPI + P2.RPCI
   Cloud Output Total = P3.MPI + P3.LBI
""")
    
    # Check for anomalies
    anomalies = [r for r in results if not r['p3_in_p2']]
    if anomalies:
        print(f"\n⚠️  ANOMALIES DETECTED:")
        for r in anomalies:
            print(f"   {r['example']}: {r['p3_not_in_p2_count']} params in P3.MPI but NOT in P2.MPI")
        print(f"   This means some cloud params bypass Lua Buffer (direct Modbus→Cloud)")
    else:
        print(f"\n✅ No anomalies - All P3.MPI params are in P2.MPI (cloud params processed by Lua)")

if __name__ == "__main__":
    main()

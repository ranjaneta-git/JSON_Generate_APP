"""
Deep analysis of P3.LBI logic from firmware examples
"""

import json
from pathlib import Path

def analyze_p3_lbi_pattern(example_path):
    """Analyze P3.LBI pattern in firmware example"""
    paramap_path = Path(example_path) / "ParamMap_Config.json"
    
    with open(paramap_path, 'r') as f:
        data = json.load(f)
    
    p1 = data['P1']
    p2 = data['P2']
    p3 = data['P3']
    
    print(f"\n{'='*70}")
    print(f"Example: {example_path.name}")
    print(f"{'='*70}")
    
    # P2 analysis
    print(f"\nP2 (Lua Buffer):")
    print(f"  LBI:  {p2['LBI']}")
    print(f"  MPI:  {p2['MPI'][:10]}{'...' if len(p2['MPI']) > 10 else ''} (len={len(p2['MPI'])})")
    print(f"  RPCI: {p2['RPCI']} (len={len(p2['RPCI'])})")
    
    # Critical observation
    print(f"\n  🔍 Lua Buffer Layout:")
    print(f"     LBI 1-{len(p2['MPI'])}: Equipment Parameters (P2.MPI)")
    if p2['RPCI']:
        rpci_start = len(p2['MPI']) + 1
        rpci_end = len(p2['LBI'])
        print(f"     LBI {rpci_start}-{rpci_end}: User Variables (P2.RPCI)")
    
    # P3 analysis  
    print(f"\nP3 (Cloud Output):")
    print(f"  MDI: [1..{len(p3['MDI'])}] (len={len(p3['MDI'])})")
    print(f"  MPI: {p3['MPI'][:10]}{'...' if len(p3['MPI']) > 10 else ''} (len={len(p3['MPI'])})")
    print(f"  LBI: {p3['LBI']} (len={len(p3['LBI'])})")
    
    # CRITICAL PATTERN
    if p3['LBI']:
        print(f"\n  🔍 P3.LBI Pattern Analysis:")
        print(f"     P3.LBI = {p3['LBI']}")
        print(f"     P2.LBI range = [1..{len(p2['LBI'])}]")
        print(f"     P2.RPCI positions in P2.LBI = [{len(p2['MPI'])+1}..{len(p2['LBI'])}]")
        
        # Check if P3.LBI points to RPCI positions
        rpci_lbi_start = len(p2['MPI']) + 1
        all_in_rpci_range = all(lbi >= rpci_lbi_start for lbi in p3['LBI'])
        
        if all_in_rpci_range:
            print(f"     ✅ ALL P3.LBI values point to P2.RPCI positions!")
            print(f"        This means: User Variables that need cloud output")
        else:
            print(f"     ⚠️  Some P3.LBI values point outside P2.RPCI range")
        
        # Verify count matches
        if len(p3['LBI']) == len(p2['RPCI']):
            print(f"     ✅ len(P3.LBI) = len(P2.RPCI) = {len(p3['LBI'])}")
            print(f"        This means: ALL User Variables go to cloud")
        else:
            print(f"     ⚠️  len(P3.LBI) = {len(p3['LBI'])} but len(P2.RPCI) = {len(p2['RPCI'])}")
    else:
        print(f"\n  ✅ P3.LBI is empty (no User Variables need cloud output)")
    
    # Verify MDI formula
    expected_mdi = len(p3['MPI']) + len(p3['LBI'])
    if len(p3['MDI']) == expected_mdi:
        print(f"\n  ✅ len(P3.MDI) = len(P3.MPI) + len(P3.LBI) = {len(p3['MPI'])} + {len(p3['LBI'])} = {expected_mdi}")
    else:
        print(f"\n  ❌ MDI count mismatch!")

def main():
    print("="*70)
    print("P3.LBI PATTERN ANALYSIS")
    print("="*70)
    
    examples_dir = Path("../Import_Examples")
    examples = [
        "Example2_163params",  # P3.LBI = []
        "Example3_25params",   # P3.LBI = [11]
        "Example4_56params",   # P3.LBI = []
        "Example5_25params_8E1",  # P3.LBI = [11, 12]
        "Example6_21params",   # P3.LBI = [16, 17, 18, 19]
    ]
    
    for example_name in examples:
        analyze_p3_lbi_pattern(examples_dir / example_name)
    
    print(f"\n{'='*70}")
    print("CONCLUSIONS")
    print(f"{'='*70}")
    print("""
🎯 FIRMWARE REQUIREMENT DISCOVERED:

P3.LBI = LBI positions of User Variables (P2.RPCI) that need cloud output

Pattern:
1. User Variables are stored at END of P2.LBI
2. P2.RPCI contains param IDs of User Variables
3. If User Variables need cloud output, their LBI positions go in P3.LBI
4. P3.LBI contains P2.LBI position numbers (NOT param IDs!)

Formula:
- P2.RPCI positions = [len(P2.MPI)+1 ... len(P2.LBI)]
- If all User Variables→cloud: P3.LBI = P2.RPCI positions
- If no User Variables→cloud: P3.LBI = []

Examples verified:
✅ Example2: No User Variables need cloud → P3.LBI = []
✅ Example3: 1 User Variable needs cloud → P3.LBI = [11] (RPCI at LBI 11)
✅ Example5: 2 User Variables need cloud → P3.LBI = [11,12] (RPCI at LBI 11-12)
✅ Example6: 4 User Variables need cloud → P3.LBI = [16,17,18,19] (RPCI at LBI 16-19)
""")

if __name__ == "__main__":
    main()

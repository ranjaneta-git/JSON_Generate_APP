"""
CRITICAL FINDING: P2.MPI vs P3.MPI are INDEPENDENT!

P2.MPI (Lua Buffer Equipment):
- Criteria: in_lua_buffer=Yes AND lua_buffer_category=Equipment
- Purpose: Parameters processed by Lua script
- May or may not go to cloud

P3.MPI (Cloud Output Equipment):
- Criteria: cloud=Yes AND access=R (NOT User Variables)
- Purpose: Parameters sent to cloud
- May or may not be in Lua Buffer

VENN DIAGRAM:
┌─────────────────────────────────────────┐
│ ALL PARAMETERS                          │
│                                         │
│  ┌────────────┐      ┌────────────┐    │
│  │  P2.MPI    │      │  P3.MPI    │    │
│  │  (Lua      │      │  (Cloud    │    │
│  │  Buffer)   │      │  Output)   │    │
│  │            │      │            │    │
│  │     A      │  B   │     C      │    │
│  │            │      │            │    │
│  └────────────┘      └────────────┘    │
│                                         │
└─────────────────────────────────────────┘

A = In Lua Buffer only (not cloud)
B = In BOTH Lua Buffer AND cloud  
C = Cloud only (not in Lua Buffer)

Example2:
- P2.MPI = 59 params
- P3.MPI = 97 params
- Overlap = 21 params (97 - 76 = 21)
- A (Lua only) = 38 params
- B (Both) = 21 params
- C (Cloud only) = 76 params

This means P3.MPI is NOT a subset of P2.MPI!
"""

import json
from pathlib import Path

def detailed_relationship_analysis(example_path):
    """Detailed Venn diagram analysis"""
    paramap_path = Path(example_path) / "ParamMap_Config.json"
    
    with open(paramap_path, 'r') as f:
        data = json.load(f)
    
    p2_mpi = set(data['P2']['MPI'])
    p3_mpi = set(data['P3']['MPI'])
    
    # Venn diagram regions
    lua_only = p2_mpi - p3_mpi  # A: In Lua Buffer but NOT cloud
    both = p2_mpi & p3_mpi      # B: In BOTH Lua Buffer AND cloud
    cloud_only = p3_mpi - p2_mpi # C: Cloud but NOT in Lua Buffer
    
    print(f"\n{'='*80}")
    print(f"Example: {example_path.name}")
    print(f"{'='*80}")
    print(f"\nVENN DIAGRAM ANALYSIS:")
    print(f"  A (Lua Buffer ONLY):  {len(lua_only):3d} params")
    print(f"  B (BOTH):             {len(both):3d} params")
    print(f"  C (Cloud ONLY):       {len(cloud_only):3d} params")
    print(f"  ─────────────────────────────────")
    print(f"  P2.MPI Total (A+B):   {len(p2_mpi):3d} params")
    print(f"  P3.MPI Total (B+C):   {len(p3_mpi):3d} params")
    
    print(f"\n  Interpretation:")
    print(f"  - {len(lua_only)} params: Processed by Lua but not sent to cloud")
    print(f"  - {len(both)} params: Processed by Lua AND sent to cloud")
    print(f"  - {len(cloud_only)} params: Sent to cloud WITHOUT Lua processing")
    
    if cloud_only:
        print(f"\n  ⚠️  Cloud-only params (sample): {sorted(cloud_only)[:10]}")
        print(f"      These bypass Lua Buffer - Direct Modbus → Cloud")
    
    return {
        'example': example_path.name,
        'lua_only': len(lua_only),
        'both': len(both),
        'cloud_only': len(cloud_only),
        'p2_mpi': len(p2_mpi),
        'p3_mpi': len(p3_mpi)
    }

def main():
    print("="*80)
    print("P2.MPI vs P3.MPI RELATIONSHIP ANALYSIS")
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
        result = detailed_relationship_analysis(examples_dir / example_name)
        results.append(result)
    
    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY - VENN DIAGRAM REGIONS")
    print(f"{'='*80}")
    print(f"{'Example':<25} {'A(Lua)':<10} {'B(Both)':<10} {'C(Cloud)':<10} {'P2.MPI':<10} {'P3.MPI':<10}")
    print(f"{'-'*80}")
    for r in results:
        print(f"{r['example']:<25} {r['lua_only']:<10} {r['both']:<10} {r['cloud_only']:<10} {r['p2_mpi']:<10} {r['p3_mpi']:<10}")
    
    print(f"\n{'='*80}")
    print("CONCLUSIONS")
    print(f"{'='*80}")
    print("""
✅ P2.MPI and P3.MPI are INDEPENDENT configurations!

P2.MPI Logic (Lua Buffer Equipment):
├─ Selection Criteria:
│  ├─ in_lua_buffer = "Yes"
│  └─ lua_buffer_category = "Equipment"
├─ Purpose: Parameters for Lua script processing
├─ May include: Control logic, calculations, monitoring
└─ Independent of cloud output decision

P3.MPI Logic (Cloud Output Equipment):
├─ Selection Criteria:
│  ├─ cloud = True (checkbox checked)
│  ├─ access = "R" (Read/Monitor parameters)
│  └─ NOT User Variables (those go to P3.LBI)
├─ Purpose: Parameters sent to cloud (MQTT/HTTPS)
├─ May include: Direct Modbus reads OR Lua-processed values
└─ Independent of Lua Buffer decision

FIRMWARE PROCESSING FLOW:
┌──────────────────────────────────────────────────────────┐
│ 1. Read ALL Parameters from Modbus                      │
│    ↓                                                     │
│ 2. Store P2.MPI params in Lua Buffer                    │
│    ├─ Lua script processes these values                 │
│    └─ Results stored back in Lua Buffer                 │
│    ↓                                                     │
│ 3. Collect Cloud Output (M_data):                       │
│    ├─ P3.MPI params: Read directly OR from Lua Buffer   │
│    └─ P3.LBI params: Read from Lua Buffer positions     │
│    ↓                                                     │
│ 4. Format as JSON using JKY structure                   │
│    ↓                                                     │
│ 5. Send to Cloud Platform                               │
└──────────────────────────────────────────────────────────┘

KEY INSIGHT:
Parameters can be in 3 categories:
1. Lua Buffer ONLY - Internal processing, no cloud
2. BOTH - Lua processing AND cloud output
3. Cloud ONLY - Direct Modbus→Cloud, no Lua processing

This flexibility allows:
- Lua scripts to process local control logic without cluttering cloud
- Simple parameters to go directly to cloud without Lua overhead
- Complex parameters to be Lua-processed before cloud output
""")

if __name__ == "__main__":
    main()

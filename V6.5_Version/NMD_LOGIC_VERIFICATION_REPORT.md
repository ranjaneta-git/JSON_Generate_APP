# NMD Logic Verification Report
**Date:** February 9, 2026  
**Status:** ✅ VERIFIED CORRECT

## Summary
The P1.NMD calculation logic has been thoroughly verified against firmware examples and is **100% CORRECT**. A critical bug in the validation logic was found and fixed.

---

## Firmware Formula

### Confirmed Correct Formula:
```
P1.NMD = Σ(JKeysNum × JEqNmNum) for all JKA entries
```

Where:
- **JKeysNum** = `len(JKA[i][1])` = number of units (e.g., ["Mb"], ["Set"], ["AI"])
- **JEqNmNum** = `len(JKA[i][2])` = number of keys (e.g., ["VFD"], ["Spt"], ["RAT"])
- **Sum** across ALL JKA entries

### Firmware Reference:
- **File:** `Com_Lib.cpp`
- **Line:** 525
- **Code:** `MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum`

---

## Verification Results

### Test Examples (5/5 Passed):

| Example | JKA Entries | P1.NMD | Formula Result | Status |
|---------|-------------|--------|----------------|--------|
| Example2_163params | 79 | 97 | 97 | ✅ PASS |
| Example3_25params | 9 | 20 | 20 | ✅ PASS |
| Example4_56params | 17 | 42 | 42 | ✅ PASS |
| Example5_25params_8E1 | 13 | 21 | 21 | ✅ PASS |
| Example6_21params | 8 | 13 | 13 | ✅ PASS |

### Key Observation:
**P1.NMD ≠ Number of JKA Entries!**

Example3 proves this:
- JKA Entries: **9**
- P1.NMD: **20** (NOT 9!)
- Calculation: 1+1+1+1+**5**+1+**5**+**4**+1 = **20** ✅

---

## Code Analysis

### ✅ Calculation Logic (Lines 1055-1100): CORRECT
```python
# Calculate total keys in JKY for P1.NMD (always calculate fresh)
# CRITICAL: Firmware expects P1.NMD = Σ(JKeysNum × JEqNmNum) for each JKA entry
# FIRMWARE CONFIRMED: Com_Lib.cpp:525 uses MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum

total_jky_keys = 0
for jka_entry in jka_list:
    if len(jka_entry) >= 3:
        num_units = len(jka_entry[1])   # JKeysNum: Number of units (index [1])
        num_keys = len(jka_entry[2])    # JEqNmNum: Number of keys (index [2])
        total_jky_keys += num_units * num_keys  # Firmware multiply formula

p1["NMD"] = total_jky_keys  # Use calculated Σ(units×keys)
```

**Status:** ✅ CORRECT - Implements firmware formula accurately

### ❌ Validation Logic (Lines 1486-1492): WAS WRONG - NOW FIXED

#### BEFORE (Incorrect):
```python
# WRONG COMMENT:
# CRITICAL: P1.NMD = Number of JKA entries (equipment groups), NOT total keys!
# From Example1: NMD=9 matches 9 JKA entries, not 20 total keys

num_jka_entries = len(jka)
if num_jka_entries != expected_nmd:
    warnings.append(f"P1.NMD ({expected_nmd}) does not match JKA entry count...")
```

**Problem:** Compared NMD against `len(JKA)` instead of `Σ(units × keys)`

#### AFTER (Fixed):
```python
# CORRECT COMMENT:
# CRITICAL: P1.NMD = Σ(JKeysNum × JEqNmNum) for all JKA entries
# Firmware: Com_Lib.cpp:525 uses MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum
# Example verification:
# - Example2: 79 JKA entries → NMD=97 (Σ units×keys)
# - Example3: 9 JKA entries → NMD=20 (NOT 9!)
# - Example6: 8 JKA entries → NMD=13 (NOT 8!)

# Calculate expected NMD using firmware formula
calculated_nmd = 0
for jka_entry in jka:
    if isinstance(jka_entry, list) and len(jka_entry) >= 3:
        num_units = len(jka_entry[1]) if isinstance(jka_entry[1], list) else 0
        num_keys = len(jka_entry[2]) if isinstance(jka_entry[2], list) else 0
        calculated_nmd += num_units * num_keys

if calculated_nmd != expected_nmd and calculated_nmd > 0:
    warnings.append(f"P1.NMD ({expected_nmd}) does not match calculated Σ(units×keys) ({calculated_nmd})...")
```

**Status:** ✅ FIXED - Now validates using correct firmware formula

---

## Example Breakdown: Example3_25params

### JKA Structure:
```json
"JKA": [
  ["AHU_SKY_AIE1", ["Set"],  ["Th1_ChWVal"]],                              // 1×1 = 1
  ["AHU_SKY_AIE2", ["AI"],   ["RAT"]],                                     // 1×1 = 1
  ["AHU_SKY_Mb1",  ["Ar"],   ["VFD"]],                                     // 1×1 = 1
  ["AHU_SKY_DIE1", ["Tr"],   ["VFDTrip"]],                                 // 1×1 = 1
  ["AHU_SKY_Mb2",  ["Mb"],   ["Rhr","P","V","Fr","I"]],                   // 1×5 = 5 ⭐
  ["AHU_SKY_AIE3", ["AI"],   ["ChWValFb"]],                                // 1×1 = 1
  ["AHU_SKY_DIE2", ["St"],   ["VFDAM","VFDRun","ChwValAuto",...,...]],     // 1×5 = 5 ⭐
  ["AHU_SKY_DIE3", ["Sw"],   ["VFDAuto","VFDMan","VFDMode","VFDBypass"]], // 1×4 = 4 ⭐
  ["AHU_SKY_DIE4", ["Set"],  ["Spt"]]                                      // 1×1 = 1
]
```

### Calculation:
```
1 + 1 + 1 + 1 + 5 + 1 + 5 + 4 + 1 = 20
```

### Result:
- **JKA Entries:** 9
- **P1.NMD:** 20 ✅
- **Formula:** Σ(units × keys) = 20 ✅

---

## Files Modified

1. **[modbus_tkinter_app_v6.6_complete.py](modbus_tkinter_app_v6.6_complete.py)** (Lines 1486-1505)
   - Fixed validation logic to use firmware formula
   - Updated comments with correct examples
   - Added calculated_nmd verification

2. **[verify_nmd_logic.py](verify_nmd_logic.py)** (Created)
   - Comprehensive test suite
   - Validates against 5 firmware examples
   - Shows detailed breakdown of calculations

---

## Firmware Compatibility

### ✅ Verified Compatible With:
- Com_Lib.cpp:525
- All Import_Examples (Example2-6)
- Forward transformation engine

### How Firmware Uses NMD:
```cpp
// Firmware iterates through M_data array
MdStrtIdx = 0;
for (i = 0; i < num_jka_entries; i++) {
    // For each JKA entry, firmware allocates space for:
    // units × keys combinations
    MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum;
}
// Total MdStrtIdx must equal P1.NMD!
```

This confirms:
- **P1.NMD** = Total size of M_data array
- **M_data** = Array storing all JSON key-value pairs
- **Size** = Σ(units × keys) for all JKA entries

---

## Common Misconceptions ❌

### WRONG: P1.NMD = Number of JKA Entries
```python
p1["NMD"] = len(jka_list)  # ❌ WRONG!
```

**Why wrong?** Example3 has 9 JKA entries but NMD=20

### WRONG: P1.NMD = Total Number of Parameters
```python
p1["NMD"] = len(registers)  # ❌ WRONG!
```

**Why wrong?** NMD counts JSON output keys, not input parameters

### CORRECT: P1.NMD = Σ(units × keys)
```python
total = 0
for jka in jka_list:
    total += len(jka[1]) * len(jka[2])
p1["NMD"] = total  # ✅ CORRECT!
```

---

## Testing

### Run Verification:
```bash
cd V6.5_Version
python verify_nmd_logic.py
```

### Expected Output:
```
🎉 ALL TESTS PASSED (5/5)
✅ NMD calculation logic is CORRECT
✅ Firmware formula: P1.NMD = Σ(units × keys) for all JKA entries
```

---

## Conclusion

✅ **NMD calculation logic is CORRECT and firmware-verified**  
✅ **Validation logic has been FIXED**  
✅ **All 5 firmware examples pass verification**  
✅ **Formula matches Com_Lib.cpp:525 implementation**  

The application correctly implements the firmware's P1.NMD calculation requirements.

---

## Related Documentation

- [EXAMPLE1_COMPLETE_ANALYSIS.md](../EXAMPLE1_COMPLETE_ANALYSIS.md) - Historical analysis (outdated conclusion)
- [COMPREHENSIVE_LOGIC_VERIFICATION_PLAN.md](../COMPREHENSIVE_LOGIC_VERIFICATION_PLAN.md) - Full system verification
- [Paramap_Logic_Specification_CORRECTED.md](../Paramap_Logic_Specification_CORRECTED.md) - Specification document

**Note:** Some older documentation may contain incorrect statements about NMD = len(JKA). This verification report supersedes those conclusions.

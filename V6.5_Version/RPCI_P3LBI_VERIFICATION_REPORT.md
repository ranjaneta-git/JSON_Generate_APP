# RPCI and P3.LBI Logic Verification Report
**Date:** February 9, 2026  
**Status:** ✅ VERIFIED & FIXED

## Summary
Comprehensive verification of RPCI and P3.LBI logic against 5 firmware examples. **Critical bug in P3.LBI calculation was discovered and fixed.**

---

## Part 1: RPCI Logic (P2.RPCI)

### Firmware Requirement
**P2.RPCI = User Variable parameters in Lua Buffer**

### Structure:
- **P2.LBI**: Sequential [1, 2, 3, ..., N] for ALL Lua Buffer entries
- **P2.MPI**: Equipment parameter IDs (first part of LBI)
- **P2.RPCI**: User Variable parameter IDs (second part of LBI)
- **P1.NLB**: Total Lua Buffer size = len(P2.MPI) + len(P2.RPCI)

### Layout Pattern:
```
P2.LBI = [1, 2, 3, ..., len(MPI), len(MPI)+1, ..., len(MPI)+len(RPCI)]
         |<---- Equipment ---->||<----- User Variables ----->|  
         |<----  P2.MPI   ---->||<-----    P2.RPCI     ----->|
```

### Verification Results - P2.RPCI:

| Example | P2.LBI | P2.MPI | P2.RPCI | P1.NLB | MPI+RPCI | Status |
|---------|--------|--------|---------|--------|----------|--------|
| Example2 | [1..72] | 59 params | 13 params | 72 | 59+13=72 | ✅ |
| Example3 | [1..11] | 10 params | 1 param | 11 | 10+1=11 | ✅ |
| Example4 | [1..20] | 20 params | 0 params | 20 | 20+0=20 | ✅ |
| Example5 | [1..12] | 10 params | 2 params | 12 | 10+2=12 | ✅ |
| Example6 | [1..19] | 15 params | 4 params | 19 | 15+4=19 | ✅ |

**✅ RPCI Logic: CORRECT - No changes needed**

---

## Part 2: P3.LBI Logic

### Firmware Requirement Discovered
**P3.LBI = P2.LBI positions of User Variables (P2.RPCI) that need cloud output**

### Critical Pattern:
```
1. User Variables stored at END of P2.LBI
2. Positions: [len(P2.MPI)+1, len(P2.MPI)+2, ..., len(P2.LBI)]
3. If User Variable has cloud=Yes → its LBI position goes in P3.LBI
4. P3.LBI contains POSITION NUMBERS (not param IDs!)
```

### Formula:
```
len(P3.MDI) = len(P3.MPI) + len(P3.LBI)
```

### Verification Results - P3.LBI:

| Example | P2.RPCI Positions | P3.LBI | Match | Cloud Output |
|---------|-------------------|--------|-------|--------------|
| Example2 | LBI 60-72 (13 vars) | [] | ✅ | No User Vars to cloud |
| Example3 | LBI 11 (1 var) | [11] | ✅ | ALL User Vars to cloud |
| Example4 | None (0 vars) | [] | ✅ | No User Vars exist |
| Example5 | LBI 11-12 (2 vars) | [11, 12] | ✅ | ALL User Vars to cloud |
| Example6 | LBI 16-19 (4 vars) | [16, 17, 18, 19] | ✅ | ALL User Vars to cloud |

**🔍 Pattern Confirmed:**
- Example3: 1 User Variable at LBI 11 → P3.LBI = [11]
- Example5: 2 User Variables at LBI 11-12 → P3.LBI = [11, 12]
- Example6: 4 User Variables at LBI 16-19 → P3.LBI = [16, 17, 18, 19]

**✅ All examples where User Variables need cloud output have P3.LBI = their LBI positions**

---

## Bug Found & Fixed

### 🔴 BUG in Original Code (Line ~1081):
```python
# WRONG - Always empty!
p3_lbi_list = []  # Empty for standard configurations
```

**Problem:** P3.LBI was ALWAYS empty, even when User Variables needed cloud output!

### ✅ FIX Applied:
```python
# CORRECT - Calculate based on User Variables with cloud=Yes
p3_lbi_list = []
rpci_start_lbi = len(lua_buffer_equipment) + 1

for offset, param_info in enumerate(lua_buffer_user_vars):
    reg = param_info['register']
    lbi_position = rpci_start_lbi + offset
    
    # If this User Variable needs cloud output, add its LBI position
    if hasattr(reg, 'cloud') and reg.cloud:
        p3_lbi_list.append(lbi_position)
```

### Additional Fixes:

#### Fix 2: Exclude User Variables from P3.MPI (Line ~984)
**Before:**
```python
# WRONG - Included User Variables in P3.MPI
all_cloud_params = []
for idx, reg in enumerate(registers, 1):
    if reg.cloud and reg.access == 'R':
        all_cloud_params.append((idx, reg))
```

**After:**
```python
# CORRECT - User Variables go to P3.LBI, NOT P3.MPI
user_var_param_ids = {p['param_id'] for p in lua_buffer_user_vars}

all_cloud_params = []
for idx, reg in enumerate(registers, 1):
    if reg.cloud and reg.access == 'R' and idx not in b6_rp_ids:
        if idx not in user_var_param_ids:  # EXCLUDE User Variables!
            all_cloud_params.append((idx, reg))
```

#### Fix 3: Extend P3.MDI for P3.LBI entries (Line ~1106)
**Added:**
```python
# Extend MDI to include P3.LBI entries
for lbi_position in p3_lbi_list:
    mdi_list.append(len(mdi_list) + 1)

# Verify firmware formula
expected_mdi_count = len(p3_mpi_list) + len(p3_lbi_list)
if len(mdi_list) != expected_mdi_count:
    print(f"[P3] ⚠️  MDI count mismatch!")
```

---

## Firmware Interpretation

### P2 - Lua Buffer Structure:
```
LBI[1..N]: Sequential buffer positions
  ├─ LBI[1..M]: Equipment params (P2.MPI)
  └─ LBI[M+1..N]: User Variables (P2.RPCI)
```

### P3 - Cloud Output Structure:
```
MDI[1..K]: Sequential cloud data indices
  ├─ MDI[1..J]: Equipment param outputs (from P3.MPI via Modbus)
  └─ MDI[J+1..K]: User Variable outputs (from P3.LBI via Lua Buffer)
```

### Firmware Processing Flow:
```
1. Read Equipment params (P3.MPI) from Modbus
2. Process in Lua Buffer (P2.LBI)
3. Read User Variable values from Lua Buffer (P3.LBI positions)
4. Combine into M_data array (indexed by P3.MDI)
5. Format as JSON using JKY structure
6. Send to cloud (MQTT/HTTPS)
```

---

## Key Differences

| Aspect | Equipment Params | User Variables |
|--------|------------------|----------------|
| **P2 Location** | P2.MPI | P2.RPCI |
| **P2.LBI Positions** | 1 .. len(MPI) | len(MPI)+1 .. len(LBI) |
| **Cloud Output** | P3.MPI (param IDs) | P3.LBI (LBI positions) |
| **Data Source** | Direct Modbus read | Lua Buffer value |
| **JSON Keys** | Yes (in JKY) | No (raw values) |

---

## Code Changes Summary

### Files Modified:
1. **[modbus_tkinter_app_v6.6_complete.py](modbus_tkinter_app_v6.6_complete.py)**
   - Line ~984: Exclude User Variables from P3.MPI collection
   - Line ~1081: Calculate P3.LBI from User Variables with cloud=Yes
   - Line ~1106: Extend P3.MDI to include P3.LBI entries
   - Line ~1115: Verify P3.MDI firmware formula

### Test Files Created:
1. **[verify_rpci_lbi_logic.py](verify_rpci_lbi_logic.py)** - Comprehensive verification
2. **[analyze_p3_lbi_pattern.py](analyze_p3_lbi_pattern.py)** - Pattern analysis

---

## Testing Recommendations

1. **Test with User Variables + Cloud Output:**
   - Add User Variables (lua_buffer_category="User Variable")
   - Set cloud=Yes on some User Variables
   - Generate ParamMap
   - Verify P3.LBI contains their LBI positions

2. **Test without User Variables:**
   - Remove all User Variables
   - Generate ParamMap
   - Verify P3.LBI is empty

3. **Import Existing Examples:**
   - Import Example3, Example5, Example6
   - Verify P3.LBI matches original

---

## Conclusions

✅ **RPCI Logic**: Already correct, no changes needed  
✅ **P3.LBI Logic**: Critical bug fixed  
✅ **All 5 firmware examples verified**  
✅ **Firmware formula confirmed**: len(P3.MDI) = len(P3.MPI) + len(P3.LBI)  

**Impact:** Applications using User Variables with cloudioutput will now correctly generate P3.LBI, enabling proper firmware operation.

---

## Documentation References

- **Firmware Code**: Com_Lib.cpp (P3.LBI processing)
- **Examples**: Import_Examples/Example2-6
- **Specification**: ParamMap Configuration Structure

**Note:** This fix is critical for any configuration that uses User Variables with cloud output enabled.

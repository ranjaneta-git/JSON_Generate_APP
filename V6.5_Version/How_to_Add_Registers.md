# How to Add Registers (Step‑by‑Step Guide)

**Version:** 6.7+ (with Manual Override)  
**Date:** February 9, 2026  
**Purpose:** Practical guide for adding registers so `P2`/`P3` arrays are correctly generated.

---

## 🚀 Quick Start Steps

1. **Open Add Register Dialog** (Click ➕ Add Register button)
2. **Fill Modbus Fields** (8 essential fields):
   - `Slave ID`: Modbus device address (1-247)
   - `Function Code`: 1/2/3/4 (read) or 5/6/15/16 (write)
   - `Address`: Register address (0-65535)
   - `Length`: Number of registers (auto-calculated from Format)
   - `Format (FMT)`: Data type (INT16, UINT32, FLOAT, etc.)
   - `Multiplier`: Scale factor (1.0, 0.1, 10, etc.)
   - `Access`: R (Read Only), W (Write Only), or RW (Read/Write)
   - `Cloud Output`: Yes (send to cloud) or No (local only)

3. **Configure Lua Buffer** (Advanced section):
   - `In Lua Buffer`: Yes (use Lua) or No (direct Modbus)
   - `Lua Category`: Equipment (P2.MPI) or User Variable (P2.RPCI)
   - `LBI Position`: Auto (recommended) or manual number
   - `LBI Data Type`: Number, Boolean, or String

4. **Optional: Enable Manual Override** (v6.7+):
   - Check ☑️ "Enable Manual Override" if you want manual control
   - Manually type Array Membership (e.g., "P2.MPI,P3.MPI")

5. **Click 💾 Add Register**

---

## 📊 Field → Array Mapping Logic

### Automatic Mode (Default - Recommended)

| Field Configuration | Result |
|---------------------|--------|
| `in_lua_buffer=Yes` + `lua_category=Equipment` | → Added to **P2.MPI** (Equipment params) |
| `in_lua_buffer=Yes` + `lua_category=User Variable` | → Added to **P2.RPCI** (User variables) |
| `cloud=Yes` + `access=R` + NOT User Variable | → Added to **P3.MPI** (Cloud output) |
| `cloud=Yes` + User Variable | → LBI position added to **P3.LBI** (NOT P3.MPI!) |

### Manual Override Mode (v6.7+ - Advanced)

When **Manual Override is enabled**:
- ✅ Your manually-typed **Array Membership** is preserved
- ✅ Parameter is **SKIPPED** during P2/P3 auto-generation
- ✅ Lua Buffer fields are saved but **NOT used** for calculation
- ⚠️ **YOU** are responsible for correct array names

---

## 🎯 Practical Examples

### Example 1: Simple Sensor to Cloud (No Lua)
**Use Case:** Direct Modbus read → Cloud output

```
Slave ID: 1
Function Code: 3
Address: 1000
Format: INT16
Access: R (Read Only)
Cloud Output: Yes
In Lua Buffer: No

Result: → P3.MPI (Region C - Cloud only)
```

### Example 2: Equipment Parameter with Lua + Cloud
**Use Case:** Lua processing + Cloud output

```
Slave ID: 1
Function Code: 3
Address: 2000
Format: FLOAT
Access: R
Cloud Output: Yes
In Lua Buffer: Yes
Lua Category: Equipment

Result: → P2.MPI + P3.MPI (Region B - Lua+Cloud)
```

### Example 3: User Variable (Local Calculation)
**Use Case:** Lua-calculated value (not sent to cloud)

```
Slave ID: 1
Function Code: 5
Address: 3000
Format: INT16
Access: W (Write)
Cloud Output: No
In Lua Buffer: Yes
Lua Category: User Variable

Result: → P2.RPCI only (Region A - User Variable local)
```

### Example 4: User Variable to Cloud
**Use Case:** Lua user variable sent to cloud

```
Slave ID: 1
Function Code: 3
Address: 4000
Format: INT16
Access: R
Cloud Output: Yes
In Lua Buffer: Yes
Lua Category: User Variable

Result: → P2.RPCI + P3.LBI (LBI position, NOT param_id!)
```

### Example 5: Manual Override (Custom Array)
**Use Case:** Legacy config or custom firmware arrays

```
Slave ID: 1
Function Code: 3
Address: 5000
Format: INT16
Access: R
Manual Override: ✓ CHECKED
Array Membership: P2.CUSTOM,P3.SPECIAL

Result: Parameter SKIPPED in auto-generation, manual text preserved
Console: [Manual Override] Param 5 - skipping auto-generation
```

---

## ✅ Verification After Adding Registers

### Method 1: Check Generated Files

1. Click **🔄 Generate All Configurations**
2. Open `Generated_ParamMap_Config.json`
3. Verify:
   - **P2.LBI length** = len(P2.MPI) + len(P2.RPCI)
   - **P2.MPI** contains Equipment param_ids
   - **P2.RPCI** contains User Variable param_ids
   - **P3.MPI** does NOT contain User Variable param_ids
   - **P3.LBI** contains LBI positions (not param_ids) of User Variables with cloud=Yes
   - **P3.MDI length** = len(P3.MPI) + len(P3.LBI)

### Method 2: Run Analysis Scripts

```bash
cd V6.5_Version
python verify_lbi_mdi.py
python analyze_p2_p3_mpi_logic.py
```

### Method 3: Check Console Logging

During generation, watch for:
```
[P2] Calculated: 15 MPI entries (LBI 1-15), 4 RPCI entries (LBI 16-19)
[P3] Cloud Equipment Parameters (for P3.MPI): 10
[P3.LBI] Calculated: 2 User Variable cloud outputs at LBI positions: [18, 19]
[P3.MDI] Extended: 12 total MDI entries (10 from P3.MPI + 2 from P3.LBI)
[Manual Override] Param 7 - skipping auto-generation (user-controlled)
```

---

## ⚠️ Common Mistakes & Warnings

### ❌ Mistake 1: User Variable in P3.MPI
**Symptom:** User Variable param_id appears in P3.MPI  
**Fix:** User Variables go to P3.LBI (LBI position), not P3.MPI (param_id)

### ❌ Mistake 2: Cloud Output with Write Access
**Symptom:** Warning "Cloud output params should be Read Only"  
**Fix:** Set `access=R` for cloud parameters (firmware only reads for cloud)

### ❌ Mistake 3: Manual Override Typos
**Symptom:** Manual array name doesn't match firmware expectations  
**Fix:** Double-check spelling: "P2.MPI", "P2.RPCI", "P3.MPI", "P3.LBI" (case-sensitive!)

### ❌ Mistake 4: Changing Lua Fields Without Regenerating
**Symptom:** Old array values in ParamMap after editing register  
**Fix:** Click "Generate" again after editing Lua Buffer settings

---

## 🛡️ Auto vs Manual Override Decision Tree

```
Should I use Manual Override?
├─ YES, if:
│  ├─ Migrating legacy configuration with special arrays
│  ├─ Using custom firmware with non-standard arrays
│  ├─ Need to temporarily exclude parameter from auto-generation
│  └─ Testing/debugging array membership
│
└─ NO (use Auto), if:
   ├─ Standard firmware configuration
   ├─ First-time setup
   ├─ Want guaranteed correct P2/P3 arrays
   └─ Don't have specific custom requirements
```

**Recommendation:** **Use Automatic Mode (default)** unless you have a specific reason to override.

---

## 🔧 Advanced: Smart Auto-Configuration

The tool automatically sets related fields when you change certain values:

### Rule 1: Cloud Output = "Yes"
**Trigger:** You set `Cloud Output = Yes`  
**Auto-sets:**
- `In Lua Buffer = Yes`
- `Lua Category = Equipment`

**Reason:** Cloud parameters typically need Lua Buffer for processing

### Rule 2: Access = "Write"
**Trigger:** You set `Access = W` or `RW`  
**Auto-sets:**
- `In Lua Buffer = Yes`
- `Lua Category = User Variable` (unless already Equipment)

**Reason:** Write parameters need Lua Buffer for command execution

**Note:** You can manually override these auto-configurations in the dialog before saving.

---

## 📚 Where These Fields Live

### Register_Config.json (Input/Output)
```json
{
  "param_id": 1,
  "slave_id": 1,
  "fc": 3,
  "address": 1000,
  "in_lua_buffer": "Yes",
  "lua_category": "Equipment",
  "lbi_position": "Auto",
  "cloud": "Yes",
  "access": "R",
  "manual_override": false
}
```

### Generated_ParamMap_Config.json (Output Only)
```json
{
  "P2": {
    "LBI": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    "MPI": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "RPCI": [16, 17, 18, 19]
  },
  "P3": {
    "MPI": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "LBI": [18, 19],
    "MDI": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
  }
}
```

---

## 🎓 Tips for Success

✅ **Prefer Auto Assignment** - Avoids mismatches with firmware rules  
✅ **Test After Changes** - Re-generate and verify arrays after editing  
✅ **Use Console Logs** - Watch generation output for validation messages  
✅ **Keep Backups** - Export configurations before major changes  
✅ **Read Verification Reports** - Check generated analysis files  
✅ **Start Simple** - Add a few registers, generate, verify, then add more

---

## 📖 Related Documentation

- **Manual Override Details:** [`MANUAL_OVERRIDE_TESTING_GUIDE.md`](MANUAL_OVERRIDE_TESTING_GUIDE.md)
- **P2/P3 Logic:** [`P2_P3_MPI_LOGIC_DOCUMENTATION.md`](P2_P3_MPI_LOGIC_DOCUMENTATION.md)
- **User Guide:** [`USER_GUIDE.md`](USER_GUIDE.md)
- **Quick Start:** [`QUICK_START_ENHANCED.md`](QUICK_START_ENHANCED.md)

---

*File: How_to_Add_Registers.md | Version: 6.7+ | Last Updated: February 9, 2026*
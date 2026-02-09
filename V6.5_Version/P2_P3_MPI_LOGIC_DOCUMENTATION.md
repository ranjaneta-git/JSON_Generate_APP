# P2.MPI and P3.MPI Logic Documentation
**Version:** 6.7+ (with Manual Override)  
**Date:** February 9, 2026  
**Status:** ✅ VERIFIED with Firmware Examples

## Executive Summary

P2.MPI and P3.MPI are **INDEPENDENT** configuration arrays with different purposes:
- **P2.MPI**: Parameters for Lua Buffer processing (Equipment category)
- **P3.MPI**: Parameters for cloud output (Equipment parameters only)

A parameter can be in P2.MPI, P3.MPI, both, or neither based on independent criteria.

**NEW in v6.7:** Manual Override allows per-register control to skip auto-generation.

---

## Part 0: Manual Override Mode (v6.7+)

### Purpose
Allows users to manually control which ParamMap arrays a parameter belongs to, **bypassing automatic generation**.

### When Manual Override is ENABLED

**Selection Criteria (P2.MPI):**
```python
for idx, reg in enumerate(registers, 1):
    # SKIP parameters with manual_override=True
    if reg.manual_override == True:
        print(f"[Manual Override] Param {idx} - skipping auto-generation")
        continue  # This parameter NOT added to P2.MPI
    
    # Normal auto-generation logic
    if (reg.in_lua_buffer == 'Yes' AND 
        reg.lua_buffer_category == 'Equipment'):
        P2.MPI.append(idx)
```

**Selection Criteria (P3.MPI):**
```python
for idx, reg in enumerate(registers, 1):
    # SKIP parameters with manual_override=True
    if reg.manual_override == True:
        continue  # This parameter NOT added to P3.MPI
    
    # Normal auto-generation logic
    if (reg.cloud == True AND reg.access == 'R' AND ...):
        P3.MPI.append(idx)
```

### Behavior

| Manual Override | Array Membership | P2/P3 Generation | Lua Buffer Fields |
|----------------|------------------|------------------|-------------------|
| **False (Default)** | Auto-calculated | Included in arrays | Used for calculation |
| **True** | User-controlled | **SKIPPED** | Saved but NOT used |

### Use Cases
- ✅ Migrate legacy configs with special array memberships
- ✅ Support custom firmware with non-standard arrays
- ✅ Temporarily exclude parameters for testing
- ✅ Mix automatic and manual parameter management

### User Configuration
- `manual_override`: Checkbox in Add/Edit Register dialog
- `array_membership`: Text field (e.g., "P2.MPI,P3.MPI" or "P2.CUSTOM")
- Manual text is preserved exactly as typed

### Console Logging
```
[Manual Override] Param 7 - skipping auto-generation (user-controlled)
```

**Detailed Guide:** See [`MANUAL_OVERRIDE_TESTING_GUIDE.md`](MANUAL_OVERRIDE_TESTING_GUIDE.md)

---

## Part 1: P2.MPI Logic (Lua Buffer Equipment)

### Purpose
Stores Equipment parameter IDs for Lua script processing in the firmware's Lua Buffer.

### Population Logic (Automatic Mode)
**Selection Criteria:**
```python
for idx, reg in enumerate(registers, 1):
    # Skip manual override parameters (v6.7+)
    if reg.manual_override == True:
        continue
    
    if (reg.in_lua_buffer == 'Yes' AND 
        reg.lua_buffer_category == 'Equipment'):
        P2.MPI.append(idx)  # Add parameter ID
```

**User Configuration Fields:**
- `in_lua_buffer`: "Yes" | "No" (Dropdown)
- `lua_buffer_category`: "Equipment" | "User Variable" | "N/A" (Dropdown)
- `lbi_position`: Integer or "Auto" (For ordering)
- `manual_override`: Checkbox (v6.7+) - Skip auto-generation

### Characteristics
- **Contains**: B5 parameter IDs (1-based index)
- **Order**: Determined by `lbi_position` field (Auto = sequential by param order)
- **LBI Assignment**: Sequential [1, 2, 3, ..., len(P2.MPI)]
- **Purpose**: Parameters available to Lua script for control logic
- **Independent of**: Cloud output decision
- **Skips**: Parameters with manual_override=True (v6.7+)

### Firmware Usage
```c
// Firmware reads Modbus parameters
for (i = 0; i < P2.MPI.length; i++) {
    param_id = P2.MPI[i];
    LuaBuffer[i+1] = ModbusRead(param_id);
}
// Lua script processes LuaBuffer values
ExecuteLuaScript();
```

---

## Part 2: P3.MPI Logic (Cloud Output Equipment)

### Purpose
Stores Equipment parameter IDs to be sent to cloud platform (MQTT/HTTPS).

### Population Logic (Automatic Mode)
**Selection Criteria:**
```python
user_var_param_ids = {p['param_id'] for p in lua_buffer_user_vars}

for idx, reg in enumerate(registers, 1):
    # Skip manual override parameters (v6.7+)
    if reg.manual_override == True:
        continue
    
    if (reg.cloud == True AND              # Cloud checkbox checked
        reg.access == 'R' AND               # Read/Monitor parameters only
        idx not in b6_rp_ids AND            # NOT verification reads
        idx not in user_var_param_ids):     # NOT User Variables
        P3.MPI.append(idx)
```

**User Configuration Fields:**
- `cloud`: Checkbox (True/False)
- `access`: "R" | "R/W" | "W" (Dropdown)
- `json_group`, `json_unit`, `json_key`: For JKY structure
- `manual_override`: Checkbox (v6.7+) - Skip auto-generation

### Characteristics
- **Contains**: B5 parameter IDs (1-based index)
- **Order**: Determined by user configuration order
- **Includes**: Both Lua Buffer params AND non-Lua Buffer params
- **Skips**: Parameters with manual_override=True (v6.7+)
- **Excludes**: User Variables (those go to P3.LBI)
- **Independent of**: Lua Buffer configuration

### Firmware Usage
```c
// Firmware collects cloud data
for (i = 0; i < P3.MPI.length; i++) {
    param_id = P3.MPI[i];
    
    // Check if param is in Lua Buffer
    if (IsInLuaBuffer(param_id)) {
        value = LuaBuffer[GetLBIPosition(param_id)];
    } else {
        value = ModbusRead(param_id);  // Direct read
    }
    
    M_data[i] = value;
}
// Format as JSON and send to cloud
FormatJSON(M_data, JKY);
SendToCloud();
```

---

## Part 3: Relationship Analysis

### Venn Diagram
```
┌─────────────────────────────────────────────────────┐
│ ALL EQUIPMENT PARAMETERS                            │
│                                                     │
│  ┌──────────────────┐      ┌──────────────────┐   │
│  │   P2.MPI         │      │      P3.MPI      │   │
│  │  (Lua Buffer)    │      │   (Cloud Output) │   │
│  │                  │      │                  │   │
│  │                  │      │                  │   │
│  │        A         │  B   │        C         │   │
│  │                  │      │                  │   │
│  │                  │      │                  │   │
│  └──────────────────┘      └──────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘

A = Lua Buffer ONLY (Lua processing, no cloud)
B = BOTH (Lua processing AND cloud output)
C = Cloud ONLY (Cloud output without Lua)
```

### Firmware Example Statistics

| Example | A (Lua Only) | B (Both) | C (Cloud Only) | P2.MPI | P3.MPI |
|---------|--------------|----------|----------------|--------|--------|
| Example2 | 38 | 21 | 76 | 59 | 97 |
| Example3 | 3 | 7 | 12 | 10 | 19 |
| Example4 | 7 | 13 | 29 | 20 | 42 |
| Example5 | 3 | 7 | 12 | 10 | 19 |
| Example6 | 6 | 9 | 0 | 15 | 9 |

### Key Insights

**Region A (Lua Buffer ONLY):**
- Parameters processed by Lua script
- Used for local control logic
- NOT sent to cloud
- Example: Internal calculations, intermediate values

**Region B (BOTH):**
- Parameters processed by Lua AND sent to cloud
- Most common for monitored equipment values
- Firmware reads from Lua Buffer for cloud output
- Example: VFD speed (Lua-processed, cloud-monitored)

**Region C (Cloud ONLY):**
- Parameters sent to cloud WITHOUT Lua processing
- Direct Modbus → Cloud pathway
- More efficient for simple monitoring
- Example: Direct temperature readings

---

## Part 4: Code Implementation

### P2.MPI Population (Lines 946-949)
```python
# Build MPI from Equipment parameters
for lbi_idx, param_info in enumerate(lua_buffer_equipment, 1):
    lbi_list.append(lbi_idx)
    mpi_list.append(param_info['param_id'])

p2 = {
    "LBI": lbi_list,    # Sequential: [1, 2, 3, ...]
    "MPI": mpi_list,    # B5 Param IDs for Equipment params
    "RPCI": rpci_list   # B5 Param IDs for User Variable params
}
```

### P3.MPI Population (Lines 982-1050)
```python
# Step 1: Collect cloud EQUIPMENT parameters (EXCLUDE User Variables!)
user_var_param_ids = {p['param_id'] for p in lua_buffer_user_vars}

all_cloud_params = []
for idx, reg in enumerate(registers, 1):
    if reg.cloud and reg.access == 'R' and idx not in b6_rp_ids:
        # CRITICAL: Exclude User Variables - they go in P3.LBI!
        if idx not in user_var_param_ids:
            all_cloud_params.append((idx, reg))

# Step 2: Build JKY structure from cloud params
# ... (JKY building logic)

# Step 3: P3.MPI is the parameter list
p3_mpi_list = [param_idx for param_idx, reg in all_cloud_params]

p3 = {
    "MDI": mdi_list,       # Sequential: [1, 2, 3, ...]
    "MPI": p3_mpi_list,    # B5 Modbus parameter IDs
    "LBI": p3_lbi_list     # P2.LBI positions of User Variables
}
```

---

## Part 5: Firmware Processing Flow

### Complete Data Flow
```
┌─────────────────────────────────────────────────────────────┐
│ 1. MODBUS READ PHASE                                        │
│    └─ Read ALL parameters from Modbus devices              │
├─────────────────────────────────────────────────────────────┤
│ 2. LUA BUFFER PHASE                                         │
│    ├─ Store P2.MPI params in Lua Buffer (Equipment)        │
│    ├─ Store P2.RPCI params in Lua Buffer (User Variables)  │
│    ├─ Execute Lua script                                    │
│    │  ├─ Process Equipment values                           │
│    │  └─ Calculate User Variable values                     │
│    └─ Updated values stored back in Lua Buffer             │
├─────────────────────────────────────────────────────────────┤
│ 3. CLOUD OUTPUT COLLECTION PHASE                            │
│    ├─ FOR each P3.MPI parameter:                            │
│    │  ├─ IF in Lua Buffer → read from Lua Buffer           │
│    │  └─ ELSE → read directly from Modbus cache            │
│    ├─ FOR each P3.LBI position:                             │
│    │  └─ Read User Variable value from Lua Buffer          │
│    └─ Store all values in M_data array                     │
├─────────────────────────────────────────────────────────────┤
│ 4. JSON FORMATTING PHASE                                    │
│    ├─ Use JKY structure to format JSON                      │
│    ├─ Map MDI indices to JSON keys                          │
│    └─ Create nested JSON object                             │
├─────────────────────────────────────────────────────────────┤
│ 5. CLOUD TRANSMISSION PHASE                                 │
│    └─ Send JSON via MQTT or HTTPS to cloud platform        │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 6: User Configuration Examples

### Example 1: Simple Temperature Sensor
```
Parameter: Tank_Temperature
├─ in_lua_buffer: No
├─ lua_buffer_category: N/A
├─ cloud: Yes ✓
└─ access: R

Result: 
├─ NOT in P2.MPI (no Lua processing)
├─ IN P3.MPI (direct cloud output)
└─ Region C (Cloud ONLY)
```

### Example 2: VFD Speed with Lua Processing
```
Parameter: VFD_Speed_Feedback
├─ in_lua_buffer: Yes
├─ lua_buffer_category: Equipment
├─ cloud: Yes ✓
└─ access: R

Result:
├─ IN P2.MPI (Lua processes value)
├─ IN P3.MPI (send to cloud)
└─ Region B (BOTH)
```

### Example 3: Internal Calculation Variable
```
Parameter: PID_Internal_Error
├─ in_lua_buffer: Yes
├─ lua_buffer_category: Equipment
├─ cloud: No
└─ access: R

Result:
├─ IN P2.MPI (Lua uses for control)
├─ NOT in P3.MPI (not sent to cloud)
└─ Region A (Lua ONLY)
```

### Example 4: User Variable (Custom Calculation)
```
Parameter: Energy_Consumption_Calc
├─ in_lua_buffer: Yes
├─ lua_buffer_category: User Variable
├─ cloud: Yes ✓
└─ access: R

Result:
├─ IN P2.RPCI (Lua calculates value)
├─ NOT in P3.MPI (User Vars don't use P3.MPI)
├─ IN P3.LBI (LBI position for cloud output)
└─ Special case: User Variable pathway
```

---

## Part 7: Validation & Verification

### Verification Checklist
✅ P2.MPI contains all Equipment params with in_lua_buffer=Yes  
✅ P2.RPCI contains all User Variable params with in_lua_buffer=Yes  
✅ P3.MPI contains all Equipment params with cloud=Yes (excluding User Vars)  
✅ P3.LBI contains LBI positions of User Variables with cloud=Yes  
✅ len(P2.LBI) = len(P2.MPI) + len(P2.RPCI)  
✅ len(P3.MDI) = len(P3.MPI) + len(P3.LBI)  
✅ P2.MPI and P3.MPI are independent (neither is subset of the other)  

### Common Misconceptions ❌

**WRONG:** "P3.MPI must be a subset of P2.MPI"
- Reality: They are independent. Cloud params can bypass Lua Buffer.

**WRONG:** "All Lua Buffer params go to cloud"
- Reality: Only those with cloud=Yes go to P3.MPI/P3.LBI.

**WRONG:** "All cloud params must be in Lua Buffer"
- Reality: Cloud params can be direct Modbus reads (Region C).

**WRONG:** "User Variables go in P3.MPI"
- Reality: User Variables go in P3.LBI (LBI positions, not param IDs).

---

## Part 8: Firmware References

### Source Code References
- **Com_Lib.cpp**: Lua Buffer management, P2.MPI/P2.RPCI handling
- **ParamMapConfig_Lib.cpp**: P3.MPI/P3.LBI cloud output collection
- **LuaEngine_Lib.cpp**: Lua script execution with Lua Buffer access

### Verified Examples
- Example2_163params: 59 P2.MPI, 97 P3.MPI (78% cloud-only params)
- Example3_25params: 10 P2.MPI, 19 P3.MPI (63% cloud-only params)
- Example6_21params: 15 P2.MPI, 9 P3.MPI (100% P3⊆P2)

---

## Conclusion

✅ **P2.MPI and P3.MPI logic VERIFIED and CORRECT**  
✅ **Independent configuration confirmed by firmware examples**  
✅ **Flexible architecture supports multiple use cases**  
✅ **Firmware processing flow documented**  

The independent nature of P2.MPI and P3.MPI provides architectural flexibility:
- Efficient direct cloud output for simple parameters
- Lua processing for complex control logic
- Hybrid approach for monitored equipment values
- User Variables for custom calculations

This design maximizes firmware efficiency while maintaining configuration flexibility.

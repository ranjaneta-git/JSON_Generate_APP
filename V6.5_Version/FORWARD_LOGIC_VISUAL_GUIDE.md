# 🎨 Forward Generation Logic - Visual Guide

**Version:** 6.6  
**Date:** February 2026  
**Target Audience:** Visual learners, application engineers, system integrators

---

## 🎯 Purpose

This guide uses **visual diagrams**, **flowcharts**, and **examples** to explain how the tool transforms Register_Config.json into Modbus_Config.json and ParamMap_Config.json.

---

## 📊 Big Picture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FORWARD TRANSFORMATION                           │
└─────────────────────────────────────────────────────────────────────┘

INPUT:                          PROCESSING:                    OUTPUT:
┌──────────────┐                                             ┌──────────────┐
│  Register    │                                             │   Modbus     │
│  Config      │──┐                                       ┌──│   Config     │
│  .json       │  │                                       │  │   .json      │
│              │  │   ┌──────────────────────────┐       │  │              │
│ • slave_id   │  │   │  FORWARD ENGINE          │       │  │ • B4 (SA)    │
│ • address    │  └──▶│                          │───────┤  │ • B5 (Params)│
│ • format     │      │  • Extract unique slaves │       │  │ • B6 (Reads) │
│ • access     │      │  • Build B5 arrays       │       │  │ • Packets    │
│ • cloud      │      │  • Detect verification   │       │  └──────────────┘
│ • 32 more    │      │  • Split P2 arrays       │       │
│   fields     │      │  • Identify cloud params │       │  ┌──────────────┐
└──────────────┘      │  • Group equipment       │       └──│  ParamMap    │
                      └──────────────────────────┘          │  Config      │
                                                             │  .json       │
                                                             │              │
                                                             │ • P2 (Lua)   │
                                                             │ • P3 (Cloud) │
                                                             │ • JKY/JKA    │
                                                             └──────────────┘
```

---

## 🔄 Step-by-Step Transformation

### Step 1: Load Register Configuration

```
INPUT FILE: Register_Config.json
┌────────────────────────────────────────────────────────────┐
│ {                                                          │
│   "registers": [                                           │
│     {                                                      │
│       "slave_id": 1,           ◄── Modbus device ID       │
│       "address": 1000,         ◄── Register address       │
│       "function_code": 3,      ◄── Holding register       │
│       "length": 1,             ◄── Number of registers    │
│       "format": 8,             ◄── INT16 data type        │
│       "multiplier": 0.1,       ◄── Scale: value × 0.1     │
│       "access_type": "Read Only",  ◄── Cannot write       │
│       "cloud_output": "Yes",   ◄── Send to MQTT/cloud     │
│       "json_group": "Equipment",                          │
│       "json_unit": "Chiller-1",                          │
│       "json_key": "Temperature",                         │
│       ...                                                 │
│     }                                                      │
│   ]                                                        │
│ }                                                          │
└────────────────────────────────────────────────────────────┘
```

---

### Step 2: Extract & Process - Block 4 (B4)

**Purpose:** Collect all unique slave IDs for polling

```
REGISTERS:                    EXTRACTION:                RESULT:
┌──────────────┐             ┌──────────────┐          ┌────────────┐
│ Reg 1        │             │ slave_id: 1  │          │ B4: {      │
│ slave_id: 1  │────────────▶│ slave_id: 2  │─────────▶│   "SA": [  │
│              │             │ slave_id: 3  │          │     1,     │
│ Reg 2        │             │ slave_id: 1  │          │     2,     │
│ slave_id: 2  │             │  (duplicate) │          │     3      │
│              │             │              │          │   ]        │
│ Reg 3        │             │ UNIQUE:      │          │ }          │
│ slave_id: 3  │             │ [1, 2, 3]    │          └────────────┘
│              │             └──────────────┘
│ Reg 4        │
│ slave_id: 1  │       (Duplicate slave IDs removed)
└──────────────┘       (Sorted ascending)
```

**Logic:**
```
B4.SA = sorted(set([register.slave_id for all registers]))
```

---

### Step 3: Build Block 5 (B5) - Parameter Arrays

**Purpose:** Create parallel arrays for all register properties

```
INPUT REGISTERS:
════════════════════════════════════════════════════════════════
Reg#  Slave  FC  Address  Length  Format  Multiplier  Access
════════════════════════════════════════════════════════════════
 1      1    3    1000      1       8        0.1      Read Only
 2      1    3    2000      1       8        1.0      Write
 3      2    4    3000      2      12        1.0      Read Only
════════════════════════════════════════════════════════════════

                        ↓ TRANSFORMATION ↓

OUTPUT B5 BLOCK:
════════════════════════════════════════════════════════════════
{
  "B5": {
    "s_Indx":  [1,     2,     3    ],  ◄── Parameter index (auto)
    "modID":   [1000,  2000,  3000 ],  ◄── Register addresses
    "func_c":  [3,     3,     4    ],  ◄── Function codes
    "Rcount":  [1,     1,     2    ],  ◄── Register lengths
    "c":       [8,     8,     12   ],  ◄── Format codes
    "f":       [0.1,   1.0,   1.0  ],  ◄── Multipliers
    "jGroup":  ["Equipment", "Settings", "Equipment"],
    "jUnit":   ["Chiller-1", "Chiller-1", "VFD-1"],
    "jKey":    ["Temp", "Setpoint", "Speed"],
    "arrmem":  ["Chiller", "None", "VFD"],
    ... (27 more arrays)
  }
}
════════════════════════════════════════════════════════════════

📌 KEY INSIGHT: All arrays have SAME LENGTH (3 in this example)
📌 Array position = Parameter ID (s_Indx value)
```

**Visualization:**

```
         Position:    0           1           2
                      ↓           ↓           ↓
         s_Indx:    [1,          2,          3         ]
         modID:     [1000,       2000,       3000      ]
         func_c:    [3,          3,          4         ]
           ↑          ↑           ↑           ↑
           └──────────┴───────────┴───────────┘
              All describe the SAME parameters
              accessed by index position
```

---

### Step 4: Generate Block 6 (B6) - Verification Reads

**Purpose:** Identify which parameters need verification (read-back after write)

```
DECISION LOGIC:
┌────────────────────────────────────────────────────────┐
│                                                        │
│   FOR EACH REGISTER:                                   │
│   ┌──────────────────────────────────────────┐        │
│   │ START                                     │        │
│   └───────────────┬──────────────────────────┘        │
│                   ↓                                    │
│           ┌───────────────────┐                        │
│           │ access_type ==    │                        │
│           │ "Read Only"?      │                        │
│           └────┬──────────┬───┘                        │
│                │YES       │NO                          │
│                ↓          ↓                             │
│         ┌──────────┐  ┌────────────────┐              │
│         │ Add to   │  │ param_type ==  │              │
│         │ B6.RP    │  │ "feedback"?    │              │
│         └──────────┘  └────┬───────┬───┘              │
│                            │YES    │NO                 │
│                            ↓       ↓                   │
│                     ┌──────────┐  ┌────────────┐      │
│                     │ Add to   │  │ Skip       │      │
│                     │ B6.RP    │  └────────────┘      │
│                     └──────────┘                       │
└────────────────────────────────────────────────────────┘
```

**Example:**

```
REGISTERS:
═══════════════════════════════════════════════════════════
ID  Access         Param Type    Include in B6.RP?
═══════════════════════════════════════════════════════════
1   Read Only      -             ✓ YES (read-only param)
2   Write          write         ✗ NO  (write command)
3   Read Only      feedback      ✓ YES (feedback read)
4   Write          -             ✗ NO  (write param)
═══════════════════════════════════════════════════════════

RESULT:
{
  "B6": {
    "RP": [1, 3]    ◄── Parameters 1 and 3 need verification
  }
}
```

---

### Step 5: Split P2 Arrays - Lua Buffer Logic

**Purpose:** Separate parameters into Equipment (MPI) vs User Variables (RPCI)

```
┌─────────────────────────────────────────────────────────────────┐
│                    P2 SPLIT DECISION TREE                       │
└─────────────────────────────────────────────────────────────────┘

FOR EACH REGISTER:

                    ┌─────────────────┐
                    │ in_lua_buffer   │
                    │    == "Yes"?    │
                    └────┬────────────┘
                         │
            ┌────────────┴────────────┐
            │YES                      │NO
            ↓                         ↓
    ┌───────────────┐        ┌──────────────┐
    │ lua_category? │        │ NOT IN LUA   │
    └───┬───────┬───┘        │ BUFFER       │
        │       │            └──────────────┘
        │       │
   ┌────┴───┐  └────┐
   │        │       │
   ↓        ↓       ↓
┌─────┐ ┌──────┐ ┌────────┐
│Equip│ │ User │ │ Other  │
│ment │ │ Var  │ │        │
└──┬──┘ └──┬───┘ └────────┘
   │       │
   ↓       ↓
┌──────┐ ┌───────┐
│P2.MPI│ │P2.RPCI│
└──────┘ └───────┘
```

**Visual Example:**

```
INPUT REGISTERS:
═════════════════════════════════════════════════════════════════════
ID  In Lua Buffer?  Lua Category      Result
═════════════════════════════════════════════════════════════════════
1   Yes             Equipment         ──▶ P2.MPI
2   Yes             User Variable     ──▶ P2.RPCI
3   Yes             Equipment         ──▶ P2.MPI
4   No              -                 ──▶ (not in Lua)
5   Yes             User Variable     ──▶ P2.RPCI
═════════════════════════════════════════════════════════════════════

OUTPUT:
{
  "P2": {
    "MPI":  [1, 3],     ◄── Equipment parameters (control logic)
    "RPCI": [2, 5]      ◄── User Variables (remote settable)
  }
}

┌─────────────────────────────────────────────────────────┐
│ 📌 FIRMWARE USAGE:                                      │
│                                                         │
│ P2.MPI  → Lua Buffer for control logic & cloud output  │
│ P2.RPCI → Lua Buffer for user-settable values          │
└─────────────────────────────────────────────────────────┘
```

---

### Step 6: Build P3 Array - Cloud Parameters

**Purpose:** List all parameters that should be sent to cloud/MQTT

```
LOGIC: cloud_output == "Yes" → Add to P3.MPI

┌────────────────────────────────────────────────────┐
│                                                    │
│  REGISTER HAS                                      │
│  cloud_output = "Yes"?                             │
│                                                    │
│         YES ↓                      NO ↓            │
│                                                    │
│    Add B5 ID to P3.MPI       Skip this register   │
│                                                    │
└────────────────────────────────────────────────────┘
```

**Visual Example:**

```
REGISTERS:
════════════════════════════════════════════════════════
ID  Name         Cloud Output?    Include in P3.MPI?
════════════════════════════════════════════════════════
1   Temperature  Yes              ✓ YES
2   Pressure     Yes              ✓ YES
3   Setpoint     No               ✗ NO (internal only)
4   Flow         Yes              ✓ YES
5   Status       No               ✗ NO (internal only)
════════════════════════════════════════════════════════

RESULT:
{
  "P3": {
    "MPI": [1, 2, 4]    ◄── These params sent to cloud
  }
}

┌──────────────────────────────────────────────────┐
│ 📊 CLOUD OUTPUT:                                 │
│                                                  │
│ MQTT Topic: device/data                         │
│ {                                                │
│   "Temperature": 25.5,   ← Param 1              │
│   "Pressure": 1.2,       ← Param 2              │
│   "Flow": 150            ← Param 4              │
│ }                                                │
│                                                  │
│ (Setpoint and Status NOT included)              │
└──────────────────────────────────────────────────┘
```

---

## 🎯 Phase 1 Smart Auto-Configuration

### Rule 1: Cloud Output Triggers Lua Buffer

```
USER INPUT:                    AUTO-CONFIGURATION:
┌──────────────────┐          ┌─────────────────────────┐
│ cloud_output:    │          │ AUTOMATIC SETTINGS:     │
│   "Yes"          │──────▶   │                         │
│                  │          │ in_lua_buffer:  "Yes"   │
│                  │          │ lua_category:   "Equip" │
└──────────────────┘          └─────────────────────────┘
                                        │
                                        ↓
                              ┌──────────────────┐
                              │ RESULT:          │
                              │ • Added to P2.MPI│
                              │ • Added to P3.MPI│
                              └──────────────────┘
```

**Why?**
- Cloud parameters need to be in Lua Buffer for firmware to access
- Equipment category is default for monitored/control values

### Rule 2: Write Access Triggers User Variable

```
USER INPUT:                    AUTO-CONFIGURATION:
┌──────────────────┐          ┌─────────────────────────┐
│ access_type:     │          │ AUTOMATIC SETTINGS:     │
│   "Write"        │──────▶   │                         │
│                  │          │ in_lua_buffer:  "Yes"   │
│                  │          │ lua_category:   "User"  │
└──────────────────┘          │                    Var" │
                              └─────────────────────────┘
                                        │
                                        ↓
                              ┌──────────────────────┐
                              │ RESULT:              │
                              │ • Added to P2.RPCI   │
                              │ • NOT in P3.MPI      │
                              │   (internal control) │
                              └──────────────────────┘
```

**Why?**
- Write parameters are user-settable (setpoints, commands)
- User Variable category keeps them separate from monitored values
- Not sent to cloud automatically (internal control only)

---

## 🔗 Equipment Grouping (JKY/JKA)

### Purpose
Group parameters by equipment type for structured JSON output

```
CONCEPT:
┌─────────────────────────────────────────────────────────┐
│ JKY = Equipment Type List (unique types)                │
│ JKA = Parameter Assignments (which param in which equip)│
└─────────────────────────────────────────────────────────┘
```

### Visual Example

```
INPUT REGISTERS:
════════════════════════════════════════════════════════════
ID  Array Membership    JSON Unit      JKA Index
════════════════════════════════════════════════════════════
1   Chiller             Chiller-1      0
2   Chiller             Chiller-2      0
3   VFD                 VFD-1          1
4   Pump                Pump-1         2
5   Chiller             Chiller-1      0
════════════════════════════════════════════════════════════

STEP 1: Extract Unique Equipment Types
─────────────────────────────────────────
Chiller, VFD, Pump → JKY Array

STEP 2: Assign Parameters to Equipment Groups
──────────────────────────────────────────────
Param 1 → Chiller (index 0)
Param 2 → Chiller (index 0)
Param 3 → VFD (index 1)
Param 4 → Pump (index 2)
Param 5 → Chiller (index 0)

OUTPUT:
═══════════════════════════════════════════════════════════
{
  "JKY": [
    "Chiller",    // Index 0
    "VFD",        // Index 1
    "Pump"        // Index 2
  ],
  "JKA": [
    [1, 2, 5],    // Chiller params (index 0)
    [3],          // VFD params (index 1)
    [4]           // Pump params (index 2)
  ]
}
═══════════════════════════════════════════════════════════
```

**Resulting JSON Structure:**

```json
{
  "Equipment": {
    "Chiller": {
      "Chiller-1": {
        "Temp": 25.5,      // Param 1
        "Flow": 150        // Param 5
      },
      "Chiller-2": {
        "Pressure": 1.2    // Param 2
      }
    },
    "VFD": {
      "VFD-1": {
        "Speed": 1450      // Param 3
      }
    },
    "Pump": {
      "Pump-1": {
        "Status": 1        // Param 4
      }
    }
  }
}
```

---

## 📦 Complete Transformation Example

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMPLETE WALKTHROUGH                          │
└──────────────────────────────────────────────────────────────────┘

INPUT: 3 Registers
═════════════════════════════════════════════════════════════════════
Register 1:                 Register 2:                Register 3:
  slave_id: 1                 slave_id: 1               slave_id: 2
  address: 1000               address: 2000             address: 3000
  function_code: 3            function_code: 3          function_code: 4
  length: 1                   length: 1                 length: 2
  format: 8 (INT16)           format: 8 (INT16)         format: 12 (FLOAT)
  multiplier: 0.1             multiplier: 1.0           multiplier: 1.0
  access: Read Only           access: Write             access: Read Only
  cloud: Yes                  cloud: No                 cloud: Yes
  json_group: Equipment       json_group: Settings      json_group: Equipment
  json_unit: Chiller-1        json_unit: Chiller-1      json_unit: VFD-1
  json_key: Temperature       json_key: Setpoint        json_key: Speed
  array_membership: Chiller   array_membership: None    array_membership: VFD
═════════════════════════════════════════════════════════════════════

                            ↓ PROCESSING ↓

BLOCK 4 (Slave Addresses):
───────────────────────────────────────────────────────────────
B4.SA = [1, 2]    (Unique slaves: 1 from Reg1&2, 2 from Reg3)


BLOCK 5 (Parameter Arrays):
───────────────────────────────────────────────────────────────
{
  "s_Indx":  [1,     2,        3      ],
  "modID":   [1000,  2000,     3000   ],
  "func_c":  [3,     3,        4      ],
  "Rcount":  [1,     1,        2      ],
  "c":       [8,     8,        12     ],
  "f":       [0.1,   1.0,      1.0    ],
  "jGroup":  ["Equipment", "Settings", "Equipment"],
  "jUnit":   ["Chiller-1", "Chiller-1", "VFD-1"],
  "jKey":    ["Temperature", "Setpoint", "Speed"],
  "arrmem":  ["Chiller", "None", "VFD"]
}


BLOCK 6 (Verification Reads):
───────────────────────────────────────────────────────────────
B6.RP = [1, 3]
  (Reg 1: Read Only → verify)
  (Reg 2: Write → NO verify)
  (Reg 3: Read Only → verify)


P2 SPLIT (Lua Buffer):
───────────────────────────────────────────────────────────────
PHASE 1 AUTO-CONFIG:
  Reg 1: cloud=Yes    → Lua Buffer=Yes, Category=Equipment
  Reg 2: access=Write → Lua Buffer=Yes, Category=User Var
  Reg 3: cloud=Yes    → Lua Buffer=Yes, Category=Equipment

P2.MPI  = [1, 3]    (Equipment params)
P2.RPCI = [2]       (User Variable)


P3 CLOUD:
───────────────────────────────────────────────────────────────
P3.MPI = [1, 3]
  (Reg 1: cloud=Yes → include)
  (Reg 2: cloud=No  → exclude)
  (Reg 3: cloud=Yes → include)


JKY/JKA (Equipment Grouping):
───────────────────────────────────────────────────────────────
JKY = ["Chiller", "VFD"]    (Unique equipment types)

JKA = [
  [1],     // Chiller: param 1
  [3]      // VFD: param 3
]
(Param 2 has array_membership="None" → not in JKA)
```

---

## 🔄 Data Flow Visualization

```
┌────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE DATA FLOW                             │
└────────────────────────────────────────────────────────────────────────┘

                        Register_Config.json
                                │
                                │ (Load & Parse)
                                ↓
                        ┌───────────────┐
                        │  RegisterEntry│
                        │    Objects    │
                        └───────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ↓               ↓               ↓
        ┌──────────────┐ ┌─────────────┐ ┌────────────┐
        │ Extract      │ │ Build B5    │ │ Detect     │
        │ Unique       │ │ Parallel    │ │ Read-Only  │
        │ Slave IDs    │ │ Arrays      │ │ Params     │
        └──────┬───────┘ └──────┬──────┘ └──────┬─────┘
               │                │               │
               ↓                ↓               ↓
         ┌─────────┐      ┌─────────┐    ┌──────────┐
         │   B4    │      │   B5    │    │    B6    │
         └────┬────┘      └────┬────┘    └─────┬────┘
              │                │               │
              └────────────────┴───────────────┘
                                │
                                ↓
                    ┌───────────────────────┐
                    │  Modbus_Config.json   │
                    │  • B4: Slave list     │
                    │  • B5: Parameters     │
                    │  • B6: Verification   │
                    │  • Packets definition │
                    └───────────────────────┘

                        Register_Config.json
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ↓               ↓               ↓
        ┌──────────────┐ ┌─────────────┐ ┌────────────┐
        │ Filter Lua   │ │ Filter      │ │ Extract    │
        │ Buffer by    │ │ Cloud=Yes   │ │ Equipment  │
        │ Category     │ │ Parameters  │ │ Types      │
        └──────┬───────┘ └──────┬──────┘ └──────┬─────┘
               │                │               │
               ↓                ↓               ↓
         ┌─────────┐      ┌─────────┐    ┌──────────┐
         │   P2    │      │   P3    │    │  JKY/JKA │
         └────┬────┘      └────┬────┘    └─────┬────┘
              │                │               │
              └────────────────┴───────────────┘
                                │
                                ↓
                    ┌───────────────────────┐
                    │  ParamMap_Config.json │
                    │  • P2: Lua split      │
                    │  • P3: Cloud params   │
                    │  • JKY: Equipment list│
                    │  • JKA: Assignments   │
                    └───────────────────────┘
```

---

## 🎓 Quick Reference Table

```
┌─────────────────────────────────────────────────────────────────────┐
│                   BLOCK/ARRAY QUICK REFERENCE                       │
├──────────┬──────────────────────────┬────────────────────────────────┤
│ Block    │ Purpose                  │ Logic                          │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ B4.SA    │ Slave address list       │ Unique slave IDs, sorted       │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ B5       │ Parameter properties     │ Parallel arrays (37 fields)    │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ B6.RP    │ Verification reads       │ Read-only + feedback params    │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ P2.MPI   │ Equipment params (Lua)   │ Lua=Yes & Category=Equipment   │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ P2.RPCI  │ User variables (Lua)     │ Lua=Yes & Category=User Var    │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ P3.MPI   │ Cloud output params      │ cloud_output = "Yes"           │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ JKY      │ Equipment type list      │ Unique array_membership values │
├──────────┼──────────────────────────┼────────────────────────────────┤
│ JKA      │ Equipment param groups   │ Params grouped by equipment    │
└──────────┴──────────────────────────┴────────────────────────────────┘
```

---

## 🧠 Decision Matrix

```
┌─────────────────────────────────────────────────────────────────────┐
│               PARAMETER CLASSIFICATION MATRIX                       │
├─────────────┬──────────────┬────────────────┬──────────────────────┤
│ Conditions  │ B6.RP?       │ P2 Array?      │ P3.MPI?              │
├─────────────┼──────────────┼────────────────┼──────────────────────┤
│ Read Only   │ ✓ YES        │ P2.MPI         │ If cloud=Yes         │
│ Cloud=Yes   │              │ (auto-config)  │                      │
├─────────────┼──────────────┼────────────────┼──────────────────────┤
│ Write       │ ✗ NO         │ P2.RPCI        │ ✗ NO                 │
│ Cloud=No    │              │ (auto-config)  │ (internal)           │
├─────────────┼──────────────┼────────────────┼──────────────────────┤
│ Read Only   │ ✓ YES        │ P2.MPI         │ ✗ NO                 │
│ Cloud=No    │              │ (auto-config)  │ (if lua enabled)     │
├─────────────┼──────────────┼────────────────┼──────────────────────┤
│ Feedback    │ ✓ YES        │ P2.RPCI        │ ✗ NO                 │
│ (paired)    │              │ (user var)     │ (internal feedback)  │
└─────────────┴──────────────┴────────────────┴──────────────────────┘
```

---

## 💡 Common Patterns

### Pattern 1: Temperature Sensor (Read, Cloud)

```
INPUT:                          OUTPUT:
────────────────               ─────────────────────────
access: Read Only     ────▶    B6.RP:   ✓ (verify read)
cloud: Yes                    P2.MPI:  ✓ (equipment)
                              P3.MPI:  ✓ (send cloud)
                              JKA:     ✓ (if equipment)
```

### Pattern 2: Setpoint (Write, Internal)

```
INPUT:                          OUTPUT:
────────────────               ─────────────────────────
access: Write         ────▶    B6.RP:   ✗ (write cmd)
cloud: No                     P2.RPCI: ✓ (user var)
                              P3.MPI:  ✗ (internal)
                              JKA:     ✗ (not in equip)
```

### Pattern 3: Status Read (Read, Not Cloud)

```
INPUT:                          OUTPUT:
────────────────               ─────────────────────────
access: Read Only     ────▶    B6.RP:   ✓ (verify read)
cloud: No                     P2.MPI:  ✓ (if lua=yes)
lua_buffer: Yes               P3.MPI:  ✗ (not cloud)
                              JKA:     Depends on array
```

---

## 🎯 Summary Flowchart

```
                    START: Register_Config.json
                                │
                                ↓
                    ┌───────────────────────┐
                    │ Parse Register List   │
                    └───────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ↓                       ↓
        ┌───────────────────┐   ┌──────────────────┐
        │ MODBUS_CONFIG     │   │ PARAMAP_CONFIG   │
        │ GENERATION        │   │ GENERATION       │
        └────────┬──────────┘   └─────────┬────────┘
                 │                        │
    ┌────────────┼───────────┐    ┌──────┼──────┬────────┐
    │            │           │    │      │      │        │
    ↓            ↓           ↓    ↓      ↓      ↓        ↓
 ┌─────┐    ┌─────┐    ┌─────┐ ┌──┐  ┌──┐  ┌─────┐  ┌─────┐
 │ B4  │    │ B5  │    │ B6  │ │P2│  │P3│  │ JKY │  │ JKA │
 └──┬──┘    └──┬──┘    └──┬──┘ └┬─┘  └┬─┘  └──┬──┘  └──┬──┘
    │          │          │     │     │      │       │
    └──────────┴──────────┴─────┴─────┴──────┴───────┘
                                │
                                ↓
                    ┌───────────────────────┐
                    │ Write JSON Files      │
                    └───────────────────────┘
                                │
                                ↓
                    ┌───────────────────────┐
                    │ Generated_Modbus_     │
                    │ Config.json           │
                    │ Generated_ParamMap_   │
                    │ Config.json           │
                    └───────────────────────┘
                                │
                                ↓
                             SUCCESS!
```

---

## 📖 Additional Resources

- **User Guide:** [USER_GUIDE.md](USER_GUIDE.md) - How to add registers
- **Engineer Guide:** [APPLICATION_ENGINEER_GUIDE.md](APPLICATION_ENGINEER_GUIDE.md) - Detailed specs
- **Developer Guide:** [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Code implementation
- **Code:** `forward_engine.py` - Actual implementation

---

**Last Updated:** February 8, 2026  
**Version:** 6.6  
**Maintainer:** Thermelgy Firmware Team

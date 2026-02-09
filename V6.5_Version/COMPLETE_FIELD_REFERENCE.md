# 📋 Complete Field Reference Guide

**Version:** 6.6  
**Date:** February 2026  
**Target Audience:** Application Engineers, End Users

---

## 🎯 Purpose

This document provides a **complete reference** for all 37 fields used in the Modbus Register Configuration Tool, explaining:
- What each field is for
- When to use it
- How it's used in forward transformation (Register → JSONs)
- How it's used in reverse transformation (JSONs → Register)
- Relationships between fields

---

## 📊 Quick Reference Table

### Field Categories

```
┌─────────────────────────────────────────────────────────────────────┐
│                     37 FIELDS ORGANIZED BY CATEGORY                 │
├──────────────────────┬──────────────────────────────────────────────┤
│ Category             │ Field Count │ Visibility                      │
├──────────────────────┼─────────────┼─────────────────────────────────┤
│ Essential Fields     │      8      │ ⭐ Required in Add dialog       │
│ JSON Mapping         │      4      │ Optional in Advanced section    │
│ Transparent Config   │      6      │ Optional in Advanced section    │
│ Lua Buffer Config    │      4      │ Optional (auto-configured)      │
│ Legacy Packet Fields │      3      │ Visible in table                │
│ Internal Metadata    │     12      │ Hidden (auto-generated)         │
├──────────────────────┼─────────────┼─────────────────────────────────┤
│ TOTAL                │     37      │                                 │
└──────────────────────┴─────────────┴─────────────────────────────────┘
```

---

## 🌟 Part 1: Essential Fields (User Must Fill)

These 8 fields are **required** when adding a register. They appear first in the Add dialog.

---

### 1. Slave ID

**Type:** Integer (1-247)  
**Purpose:** Identifies which Modbus device to communicate with

**Forward Transformation:**
```
Register Config: slave_id = 1
         ↓
Modbus Config: B4.SA = [1, 2, 3] (unique list)
```

**Reverse Transformation:**
```
Modbus Config: B5.slaveID[index] = 1
         ↓
Register Config: slave_id = 1
```

**Example:**
```
Bus:  RS485 ──┬─── Device 1 (Slave ID: 1) ← Chiller
              ├─── Device 2 (Slave ID: 2) ← VFD
              └─── Device 3 (Slave ID: 3) ← Pump
```

**Notes:**
- Must be unique on the Modbus bus
- Valid range: 1-247 (0 = broadcast, 248-255 = reserved)
- Same device can have multiple registers

---

### 2. Function Code

**Type:** Integer (3 or 4)  
**Purpose:** Specifies the Modbus command type

**Values:**
- `3` = Read Holding Registers (read/write registers)
- `4` = Read Input Registers (read-only registers)

**Forward Transformation:**
```
Register Config: function_code = 3
         ↓
Modbus Config: B5.func_c[index] = 3
```

**Reverse Transformation:**
```
Modbus Config: B5.func_c[index] = 3
         ↓
Register Config: function_code = 3
```

**When to Use:**
- FC 3: For parameters that can be read or written (temperatures, setpoints, control flags)
- FC 4: For read-only parameters (sensor readings, status registers)

**Example:**
```
Temperature sensor:     FC 4 (read-only)
Temperature setpoint:   FC 3 (read/write)
Motor speed:            FC 3 (read/write)
Motor status:           FC 4 (read-only)
```

---

### 3. Address (Register Address)

**Type:** Integer (0-65535)  
**Purpose:** The Modbus register address to read/write

**Forward Transformation:**
```
Register Config: address = 1000
         ↓
Modbus Config: B5.modID[index] = 1000
```

**Reverse Transformation:**
```
Modbus Config: B5.modID[index] = 1000
         ↓
Register Config: address = 1000
```

**Important Notes:**
- Address space: 0-65535 (16-bit)
- Modbus addressing can be confusing:
  - Some devices use 0-based (0-65535)
  - Some use 1-based (1-65536)
  - Some use function-code prefixes (40001 = FC3, address 0)
- **Use the address documented in device manual**

**Example:**
```
Device Manual Says:        Use in Tool:
├─ "Register 40001"    →   Address: 0     (40001 = FC3 + addr 0)
├─ "Register 40100"    →   Address: 99    (40100 = FC3 + addr 99)
├─ "Address 1000"      →   Address: 1000  (direct address)
└─ "Holding reg 50"    →   Address: 50    (direct address)
```

---

### 4. Length (Register Length)

**Type:** Integer (1-125)  
**Purpose:** Number of 16-bit registers to read

**Forward Transformation:**
```
Register Config: length = 2
         ↓
Modbus Config: B5.Rcount[index] = 2
```

**Reverse Transformation:**
```
Modbus Config: B5.Rcount[index] = 2
         ↓
Register Config: length = 2
```

**How to Determine Length:**

| Data Type | Registers | Example |
|-----------|-----------|---------|
| INT16, UINT16, BOOLEAN | 1 | Temperature (16-bit) |
| INT32, UINT32, FLOAT | 2 | Flow rate (32-bit) |
| INT64, UINT64, DOUBLE | 4 | High-precision value |
| STRING | Variable | Text string (1 reg = 2 chars) |

**Auto-Calculation:**
The tool can auto-fill this based on Format selection!

**Example:**
```
Format: INT16     → Length: 1 (auto)
Format: FLOAT     → Length: 2 (auto)
Format: UINT64    → Length: 4 (auto)
```

---

### 5. Format (Data Type)

**Type:** Integer code (8-26)  
**Purpose:** How to interpret the raw register bytes

**Forward Transformation:**
```
Register Config: format = 8 (INT16)
         ↓
Modbus Config: B5.c[index] = 8
```

**Reverse Transformation:**
```
Modbus Config: B5.c[index] = 8
         ↓
Register Config: format = 8
```

**Complete Format Table:**

| Code | Name | Size | Description | Example Use |
|------|------|------|-------------|-------------|
| **8** | INT16 | 1 reg | Signed 16-bit integer | Temperature (-32768 to 32767) |
| **9** | UINT16 | 1 reg | Unsigned 16-bit integer | Count (0 to 65535) |
| **10** | INT32 | 2 regs | Signed 32-bit integer | Large values |
| **11** | UINT32 | 2 regs | Unsigned 32-bit integer | Timestamps |
| **12** | FLOAT | 2 regs | 32-bit floating point | Precise decimals |
| **13** | BOOLEAN | 1 reg | True/False | On/Off status |
| **14** | STRING | Variable | Text string | Equipment name |
| **15** | INT64 | 4 regs | Signed 64-bit integer | Very large values |
| **16** | UINT64 | 4 regs | Unsigned 64-bit integer | Large counters |
| **17** | DOUBLE | 4 regs | 64-bit floating point | High precision |
| **18** | BCD16 | 1 reg | Binary-coded decimal | Display values |
| **19** | BCD32 | 2 regs | 32-bit BCD | Large BCD values |
| **20-26** | Advanced | Various | Packed formats | Special encodings |

**Common Formats for HVAC/Industrial:**
- Temperature: **INT16** (with multiplier 0.1)
- Pressure: **FLOAT** (direct decimal)
- Status: **BOOLEAN** (on/off)
- Setpoint: **INT16** or **FLOAT**
- Count: **UINT16** or **UINT32**

---

### 6. Multiplier (Scale Factor)

**Type:** Float  
**Purpose:** Scale the raw Modbus value to engineering units

**Forward Transformation:**
```
Register Config: multiplier = 0.1
         ↓
Modbus Config: B5.f[index] = 0.1
```

**Reverse Transformation:**
```
Modbus Config: B5.f[index] = 0.1
         ↓
Register Config: multiplier = 0.1
```

**Formula:**
```
Actual Value = Raw Modbus Value × Multiplier
```

**Common Multipliers:**

| Raw Value | Multiplier | Actual Value | Use Case |
|-----------|------------|--------------|----------|
| 255 | 0.1 | 25.5 | Temperature (°C) |
| 1450 | 1 | 1450 | Motor RPM |
| 50 | 10 | 500 | Pressure (kPa) |
| 123 | 0.01 | 1.23 | Flow (m³/h) |
| 1 | 1 | 1 | Boolean (no scaling) |
| 2500 | 0.001 | 2.5 | Voltage (V) |

**Example:**
```
Device Returns:  255 (raw)
Multiplier:      0.1
Result:          25.5°C

Device Returns:  1234 (raw)
Multiplier:      0.01
Result:          12.34 bar
```

**Special Cases:**
- `1` = No scaling (direct value)
- `0.1` = Divide by 10 (common for temperatures)
- `10` = Multiply by 10 (scale up)
- `0.001` = Divide by 1000 (millis to units)

---

### 7. Access Type

**Type:** String ("Read Only" or "Write")  
**Purpose:** Can the parameter be written to, or only read?

**Forward Transformation:**
```
Register Config: access_type = "Read Only"
         ↓
Modbus Config: B6.RP includes this param (verification read)
```

**Reverse Transformation:**
```
Modbus Config: Check if param in B6.RP
         ↓
Register Config: access_type = "Read Only" (if in B6)
                               = "Write" (if not in B6 and writable)
```

**Values:**
- **"Read Only"**: Cannot write, only read (sensors, status)
- **"Write"**: Can write values (setpoints, commands)

**Phase 1 Auto-Configuration:**
```
IF access_type == "Write":
    ✓ in_lua_buffer = "Yes"
    ✓ lua_category = "User Variable"
    ✓ Added to P2.RPCI
```

**Examples:**

| Parameter | Access Type | Reason |
|-----------|-------------|--------|
| Temperature | Read Only | Sensor reading |
| Pressure | Read Only | Sensor reading |
| Setpoint | Write | User can change |
| Manual Mode | Write | User control |
| Alarm Status | Read Only | System generated |
| Reset Command | Write | User action |

---

### 8. Cloud Output

**Type:** String ("Yes" or "No")  
**Purpose:** Should this parameter be sent to MQTT/cloud?

**Forward Transformation:**
```
Register Config: cloud_output = "Yes"
         ↓
ParamMap Config: P3.MPI includes this param
                P2.MPI includes this param (if Lua enabled)
```

**Reverse Transformation:**
```
ParamMap Config: Check if param in P3.MPI
         ↓
Register Config: cloud_output = "Yes" (if in P3.MPI)
                               = "No" (if not)
```

**Values:**
- **"Yes"**: Send to cloud/MQTT
- **"No"**: Internal use only

**Phase 1 Auto-Configuration:**
```
IF cloud_output == "Yes":
    ✓ in_lua_buffer = "Yes"
    ✓ lua_category = "Equipment"
    ✓ Added to P2.MPI
    ✓ Added to P3.MPI
```

**When to Use "Yes":**
- Monitored values (temperatures, pressures, flows)
- Status parameters (alarms, operating mode)
- Performance metrics (efficiency, energy consumption)
- Equipment state (on/off, running/stopped)

**When to Use "No":**
- Internal control parameters
- Temporary calculations
- Diagnostic registers
- Write-only commands
- Feedback parameters (paired with writes)

**Example:**
```
Equipment Monitoring (Cloud = Yes):
├─ Chiller temperature → Cloud
├─ VFD speed → Cloud
├─ Pump flow → Cloud
└─ System status → Cloud

Internal Control (Cloud = No):
├─ Temp setpoint → Internal (user sets, not monitored)
├─ Manual override → Internal (command only)
└─ Write feedback → Internal (verification)
```

---

## 🗂️ Part 2: JSON Mapping Fields (Optional)

These 4 fields define how parameters appear in the output JSON structure.

---

### 9. JSON Group

**Type:** String  
**Purpose:** Top-level category in output JSON

**Forward Transformation:**
```
Register Config: json_group = "Equipment"
         ↓
Modbus Config: B5.jGroup[index] = "Equipment"
```

**Reverse Transformation:**
```
Modbus Config: B5.jGroup[index] = "Equipment"
         ↓
Register Config: json_group = "Equipment"
```

**Common Values:**
- `Equipment` - Monitored equipment parameters
- `Settings` - User-configurable settings
- `Status` - System status parameters
- `Control` - Control parameters
- (Custom names allowed)

**JSON Output Structure:**
```json
{
  "Equipment": {        ← JSON Group
    "Chiller-1": {
      "Temperature": 25.5
    }
  },
  "Settings": {         ← JSON Group
    "Chiller-1": {
      "Setpoint": 22.0
    }
  }
}
```

---

### 10. JSON Unit

**Type:** String  
**Purpose:** Equipment/device identifier within the group

**Forward Transformation:**
```
Register Config: json_unit = "Chiller-1"
         ↓
Modbus Config: B5.jUnit[index] = "Chiller-1"
```

**Reverse Transformation:**
```
Modbus Config: B5.jUnit[index] = "Chiller-1"
         ↓
Register Config: json_unit = "Chiller-1"
```

**Examples:**
- `Chiller-1`, `Chiller-2` (multiple chillers)
- `VFD-1`, `VFD-2` (multiple VFDs)
- `AHU-North`, `AHU-South` (named by location)
- `Zone-1`, `Zone-2` (zones)

**JSON Output Structure:**
```json
{
  "Equipment": {
    "Chiller-1": {      ← JSON Unit
      "Temperature": 25.5,
      "Flow": 150
    },
    "Chiller-2": {      ← JSON Unit
      "Temperature": 24.8,
      "Flow": 145
    }
  }
}
```

---

### 11. JSON Key

**Type:** String  
**Purpose:** Parameter name in the output JSON

**Forward Transformation:**
```
Register Config: json_key = "Temperature"
         ↓
Modbus Config: B5.jKey[index] = "Temperature"
```

**Reverse Transformation:**
```
Modbus Config: B5.jKey[index] = "Temperature"
         ↓
Register Config: json_key = "Temperature"
```

**Best Practices:**
- Use clear, descriptive names
- CamelCase or snake_case
- Avoid spaces (use underscores)
- Be consistent across parameters

**Examples:**
```
Good:               Avoid:
Temperature         Temp1
SupplyPressure      SP
FlowRate           Flow_123
OperatingMode       Mode
AlarmStatus         Alm
```

**JSON Output Structure:**
```json
{
  "Equipment": {
    "Chiller-1": {
      "Temperature": 25.5,    ← JSON Key
      "Pressure": 1.2,        ← JSON Key
      "FlowRate": 150         ← JSON Key
    }
  }
}
```

---

### 12. Array Membership (Equipment Type)

**Type:** String  
**Purpose:** Groups parameters by equipment type for JKY/JKA arrays

**Forward Transformation:**
```
Register Config: array_membership = "Chiller"
         ↓
Modbus Config: B5.arrmem[index] = "Chiller"
ParamMap Config: JKY includes "Chiller"
                JKA groups params by type
```

**Reverse Transformation:**
```
Modbus Config: B5.arrmem[index] = "Chiller"
ParamMap Config: JKY array and JKA assignments
         ↓
Register Config: array_membership = "Chiller"
```

**Common Values:**
- Equipment types: `Chiller`, `VFD`, `Pump`, `AHU`, `FCU`, `Boiler`
- Generic: `Sensor`, `Actuator`, `Controller`
- Special: `None` (not in equipment grouping)

**How JKY/JKA Works:**
```
INPUT REGISTERS:
Param 1: array_membership = "Chiller"
Param 2: array_membership = "Chiller"
Param 3: array_membership = "VFD"
Param 4: array_membership = "Pump"
Param 5: array_membership = "None"

OUTPUT ParamMap Config:
{
  "JKY": ["Chiller", "VFD", "Pump"],    ← Unique types
  "JKA": [
    [1, 2],    ← Chiller params
    [3],       ← VFD params
    [4]        ← Pump params
  ]
  // Param 5 not included (None)
}
```

**Use Case:**
Firmware uses JKA to group parameters by equipment type for structured output.

---

## 🎛️ Part 3: Transparent Packet Configuration (Advanced)

These 6 fields manage packet organization and write/feedback pairing.

---

### 13. Packet # (Packet Number)

**Type:** Integer  
**Purpose:** Groups related parameters into polling packets

**Forward Transformation:**
```
Register Config: packet_num = 1
         ↓
(Used for packet organization, not directly in JSON)
```

**Reverse Transformation:**
```
(Not stored in firmware JSON)
         ↓
Register Config: packet_num = (empty or manual entry)
```

**Purpose:**
Group parameters that should be polled together in one Modbus transaction.

**Example:**
```
Packet 1:
├─ Param 1: Slave 1, Address 1000-1001
├─ Param 2: Slave 1, Address 1002
└─ Param 3: Slave 1, Address 1003-1004

Packet 2:
├─ Param 4: Slave 1, Address 2000
└─ Param 5: Slave 1, Address 2001
```

**Benefits:**
- Optimized Modbus communication
- Reduced bus traffic
- Faster polling

---

### 14. Packet Start (Packet Start Address / SA)

**Type:** Integer  
**Purpose:** First Modbus address the firmware reads for this packet

**How It's Calculated:**
The minimum address among all parameters in the packet.

**Example:**
```
Packet contains parameters at addresses: [32, 33, 35, 38, 39, 41]
→ Packet Start (SA) = 32 (the minimum)
→ Packet Regs (NRT) = 10 (41 - 32 + 1 = 10 addresses)
→ Firmware Command: READ_HOLDING_REGISTERS(address=32, count=10)
```

**Forward Transformation:**
```
Register Config: Click "Calculate Packets"
         ↓
Auto-calculated: packet_sa = min(all addresses in packet)
         ↓
Modbus Config: B4.SA = [0, 32, 1561, ...]
```

**Reverse Transformation:**
```
Modbus Config: B4.SA = [0, 32, 1561, ...]
         ↓
Register Config: packet_sa = 0, 32, 1561, ... (per parameter)
```

**Auto-Filled:** Yes, when you click "🔄 Calculate Packets" button

**Note:** This is the actual address sent in the Modbus command, not necessarily the first parameter's address if there are gaps.

---

### 15. Packet Regs (Packet Register Count / NRT)

**Type:** Integer  
**Purpose:** Number of consecutive Modbus addresses the firmware reads in a single transaction

**How It's Calculated:**
The firmware reads a **contiguous block** of addresses. Even if only some addresses are mapped to parameters, the firmware reads all addresses in the span.

**Example:**
```
Parameters at addresses: [0, 1, 2, 3, 4, 5]
→ Packet Start (SA) = 0
→ Packet Regs (NRT) = 6
→ Firmware Command: READ_HOLDING_REGISTERS(address=0, count=6)
   
Parameters at addresses: [100, 105] (both length=1)
→ Packet Start (SA) = 100
→ Packet Regs (NRT) = 6 (reads 100-105, even though 101-104 unmapped)
→ Firmware Command: READ_HOLDING_REGISTERS(address=100, count=6)
```

**Multi-Register Parameters:**
If a parameter has length>1, all occupied addresses are counted:
```
Parameter at address 100, length=4 (32-bit float)
→ Occupies addresses: [100, 101, 102, 103]
→ Packet Regs includes all 4 addresses
```

**Forward Transformation:**
```
Register Config: Click "Calculate Packets"
         ↓
Auto-calculated: packet_nrt = (max_addr - min_addr + 1)
         ↓
Modbus Config: B4.NRT = [6, 1, 8, ...]
```

**Reverse Transformation:**
```
Modbus Config: B4.NRT = [6, 1, 8, ...]
         ↓
Register Config: packet_nrt = 6, 1, 8, ... (per parameter)
```

**Auto-Filled:** Yes, when you click "🔄 Calculate Packets" button

**Critical Constraint:** Maximum 70 addresses per packet (firmware limitation)

---

### 16. Param Type (Parameter Type)

**Type:** String ("write", "feedback", "read_only")  
**Purpose:** Classifies parameter role in write operations

**Forward Transformation:**
```
Register Config: param_type = "write"
         ↓
(Used for write/feedback pairing logic)
```

**Reverse Transformation:**
```
(Not directly stored, inferred from access and pairing)
         ↓
Register Config: param_type = "write" (if paired)
```

**Values:**
- **"write"**: Write command parameter
- **"feedback"**: Feedback read after write
- **"read_only"**: Read-only parameter

**Write/Feedback Pairing:**
```
Write Param:              Feedback Param:
├─ param_type: write      ├─ param_type: feedback
├─ paired_with: 5         ├─ paired_with: 4
├─ Address: 2000          ├─ Address: 2001
└─ Action: Send command   └─ Action: Verify write

Workflow:
1. User writes value to param 4 (address 2000)
2. Firmware writes to device
3. Firmware reads param 5 (address 2001) for verification
4. If mismatch → retry or alert
```

---

### 17. Paired With

**Type:** String (B5 ID)  
**Purpose:** Links write parameters with feedback parameters

**Forward Transformation:**
```
Register Config: paired_with = "5"
         ↓
(Used to establish bidirectional pairing)
```

**Reverse Transformation:**
```
(Not stored in firmware JSON)
         ↓
Register Config: paired_with = (empty or manual entry)
```

**Example:**
```
Register 4 (Write):
├─ B5 ID: 4
├─ Access: Write
├─ Address: 2000
├─ param_type: write
└─ paired_with: "5"  ← Links to feedback

Register 5 (Feedback):
├─ B5 ID: 5
├─ Access: Read Only
├─ Address: 2001
├─ param_type: feedback
└─ paired_with: "4"  ← Links back to write
```

**Use Case:**
Ensures write operations are verified by reading back the value.

---

### 18. JKA Index (Equipment Group Index)

**Type:** Integer (-1 or 0+)  
**Purpose:** Directly assigns parameter to equipment group index

**Forward Transformation:**
```
Register Config: jka_param_index = 0
         ↓
ParamMap Config: Assigned to JKA[0] (first equipment group)
```

**Reverse Transformation:**
```
ParamMap Config: Parameter in JKA[0]
         ↓
Register Config: jka_param_index = 0
```

**Values:**
- `-1` = Not in any equipment group
- `0` = First equipment group (JKY[0])
- `1` = Second equipment group (JKY[1])
- etc.

**Relationship with Array Membership:**
```
Method 1 (Automatic):
array_membership = "Chiller"  → Firmware maps to JKY index

Method 2 (Manual):
jka_param_index = 0  → Directly assigns to JKY[0]
```

---

## 🔧 Part 4: Lua Buffer Configuration

These 4 fields control Lua Buffer integration (Phase 1 auto-configured).

---

### 19. In Lua Buffer

**Type:** String ("Yes" or "No")  
**Purpose:** Should this parameter be stored in Lua Buffer?

**Forward Transformation:**
```
Register Config: in_lua_buffer = "Yes"
         ↓
ParamMap Config: Included in P2.MPI or P2.RPCI
```

**Reverse Transformation:**
```
ParamMap Config: Check if param in P2.MPI or P2.RPCI
         ↓
Register Config: in_lua_buffer = "Yes" (if in P2)
                               = "No" (if not)
```

**Phase 1 Auto-Configuration:**
```
IF cloud_output == "Yes":
    → in_lua_buffer = "Yes"

IF access_type == "Write":
    → in_lua_buffer = "Yes"
```

**Purpose:**
Parameters in Lua Buffer are available for:
- Lua control scripts
- Cloud output
- User modification (if User Variable)

---

### 20. Lua Category

**Type:** String ("Equipment" or "User Variable")  
**Purpose:** How the parameter is classified in Lua Buffer

**Forward Transformation:**
```
Register Config: lua_category = "Equipment"
         ↓
ParamMap Config: P2.MPI (if Equipment)
                P2.RPCI (if User Variable)
```

**Reverse Transformation:**
```
ParamMap Config: Check if param in P2.MPI or P2.RPCI
         ↓
Register Config: lua_category = "Equipment" (if P2.MPI)
                               = "User Variable" (if P2.RPCI)
```

**Phase 1 Auto-Configuration:**
```
IF cloud_output == "Yes":
    → lua_category = "Equipment"

IF access_type == "Write":
    → lua_category = "User Variable"
```

**Categories:**
- **"Equipment"**: Monitored parameters, cloud output, control logic
- **"User Variable"**: User-settable values, setpoints, commands

**P2 Arrays:**
```
P2.MPI  (Equipment):        P2.RPCI (User Variables):
├─ Temperature readings     ├─ Temperature setpoints
├─ Pressure readings        ├─ Control commands
├─ Flow rates               ├─ User preferences
└─ Status parameters        └─ Manual overrides
```

---

### 21. LBI Position (Lua Buffer Index)

**Type:** String ("Auto" or integer)  
**Purpose:** Position in Lua Buffer array

**Forward Transformation:**
```
Register Config: lbi_position = "Auto"
         ↓
(Firmware auto-assigns sequential positions)
```

**Reverse Transformation:**
```
(Not directly stored)
         ↓
Register Config: lbi_position = "Auto" (or manual if specified)
```

**Values:**
- **"Auto"**: Firmware assigns position automatically
- **Integer**: Manually specify position (advanced use)

**Use Case:**
For most applications, use "Auto". Manual positioning only needed for specific firmware requirements.

---

### 22. LBI Data Type (Lua Buffer Data Type)

**Type:** String ("Number", "Boolean", "String")  
**Purpose:** Data type in Lua Buffer array

**Forward Transformation:**
```
Register Config: lbi_data_type = "Number"
         ↓
(Used by Lua scripts to interpret data)
```

**Reverse Transformation:**
```
(Not directly stored, inferred from format)
         ↓
Register Config: lbi_data_type = "Number" (default)
```

**Values:**
- **"Number"**: Numeric values (most common)
- **"Boolean"**: True/False values
- **"String"**: Text strings

**Mapping:**
```
Format → LBI Data Type:
├─ INT16, UINT16, INT32, UINT32, FLOAT → Number
├─ BOOLEAN → Boolean
└─ STRING → String
```

---

## 📦 Part 5: Legacy Packet Field Names (Internal)

These alternate field names may appear in imported JSON files or internal code.

---

### 23-25. Legacy Packet Field Names

**Alternate Names:**
- **Packet_Num** / **packet_num** → Displayed as **Packet #** in UI
- **Packet_SA** / **packet_sa** / **packet_start_addr** → Displayed as **Packet Start** in UI  
- **Packet_NRT** / **packet_nrt** / **packet_register_count** → Displayed as **Packet Regs** in UI

**Status:** Active and fully functional. These are internal field names that map to the visible columns.

**Implementation:** The application uses property aliases internally:
```python
reg.packet_sa == reg.packet_start_addr  # Same value
reg.packet_nrt == reg.packet_register_count  # Same value
```

**Usage:** Use the "🔄 Calculate Packets" button to automatically populate these fields based on firmware constraints:
- Group by Slave ID + Function Code
- Maximum 70 parameters per packet
- **Maximum 70 address span per packet** (critical firmware limit)
- Auto-calculate SA (start address) and NRT (register count)

---

## 🔒 Part 6: Internal Metadata (Hidden/Auto-Generated)

These 12 fields are auto-generated or internal. Not shown in Add dialog.

---

### 26. B5 ID (Parameter Index)

**Type:** Integer (auto-increment)  
**Purpose:** Unique identifier for each parameter in firmware

**Forward Transformation:**
```
Register Config: (auto-generated: 1, 2, 3, ...)
         ↓
Modbus Config: B5.s_Indx = [1, 2, 3, ...]
```

**Reverse Transformation:**
```
Modbus Config: B5.s_Indx[index]
         ↓
Register Config: b5_id = extracted value
```

**Notes:**
- Auto-assigned sequentially (1, 2, 3, ...)
- Used throughout firmware for parameter references
- Referenced in P2, P3, B6, JKA arrays

---

### 27-37. Other Internal Fields

**Equipment Group** - Equipment classification  
**Device Name** - Device identifier  
**Equipment Type** - Type of equipment  
**JKA Equipment Index** - Equipment group index  
**Lua Buffer Note** - Internal notes  
**Parameter Type (internal)** - Internal type classification  
**Write Param ID** - Write parameter reference  
**Feedback Param ID** - Feedback parameter reference  
**P2 MPI Index** - Position in P2.MPI  
**P3 MPI Index** - Position in P3.MPI  
**Legacy Format** - Old format code

**Status:** Auto-generated by tool, not user-editable.

---

## 🔄 Part 7: Forward vs Reverse Comparison

### Key Differences

```
┌─────────────────────────────────────────────────────────────────────┐
│            FORWARD vs REVERSE TRANSFORMATION                        │
├────────────────────────┬────────────────────────┬───────────────────┤
│ Aspect                 │ Forward (Reg→JSON)     │ Reverse (JSON→Reg)│
├────────────────────────┼────────────────────────┼───────────────────┤
│ Starting Point         │ User enters registers  │ Import firmware   │
│                        │ in GUI                 │ JSON files        │
├────────────────────────┼────────────────────────┼───────────────────┤
│ Essential Fields       │ User must fill 8 fields│ Extracted from B5 │
├────────────────────────┼────────────────────────┼───────────────────┤
│ Phase 1 Auto-Config    │ ✅ Yes (Cloud→Lua)     │ ✅ Yes (P2/P3→Lua)│
│                        │       (Write→User Var) │                   │
├────────────────────────┼────────────────────────┼───────────────────┤
│ JSON Mapping           │ User fills (optional)  │ Extracted from B5 │
├────────────────────────┼────────────────────────┼───────────────────┤
│ Lua Buffer Config      │ Auto-configured        │ Inferred from P2  │
├────────────────────────┼────────────────────────┼───────────────────┤
│ Transparent Packet     │ User fills (optional)  │ Not stored (lost) │
├────────────────────────┼────────────────────────┼───────────────────┤
│ B5 ID                  │ Auto-generated         │ Preserved from B5 │
├────────────────────────┼────────────────────────┼───────────────────┤
│ Output                 │ Modbus_Config.json     │ Register list in  │
│                        │ ParamMap_Config.json   │ GUI table         │
└────────────────────────┴────────────────────────┴───────────────────┘
```

### Field Persistence

**Always Preserved:**
✅ Essential fields (Slave, FC, Address, Length, Format, Multiplier, Access, Cloud)  
✅ JSON mapping (Group, Unit, Key, Array)  
✅ B5 ID (parameter index)  
✅ Lua Buffer settings (In Lua, Category)

**May Be Lost:**
⚠️ Transparent packet settings (Packet #, Start, Regs, Param Type, Paired With, JKA Index)  
⚠️ User comments or notes

**Reason:**
Firmware JSONs (Modbus_Config, ParamMap_Config) don't store transparent packet details. They're reorganized into optimal polling packets.

### Round-Trip Workflow

```
1. USER CREATES REGISTERS (Forward)
   ├─ Add registers in GUI
   ├─ Fill 8 essential fields
   ├─ (Optional) Fill advanced fields
   └─ Phase 1 auto-config applies

2. GENERATE FILES (Forward)
   ├─ Click "Generate All Configurations"
   ├─ Tool creates Modbus_Config.json
   ├─ Tool creates ParamMap_Config.json
   └─ Tool creates Register_Config.json (backup)

3. DEPLOY TO FIRMWARE
   ├─ Copy JSONs to ESP32 /data folder
   ├─ Upload to device
   └─ Firmware uses configs

4. LATER: IMPORT BACK (Reverse)
   ├─ Import Modbus_Config.json + ParamMap_Config.json
   ├─ Tool reconstructs registers
   ├─ Essential fields preserved
   ├─ Lua config inferred from P2/P3
   └─ Transparent config lost (must re-enter if needed)

5. EDIT & REGENERATE
   ├─ Edit registers in GUI
   ├─ Add/remove parameters
   ├─ Re-generate JSONs
   └─ Re-deploy to firmware
```

---

## 💡 Part 8: Common Scenarios

### Scenario 1: Simple Temperature Sensor (Read, Cloud)

```
FIELDS TO FILL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Essential:
  Slave ID: 1
  Function Code: 4 (Input Register)
  Address: 1000
  Length: 1 (auto from format)
  Format: 8 - INT16
  Multiplier: 0.1 (raw 255 → 25.5°C)
  Access: Read Only
  Cloud Output: Yes

JSON Mapping:
  JSON Group: Equipment
  JSON Unit: Chiller-1
  JSON Key: SupplyTemp
  Array: Chiller

AUTO-CONFIGURED (Phase 1):
  In Lua Buffer: Yes (because Cloud=Yes)
  Lua Category: Equipment (because Cloud=Yes)
  LBI Position: Auto
  LBI Data Type: Number

RESULT IN FIRMWARE:
  ✓ B5 parameter created
  ✓ Added to B6.RP (verification read)
  ✓ Added to P2.MPI (Equipment)
  ✓ Added to P3.MPI (Cloud output)
  ✓ Grouped in JKA under "Chiller"
```

### Scenario 2: Setpoint (Write, Internal)

```
FIELDS TO FILL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Essential:
  Slave ID: 1
  Function Code: 3 (Holding Register)
  Address: 2000
  Length: 1
  Format: 8 - INT16
  Multiplier: 0.1
  Access: Write
  Cloud Output: No (internal control)

JSON Mapping:
  JSON Group: Settings
  JSON Unit: Chiller-1
  JSON Key: TempSetpoint
  Array: None (not in equipment grouping)

AUTO-CONFIGURED (Phase 1):
  In Lua Buffer: Yes (because Access=Write)
  Lua Category: User Variable (because Access=Write)
  LBI Position: Auto
  LBI Data Type: Number

RESULT IN FIRMWARE:
  ✓ B5 parameter created
  ✗ NOT in B6.RP (write command, not read)
  ✓ Added to P2.RPCI (User Variable)
  ✗ NOT in P3.MPI (Cloud=No, internal only)
  ✗ NOT in JKA (Array=None)
```

### Scenario 3: Write with Feedback Pair

```
WRITE PARAMETER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Essential:
  Slave ID: 1
  Function Code: 3
  Address: 3000
  Length: 1
  Format: 8 - INT16
  Multiplier: 1
  Access: Write
  Cloud Output: No

Advanced:
  Param Type: write
  Paired With: 5 (B5 ID of feedback param)

FEEDBACK PARAMETER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Essential:
  Slave ID: 1
  Function Code: 3
  Address: 3001
  Length: 1
  Format: 8 - INT16
  Multiplier: 1
  Access: Read Only
  Cloud Output: No

Advanced:
  Param Type: feedback
  Paired With: 4 (B5 ID of write param)

RESULT:
  ✓ Write param in P2.RPCI (User Variable)
  ✓ Feedback param in B6.RP (verification)
  ✓ Bidirectional pairing maintained
  Firmware workflow:
    1. User writes to param 4
    2. Firmware writes to device (addr 3000)
    3. Firmware reads param 5 (addr 3001)
    4. Compares and alerts if mismatch
```

---

## 📖 Part 9: Quick Decision Guide

### "Which fields do I NEED to fill?"

**Minimum Required (8 fields):**
1. ✅ Slave ID
2. ✅ Function Code
3. ✅ Address
4. ✅ Length (or auto from Format)
5. ✅ Format
6. ✅ Multiplier
7. ✅ Access Type
8. ✅ Cloud Output

**Everything else is optional or auto-configured!**

---

### "Should I set Cloud Output to Yes or No?"

```
YES if:
✓ Parameter should be monitored remotely
✓ Parameter sent to MQTT/cloud dashboard
✓ Parameter used in cloud analytics
✓ Parameter visible in mobile app

Examples: Temperature, Pressure, Flow, Status, Alarms

NO if:
✓ Parameter is internal control only
✓ Parameter is a write command
✓ Parameter is temporary/diagnostic
✓ Parameter is a feedback read

Examples: Setpoints, Commands, Write-feedback pairs
```

---

### "When do I need to fill Transparent Config?"

**Most users: Skip it!**

**Fill if:**
- You need specific packet organization
- You're pairing write/feedback parameters
- You're assigning to equipment groups manually

**Tool handles this automatically for most cases.**

---

### "What happens if I import then export?"

```
PRESERVED:
✓ All essential fields
✓ JSON mapping
✓ Lua Buffer config
✓ B5 IDs

MAY BE LOST:
⚠️ Transparent packet settings
⚠️ Manual packet organization
⚠️ Write/feedback pairing details

RECOMMENDATION:
Keep Register_Config.json as master backup!
(Tool saves this automatically when generating)
```

---

## 🎓 Summary

### Field Count by Category

```
📊 37 TOTAL FIELDS:

Essential (User fills):          8 fields  ⭐
JSON Mapping (Optional):         4 fields
Transparent Config (Advanced):   6 fields
Lua Buffer (Auto):               4 fields
Legacy (Deprecated):             3 fields
Internal (Auto):                12 fields
```

### Complexity Levels

```
BEGINNER:
Fill only 8 essential fields
Let Phase 1 auto-config handle the rest
Result: Functional configuration ✓

INTERMEDIATE:
Fill essential + JSON mapping (12 fields)
Result: Structured output + cloud integration ✓

ADVANCED:
Fill essential + JSON + transparent config (18 fields)
Result: Full control over firmware behavior ✓

EXPERT:
Understand all 37 fields
Result: Maximum flexibility ✓
```

---

## 📞 Additional Resources

- **User Guide:** [USER_GUIDE.md](USER_GUIDE.md) - How to use the tool
- **Engineer Guide:** [APPLICATION_ENGINEER_GUIDE.md](APPLICATION_ENGINEER_GUIDE.md) - System integration
- **Visual Guide:** [FORWARD_LOGIC_VISUAL_GUIDE.md](FORWARD_LOGIC_VISUAL_GUIDE.md) - Visual explanations
- **Developer Guide:** [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Code details

---

**Last Updated:** February 9, 2026  
**Version:** 6.6  
**Maintainer:** Thermelgy Firmware Team

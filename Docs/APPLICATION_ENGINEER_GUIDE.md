# 🔧 Modbus Register Configuration Tool - Application Engineer Guide

**Version:** 6.6  
**Date:** February 2026  
**Target Audience:** Application Engineers, System Integrators

---

## 🎯 Overview

This guide covers **advanced configuration**, **firmware integration**, and **system-level setup** for deploying Modbus register configurations on Thermelgy BMIoT Gateway devices.

---

## 📐 Architecture Understanding

### Configuration Flow

```
┌─────────────────────┐
│  GUI Application    │
│  (This Tool)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Register_Config.json│ ◄── Master Config
└──────────┬──────────┘
           │
           ├──► FORWARD GENERATION
           │
    ┌──────┴──────┬────────────┐
    ▼             ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ Modbus  │  │ ParamMap│  │ Register│
│ Config  │  │ Config  │  │ Config  │
└─────────┘  └─────────┘  └─────────┘
     │            │            │
     └────────────┴────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │  ESP32 Firmware  │
        │  (/data folder)  │
        └──────────────────┘
```

### Generated Files Purpose

| File | Purpose | Used By |
|------|---------|---------|
| **Modbus_Config.json** | Polling schedule, packet definitions | Modbus task |
| **ParamMap_Config.json** | Parameter mapping, Lua integration | ParamMap module |
| **Register_Config.json** | Complete register backup | Configuration tool |

---

## 🏗️ Configuration Blocks

### Block Structure (Firmware Mapping)

The tool generates firmware-compatible structures:

#### Block 4 (B4) - Slave Address List
```json
{
  "B4": {
    "SA": [1, 2, 3]  // Unique slave IDs
  }
}
```

#### Block 5 (B5) - Parameter Definitions
```json
{
  "B5": {
    "s_Indx": [1, 2, 3],      // Parameter index
    "jGroup": ["Equipment"],   // JSON group
    "jUnit": ["Chiller-1"],    // JSON unit
    "jKey": ["Temperature"],   // JSON key
    "arrmem": ["Chiller"]      // Array membership
  }
}
```

#### Block 6 (B6) - Verification Reads
```json
{
  "B6": {
    "RP": [1, 5, 10]  // Read-only parameter IDs
  }
}
```

#### P2 - Lua Buffer Split
```json
{
  "P2": {
    "MPI": [1, 2, 3],   // Equipment params (cloud output)
    "RPCI": [4, 5]      // User variables (write access)
  }
}
```

#### P3 - Cloud Parameters
```json
{
  "P3": {
    "MPI": [1, 2, 3]  // Parameters sent to cloud
  }
}
```

---

## 🧩 Phase 1 Smart Logic (Auto-Configuration)

### Rule 1: Cloud Output Triggers Lua Buffer

```
IF Cloud Output = "Yes"
THEN:
  ✓ In Lua Buffer = "Yes"
  ✓ Lua Category = "Equipment"
  ✓ Parameter added to P2.MPI (Equipment array)
  ✓ Parameter added to P3.MPI (Cloud output)
```

**Firmware Behavior:**
- Parameter stored in Lua Buffer
- Available for control logic
- Sent to MQTT/HTTPS cloud

### Rule 2: Write Access Triggers Lua Buffer

```
IF Access = "Write"
THEN:
  ✓ In Lua Buffer = "Yes"
  ✓ Lua Category = "User Variable"
  ✓ Parameter added to P2.RPCI (Remote Param array)
```

**Firmware Behavior:**
- Parameter stored in Lua Buffer
- User can modify from GUI/cloud
- NOT sent to cloud automatically

### Override Capability

Users can manually change defaults in **Advanced Options**:
- Change Lua Category: Equipment ↔ User Variable
- Disable Lua Buffer (if firmware allows)
- Adjust LBI position manually

---

## 🔍 Transparent Packet Configuration

### What are Transparent Packets?

Grouping of Modbus registers for **optimized polling** and **batch operations**.

### Configuration Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Packet #** | Packet identifier | 1, 2, 3 |
| **Packet Start** | First register address | 1000 |
| **Packet Regs** | Total registers in packet | 10 |
| **Param Type** | write / feedback / read_only | write |
| **Paired With** | Link write ↔ feedback | 5 (B5 ID) |
| **JKA Index** | Equipment group index | 0, 1, 2, -1 |

### Pairing Write Parameters with Feedback

**Example Configuration:**

**Write Parameter (Control Command):**
```
B5 ID: 10
Address: 5000
Access: Write
Param Type: write
Paired With: 11  ← Links to feedback param
```

**Feedback Parameter (Confirmation Read):**
```
B5 ID: 11
Address: 5001
Access: Read Only
Param Type: feedback
Paired With: 10  ← Links back to write param
```

**Firmware Behavior:**
1. User writes to parameter 10 (address 5000)
2. Firmware writes value to Modbus device
3. Firmware reads parameter 11 (address 5001) for verification
4. If mismatch → retry or alert

---

## 🗂️ Equipment Groups (JKA Mapping)

### JKY Array Structure

```json
{
  "JKY": [
    "Chiller",    // Index 0
    "VFD",        // Index 1
    "Pump",       // Index 2
    "AHU"         // Index 3
  ]
}
```

### Assigning Parameters to Equipment

**Method 1: Array Membership**
```
Array Membership: Chiller
→ Firmware maps to JKY[0]
```

**Method 2: JKA Index**
```
JKA Index: 1
→ Directly assigns to JKY[1] = "VFD"
```

**Special Values:**
- `JKA Index = -1` → No equipment group
- `JKA Index = 0` → First equipment group

---

## 📊 Field Mapping Reference

### Register_Config.json ↔ Firmware

| GUI Field | JSON Key | Firmware Block | Notes |
|-----------|----------|----------------|-------|
| Slave ID | slave_id | B4.SA | Unique list |
| Address | address | B5.modID | Register address |
| Function Code | function_code | B5.func_c | 3 or 4 |
| Length | length | B5.Rcount | Register count |
| Format | format | B5.c | Data type code |
| Multiplier | multiplier | B5.f | Float value |
| Access | access_type | B6.RP detection | RO → B6 |
| Cloud Output | cloud_output | P3.MPI | Yes → P3 |
| JSON Group | json_group | B5.jGroup | Group name |
| JSON Unit | json_unit | B5.jUnit | Unit name |
| JSON Key | json_key | B5.jKey | Key name |
| Array | array_membership | B5.arrmem, JKA | Equipment type |

---

## ⚙️ Advanced Configuration Scenarios

### Scenario 1: Multi-Slave Polling

**Setup:**
```
Register 1: Slave 1, Address 1000
Register 2: Slave 2, Address 1000
Register 3: Slave 3, Address 1000
```

**Generated:**
```json
{
  "B4": {"SA": [1, 2, 3]},
  "Modbus_Config": {
    "slaves": [
      {"id": 1, "packets": [...]},
      {"id": 2, "packets": [...]},
      {"id": 3, "packets": [...]}
    ]
  }
}
```

### Scenario 2: Complex Control Loop

**Temperature Read:**
```
Slave: 1, Address: 1000, FC: 3
Access: Read Only
Cloud Output: Yes
→ P2.MPI, P3.MPI
```

**Setpoint Write:**
```
Slave: 1, Address: 2000, FC: 3
Access: Write
Paired With: [B5 ID of feedback]
→ P2.RPCI, Param Type = write
```

**Setpoint Feedback:**
```
Slave: 1, Address: 2001, FC: 3
Access: Read Only
Paired With: [B5 ID of write]
→ B6.RP, Param Type = feedback
```

### Scenario 3: Equipment Grouping

**Chiller Group:**
```json
{
  "Array": "Chiller",
  "JKA Index": 0,
  "Parameters": [
    {"Key": "Temp", "Address": 1000},
    {"Key": "Flow", "Address": 1001},
    {"Key": "Status", "Address": 1002}
  ]
}
```

**Output JSON Structure:**
```json
{
  "Equipment": {
    "Chiller": {
      "Chiller-1": {
        "Temp": 25.5,
        "Flow": 150,
        "Status": 1
      }
    }
  }
}
```

---

## 🔬 Testing & Validation

### Pre-Deployment Checklist

#### 1. Register Configuration
- [ ] All slave IDs are correct (1-247)
- [ ] No overlapping addresses for same slave
- [ ] Function codes match device capabilities
- [ ] Data formats match Modbus device specs
- [ ] Multipliers produce correct units

#### 2. Generation Validation
- [ ] Generate all files without errors
- [ ] Check B4.SA contains all unique slaves
- [ ] Verify B5 array lengths match
- [ ] Confirm P2 split (MPI vs RPCI)
- [ ] Check P3.MPI for cloud parameters

#### 3. Firmware Integration
- [ ] Copy files to `/data` folder
- [ ] Upload to ESP32 using PlatformIO
- [ ] Monitor serial console for errors
- [ ] Verify Modbus polling starts
- [ ] Check Lua Buffer initialization

### Testing Tools

**Modbus Simulator:**
```bash
# Use included Modbus Slave Software
Modbus Slave Software/Mbslave6.mbs
```

**Configuration Test:**
```python
# Run automated tests
python test_phase1_autoconfig.py
python test_gui_integration.py
python verify_examples.py
```

---

## 🚀 Deployment Workflow

### Step 1: Configure Registers
1. Open application
2. Add all Modbus registers
3. Set JSON mappings
4. Configure transparency settings
5. Export Register_Config.json

### Step 2: Generate Firmware Files
1. Click "Generate All Configurations"
2. Verify no errors in output
3. Review generated files

### Step 3: Deploy to Device
```bash
# Copy to firmware data folder
cp Generated_*.json ../Thermelgy-Gateway-BMIoT/data/

# Build and upload
cd ../Thermelgy-Gateway-BMIoT
pio run -t upload
pio run -t uploadfs  # Upload SPIFFS
```

### Step 4: Verify Operation
1. Connect to device serial console
2. Monitor Modbus polling logs
3. Check Lua Buffer initialization
4. Verify cloud parameter publication
5. Test write parameters from GUI

---

## 🐛 Troubleshooting

### Issue: Parameters Not in Lua Buffer

**Check:**
- Cloud Output or Write Access set?
- Phase 1 auto-config enabled?
- Manual override in Advanced Options?

**Solution:**
- Verify "In Lua Buffer" = "Yes"
- Check Lua Category assignment
- Regenerate configuration

### Issue: Write Parameters Not Working

**Check:**
- Access Type = "Write"?
- Feedback parameter configured?
- Pairing correct (Paired With field)?

**Solution:**
- Set Param Type = "write"
- Create feedback parameter
- Link with B5 ID in "Paired With"

### Issue: Cloud Data Missing Parameters

**Check:**
- Cloud Output = "Yes"?
- Parameter in P3.MPI array?
- Firmware cloud config correct?

**Solution:**
- Enable Cloud Output
- Regenerate ParamMap_Config
- Check MQTT connection

---

## 📚 Best Practices

### 1. Configuration Management
✅ **DO:**
- Version control Register_Config.json
- Document equipment mapping
- Use descriptive JSON key names
- Keep backup copies

❌ **DON'T:**
- Edit generated files manually
- Use special characters in names
- Create duplicate slave/address combinations

### 2. Performance Optimization
- Group consecutive registers in packets
- Minimize polling frequency for slow-changing data
- Use appropriate data formats (avoid FLOAT for integers)
- Balance cloud output (don't send everything)

### 3. Security Considerations
- Validate write parameter ranges in Lua
- Implement timeout for feedback verification
- Log configuration changes
- Secure device firmware updates

---

## 📞 Support Resources

- **Firmware Documentation:** See main README.md
- **API Reference:** See API Documentation folder
- **Command Reference:** See Doc/Command Doc/
- **Bug Reports:** See Bugs folder

---

## 📝 Revision History

| Version | Date | Changes |
|---------|------|---------|
| 6.6 | Feb 2026 | Phase 1 auto-config, transparent packets |
| 6.5 | Jan 2026 | Lua Buffer integration |
| 6.0 | Dec 2025 | Initial GUI release |

---

**Last Updated:** February 8, 2026  
**Application Version:** v6.6  
**Firmware Compatibility:** v3.0+

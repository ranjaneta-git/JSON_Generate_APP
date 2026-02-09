# 📘 Modbus Register Configuration Tool - User Guide

**Version:** 6.7+  
**Date:** February 9, 2026  
**Target Audience:** End Users (Operators, Technicians)

---

## 🎯 Purpose

This tool provides a **graphical interface** to manage Modbus register configurations and generate firmware-compatible JSON files for the Thermelgy BMIoT Gateway.

**New in v6.7:**
- 🛡️ **Manual Override Mode** - Control which ParamMap arrays parameters belong to
- 🐛 **Bug Fixes** - Lua Buffer fields now properly saved/loaded
- ✅ **38 Configuration Fields** - Complete firmware control

---

## 🚀 Quick Start

### Starting the Application

**Windows:**
```batch
Double-click: Start_Application.bat
```

**Command Line:**
```bash
python modbus_tkinter_app_v6.6_complete.py
```

---

## 📋 Main Interface Overview

### Navigation Tabs

1. **📄 Register Configuration** - Main workspace for managing Modbus registers
2. **📊 Generation Panel** - Generate firmware JSON files
3. **ℹ️ About/Help** - Version info and guidance

---

## ✏️ Working with Registers

### Adding a New Register

1. Click **➕ Add Register** button
2. Fill in the **8 Essential Fields** (marked with ★):
   - **Slave ID**: Modbus device ID (1-247)
   - **Function Code**: 3 (Holding) or 4 (Input)
   - **Address**: Register address (0-65535)
   - **Length**: Number of registers (1-125)
   - **Format**: Data type (INT16, UINT32, FLOAT, etc.)
   - **Multiplier**: Scale factor for value conversion
   - **Access Type**: Read Only / Read & Write
   - **Cloud Output**: Include in cloud/MQTT output (Yes/No)

3. *(Optional)* Click **▶ Advanced Options** to set:
   - JSON mapping (Group, Unit, Key)
   - Array Membership
   - Transparent packet settings
   - Write/Feedback pairing

4. Click **💾 Add Register**

### Editing a Register

**Method 1:** Double-click the row in the table  
**Method 2:** Select row → Click **✏️ Edit Selected**

- Modify any field
- Click **💾 Save Changes**

### Deleting Registers

1. Select one or more rows
2. Click **🗑️ Delete Selected**
3. Confirm deletion

### Clear All

Click **🧹 Clear All** to remove all registers (confirmation required)

---

## 📂 File Operations

### Loading Configuration

1. Click **📥 Import Registers**
2. Select `Register_Config.json` file
3. Registers load into the table

**Supported Formats:**
- Standard Register_Config.json
- Legacy formats with field name variations

### Exporting Configuration

1. Click **💾 Export Registers**
2. Choose save location
3. File saved as `Register_Config.json`

**What's Exported:**
- All register definitions
- Metadata fields
- Transparent configuration
- Lua Buffer settings

### Sample Data

Click **📋 Load Sample** to load example configurations for testing

---

## ⚡ Generating Firmware Files

### Step 1: Configure Registers
Add all Modbus registers with correct settings

### Step 2: Calculate Packet Assignments (Recommended)

**What are Packets?**
Packets group parameters for efficient Modbus communication. The firmware reads multiple registers in a single Modbus command when they're grouped in the same packet.

**How to Calculate:**
1. Click **🔄 Calculate Packets** button (purple button in toolbar)
2. Review the preview dialog showing:
   - Total packets generated
   - Parameters per packet
   - Modbus commands (e.g., FC3(address=0, count=6))
   - Validation warnings/errors
3. Click **"✅ Proceed to Generate"** or **"Close & Review"**

**Packet Constraints (Firmware Requirements):**
- Same Slave ID + Function Code per packet
- Maximum 70 registers per packet
- **Maximum 70 address span per packet** (critical!)
- Write operations (FC 5,6,15,16) are individual packets
- Read operations (FC 1,2,3,4) are grouped for efficiency

**Manual Editing (Advanced):**
- Double-click any row to edit Packet # field
- After manual edits, re-click "Calculate Packets" to update packet_sa and packet_nrt

**Note:** If you skip this step, packets are auto-calculated during generation.

### Step 3: Generate Files

1. Switch to **📊 Generation Panel** tab
2. Click **🔄 Generate All Configurations**

### Step 4: Output Files

Generated files appear in workspace:
- `Generated_Modbus_Config.json` - Modbus polling configuration (includes B4.SA, B4.NRT, B5.PN arrays)
- `Generated_ParamMap_Config.json` - Parameter mapping
- `Generated_Register_Config.json` - Complete register backup with packet metadata

### Step 5: Deploy to Firmware

Copy generated files to ESP32 firmware `/data` folder:
```
Thermelgy-Gateway-BMIoT/data/
  ├── Modbus_Config.json
  ├── ParamMap_Config.json
  └── Register_Config.json
```

---

## 🎨 Understanding the Table

### Column Reference

| Column | Description | Example |
|--------|-------------|---------|
| **S** | Serial number | 1, 2, 3... |
| **Slave** | Modbus slave ID | 1-247 |
| **FC** | Function code | 3, 4 |
| **Address** | Register address | 1000, 2000 |
| **Length** | Register count | 1, 2, 4 |
| **Format** | Data type | INT16, FLOAT |
| **Multi** | Multiplier | 1, 0.1, 10 |
| **Access** | Read/Write | RO, RW |
| **Cloud** | Cloud output | Yes, No |
| **Group** | JSON group name | Equipment, Settings |
| **Unit** | JSON unit name | Chiller-1, VFD-2 |
| **Key** | JSON key name | Temp, Pressure |
| **Array** | Equipment group | Chiller, VFD, Pump |
| **Packet #** | Packet number (auto-calculated) | 1, 2, 3... |
| **Packet Start** | Modbus start address for packet | 0, 100, 1561 |
| **Packet Regs** | Number of addresses to read | 6, 1, 8 |

---

## 🔥 Phase 1 Smart Features

### Auto-Configuration

When you set certain fields, the tool automatically configures related settings:

1. **Cloud Output = "Yes"** → Automatically sets:
   - ✅ Lua Buffer = "Yes"
   - ✅ Lua Category = "Equipment"

2. **Access = "Write"** → Automatically sets:
   - ✅ Lua Buffer = "Yes"
   - ✅ Lua Category = "User Variable"

### What This Means

- **Equipment** → Control logic parameters (P2.MPI - Equipment)
- **User Variable** → User-settable values (P2.RPCI - Remote Param)

You can override these in Advanced Options if needed.

---

## 🛡️ Manual Override Mode (NEW in v6.7)

### What is Manual Override?

Manual Override allows you to **manually control** which ParamMap arrays (P2.MPI, P2.RPCI, P3.MPI, P3.LBI) a parameter belongs to, **preventing automatic recalculation** during Generate.

### When to Use Manual Override

✅ **Migrating Legacy Configurations** - Preserve existing array memberships  
✅ **Custom Firmware Modifications** - Support non-standard arrays  
✅ **Testing/Debugging** - Temporarily exclude parameters from auto-generation  
✅ **Partial Automation** - Mix automatic and manual parameter management

### How to Enable Manual Override

**When Adding a Register:**
1. Fill in basic fields (Slave, FC, Address, etc.)
2. Scroll down to **🛡️ Manual Override** section
3. Check ☑️ **"Enable Manual Override"**
4. Manually type **Array Membership** (e.g., "P2.MPI,P3.MPI")
5. Click **💾 Add Register**

**When Editing a Register:**
1. Double-click the register row
2. Scroll to **🛡️ Manual Override** section
3. Check/uncheck the override option
4. Modify Array Membership if needed
5. Click **💾 Save Changes**

### Behavior Comparison

| Mode | Array Membership | P2/P3 Generation | Lua Buffer Fields | Save/Load |
|------|-----------------|------------------|-------------------|-----------|
| **Automatic (Default)** | Auto-calculated | Parameter included in auto-arrays | Used for calculation | ✅ Preserved |
| **Manual Override** | User-controlled | Parameter SKIPPED in auto-arrays | Saved but NOT used | ✅ Preserved |

### Examples

**Example 1: Force Custom Array**
```
Manual Override: ✓ CHECKED
Array Membership: P2.CUSTOM,P3.OVERRIDE

Result: Parameter excluded from P2.MPI/P3.MPI, custom text preserved
```

**Example 2: Exclude from Generation**
```
Manual Override: ✓ CHECKED
Array Membership: (empty)

Result: Parameter not included in any ParamMap arrays
```

**Example 3: Mixed Mode**
```
Register 1: Manual Override=False, Lua Buffer=Yes → Added to P2.MPI automatically
Register 2: Manual Override=True, Array=P2.SPECIAL → Kept as P2.SPECIAL
Register 3: Manual Override=False, Cloud=Yes → Added to P3.MPI automatically

Result: Registers 1 and 3 auto-managed, Register 2 manually controlled
```

### Verification

**During Generation:**
Console shows which parameters are skipped:
```
[Manual Override] Param 7 - skipping auto-generation (user-controlled)
```

**In Exported JSON:**
```json
{
  "param_id": 7,
  "array_membership": "P2.CUSTOM",
  "manual_override": true
}
```

### Important Notes

⚠️ **No Validation** - Manual array names are not validated. Make sure they match your firmware expectations.

⚠️ **Lua Buffer Fields Still Saved** - Even with Manual Override, Lua Buffer fields (in_lua_buffer, lua_category) are saved for documentation purposes.

💡 **Console Logging** - Watch the console during Generate to see which parameters are manually overridden.

📚 **Detailed Guide** - See [`MANUAL_OVERRIDE_TESTING_GUIDE.md`](MANUAL_OVERRIDE_TESTING_GUIDE.md) for comprehensive testing scenarios.

---

## 🛠️ Common Tasks

### Creating Temperature Reading

```
Slave ID: 1
Function Code: 3
Address: 1000
Length: 1
Format: 8 - INT16
Multiplier: 0.1
Access: Read Only
Cloud Output: Yes
JSON Group: Equipment
JSON Unit: Chiller-1
JSON Key: Temperature
Array: Chiller
```

### Creating Setpoint (Read/Write)

```
Slave ID: 1
Function Code: 3
Address: 2000
Length: 1
Format: 8 - INT16
Multiplier: 0.1
Access: Write
Cloud Output: No
JSON Group: Settings
JSON Unit: Chiller-1
JSON Key: TempSetpoint
```

---

## ⚠️ Important Notes

### Data Validation

- ✅ Required fields are validated automatically
- ⚠️ Invalid entries show error messages
- 💡 Hover over column headers for help

### File Compatibility

- ✅ Import old Register_Config.json files
- ✅ Export with all new features preserved
- ✅ Backward compatible with firmware v3.x+

### Save Your Work

- 💾 Always export before closing
- 📝 Keep backup copies
- 🔄 Use version control for configuration files

---

## ❓ Troubleshooting

### Issue: Import fails with error

**Solution:**
- Check JSON file is valid
- Ensure required fields exist
- Try opening file in text editor to verify format

### Issue: Generate produces errors

**Solution:**
- Verify all registers have required fields
- Check for duplicate addresses
- Ensure multiplier values are valid numbers

### Issue: Application won't start

**Solution:**
- Check Python 3.8+ is installed
- Verify dependencies: `pip install -r requirements.txt`
- Run from command line to see error messages

---

## 📞 Getting Help

- **Documentation:** See `DEPLOYMENT_GUIDE.md` for detailed setup
- **Quick Reference:** See `QUICK_START_ENHANCED.md`
- **Support:** Contact firmware team

---

## 📝 Glossary

| Term | Definition |
|------|------------|
| **Slave ID** | Modbus device address on RS485 bus |
| **Function Code** | Modbus command (3=Holding, 4=Input) |
| **Register Address** | Memory location in Modbus device |
| **Multiplier** | Scaling factor (value × multiplier = actual) |
| **Cloud Output** | Send this parameter to MQTT/cloud |
| **Lua Buffer** | Store in Lua control logic memory |
| **Array Membership** | Equipment group for JSON structure |
| **B5 ID** | Firmware Block 5 index (auto-generated) |
| **Packet #** | Packet grouping (1-indexed, auto-calculated) |
| **Packet Start (SA)** | Starting Modbus address for packet read |
| **Packet Regs (NRT)** | Number of registers/addresses to read |
| **Address Span** | Max address - Min address in packet (≤70 limit) |

---

**Last Updated:** February 9, 2026  
**Application Version:** v6.6+

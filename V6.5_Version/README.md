# 🔧 Modbus Register Configuration Tool v6.7

**Version:** 6.7+  
**Release Date:** February 9, 2026  
**Python Required:** 3.8+  
**Dependencies:** None (Python standard library only)

---

## 📖 Overview

A **graphical configuration tool** for managing Modbus register definitions and generating firmware-compatible JSON files for the **Thermelgy BMIoT Gen2 Gateway**.

### ✨ Key Features

- ✅ **Manual Override Mode** - NEW v6.7: Manually control P2/P3 array membership
- ✅ **Lua Buffer Save/Load Fix** - NEW v6.7: All Lua fields properly preserved
- ✅ **Enhanced Packet Calculation** - Automatic packet assignment with address span validation
- ✅ **GUI-based register configuration** - No command-line required
- ✅ **Zero external dependencies** - Pure Python standard library
- ✅ **Smart Auto-Configuration** - Intelligent defaults based on field values
- ✅ **Import/Export** - Full round-trip compatibility with firmware JSONs
- ✅ **Transparent packet configuration** - Write/feedback pairing support
- ✅ **Lua Buffer integration** - Automatic P2/P3 array generation
- ✅ **Equipment grouping** - JKY/JKA array management
- ✅ **38 configuration fields** - Complete control over firmware behavior

---

## 🚀 Quick Start

### Windows Users

```batch
# Double-click to start:
Start_Application.bat
```

### Linux/Mac Users

```bash
python3 modbus_tkinter_app_v6.6_complete.py  # v6.7+ with Manual Override
```

---

## 📂 Directory Structure

```
V6.5_Version/
├── 📄 modbus_tkinter_app_v6.6_complete.py  ⭐ MAIN APPLICATION (5965 lines)
├── 🔧 forward_engine.py                    Forward transformation
├── 🔧 reverse_engine.py                    Reverse transformation
├── 🔧 transform_wrapper.py                 Unified API wrapper
├── 🔧 bmiot_constants.py                   Constants and mappings
├── 🔧 json_formatter.py                    JSON pretty-printing
├── 🔧 ui_helpers.py                        UI utilities
├── 🚀 Start_Application.bat                Windows launcher
├── 📋 requirements.txt                     Python dependencies (none!)
│
├── 📘 Documentation/
│   ├── USER_GUIDE.md                       ⭐ End user manual
│   ├── APPLICATION_ENGINEER_GUIDE.md       ⭐ System integration guide
│   ├── DEVELOPER_GUIDE.md                  ⭐ Developer documentation
│   ├── FORWARD_LOGIC_VISUAL_GUIDE.md       ⭐ Visual logic explanation
│   ├── DEPLOYMENT_GUIDE.md                 Installation instructions
│   ├── QUICK_START_ENHANCED.md             Quick reference card
│   └── CHANGELOG_v6.6.md                   Version history
│
├── 📦 Examples/
│   ├── Test_Phase1_Register_Config.json           Sample register config
│   ├── Test_Phase1_Generated_ParamMap_Config.json Sample output
│   └── README_EXAMPLES.md                         Example descriptions
│
├── 🧪 Tests/
│   ├── test_phase1_autoconfig.py           Phase 1 logic tests
│   └── README_TESTS.md                     Testing documentation
│
└── 📄 README.md                            ⭐ This file
```

---

## 📚 Documentation Guide

### 👤 For End Users
**Start here:** [`USER_GUIDE.md`](USER_GUIDE.md)
- How to add/edit/delete registers
- Import/export configurations
- Generate firmware files
- Common tasks and troubleshooting

### 🔧 For Application Engineers
**Start here:** [`APPLICATION_ENGINEER_GUIDE.md`](APPLICATION_ENGINEER_GUIDE.md)
- Architecture and configuration flow
- Firmware integration details
- Transparent packet configuration
- Equipment grouping (JKY/JKA)
- Testing and validation procedures

**Visual learners:** [`FORWARD_LOGIC_VISUAL_GUIDE.md`](FORWARD_LOGIC_VISUAL_GUIDE.md)
- Step-by-step visual diagrams
- Flowcharts and decision trees
- Complete transformation examples
- ASCII diagrams of data flow

### 💻 For Developers
**Start here:** [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md)
- Code architecture and module structure
- UI implementation details
- Adding new features
- Testing framework
- Contributing guidelines

### ⚡ Quick Reference
**Start here:** [`QUICK_START_ENHANCED.md`](QUICK_START_ENHANCED.md)
- One-page cheat sheet
- Common commands
- Field reference table

---

## 🎯 What's New in v6.7

### 🛡️ Manual Override Mode (February 9, 2026)

**NEW FEATURE: Per-Register Manual Control**
```
Enable Manual Override → Manually set Array Membership → Skip auto-generation
```

**Key Benefits:**
- ✅ **Preserve custom array memberships** - Your manual values stay exactly as typed
- ✅ **Skip P2/P3 auto-calculation** - Parameters with override won't be recalculated
- ✅ **Mixed mode support** - Some parameters automatic, some manual
- ✅ **Perfect for migrations** - Preserve legacy configurations

**How to Use:**
1. Add/Edit a register
2. Scroll to "🛡️ Manual Override" section
3. Check ☑️ "Enable Manual Override"
4. Manually type Array Membership (e.g., "P2.MPI,P3.CUSTOM")
5. Your value is preserved - won't be overwritten during Generate

**Console Logging:**
```
[Manual Override] Param 7 - skipping auto-generation (user-controlled)
```

**Detailed Guide:** See [`MANUAL_OVERRIDE_TESTING_GUIDE.md`](MANUAL_OVERRIDE_TESTING_GUIDE.md)

### 🐛 Critical Bug Fixes (February 9, 2026)

**Fix 1: Lua Buffer Fields Now Properly Saved**
- ✅ Add Register now creates RegisterEntry objects
- ✅ Export fallback condition fixed (>= 38 columns)
- ✅ Edit Register updates RegisterEntry objects
- ✅ All Lua fields preserved through save/load cycles

**Fix 2: Export Column Mapping Corrected**
- ✅ Fixed column indices for Lua Buffer fields
- ✅ manual_override field added to export/import
- ✅ 38 total columns (0-37) now fully functional

**Verification:**
```bash
python test_save_load_fix.py your_exported_file.json
# Should show: "✅ SUCCESS: All registers have Lua Buffer fields!"
```

### Enhanced Packet Calculation (v6.6)

**"Calculate Packets" Button:**
```
Click 🔄 Calculate Packets → Preview packet groupings → Validate constraints
```

**Automatic Calculation:**
- ✅ Groups by Slave ID + Function Code
- ✅ Enforces 70 register limit per packet
- ✅ **Enforces 70 address span limit** (critical firmware constraint)
- ✅ Calculates packet_sa (start address) and packet_nrt (register count)
- ✅ Shows actual Modbus commands in preview (e.g., "FC3(address=32, count=11)")

### Smart Auto-Configuration (v6.6)

**Rule 1: Cloud Output = "Yes"**
```
Automatically sets:
✓ In Lua Buffer = "Yes"
✓ Lua Category = "Equipment"
✓ Added to P2.MPI (Equipment parameters)
✓ Added to P3.MPI (Cloud output)
```

**Rule 2: Access = "Write"**
```
Automatically sets:
✓ In Lua Buffer = "Yes"
✓ Lua Category = "User Variable"
✓ Added to P2.RPCI (Remote parameter control)
```

### Enhanced UI (v6.6)
- ✅ Scrollable Add/Edit dialogs (600x750)
- ✅ Manual Override section (v6.7)
- ✅ Fixed mousewheel binding issues
- ✅ Symmetrical column headers
- ✅ 38 configuration fields (27 visible + 11 hidden metadata)

### Improved Import (v6.6)
- ✅ Handles legacy field names (register_address, function_code)
- ✅ Empty string safety (converts to 0)
- ✅ Format string conversion ("INT16" → 8)
- ✅ manual_override field support (v6.7)

---

## 🔄 Workflow

### 1. Configure Registers
```
Add Register → Fill 8 Essential Fields → (Optional) Advanced Options → Save
```

### 2. Generate Files
```
Generation Panel → Generate All Configurations
```

### 3. Deploy to Firmware
```
Copy Generated_*.json files to ESP32 /data folder
```

### 4. Upload to Device
```
PlatformIO: pio run -t uploadfs
```

---

## 📊 Configuration Files

### Input Files

| File | Purpose | Source |
|------|---------|--------|
| `Register_Config.json` | Master register definitions | User-created or imported |

### Output Files (Generated)

| File | Purpose | Target Firmware Module |
|------|---------|------------------------|
| `Generated_Modbus_Config.json` | Polling schedule, B4/B5/B6 blocks | Modbus task |
| `Generated_ParamMap_Config.json` | P2/P3/JKY/JKA arrays | ParamMap module |
| `Generated_Register_Config.json` | Backup of complete config | Configuration tool |

---

## 🎨 GUI Overview

### Register Configuration Tab

```
┌─────────────────────────────────────────────────────────────┐
│ ➕ Add  ✏️ Edit  🗑️ Delete  🧹 Clear  📥 Import  💾 Export   │
├─────────────────────────────────────────────────────────────│
│ S │Slave│FC│Addr │Len│Format│Multi│Access│Cloud│Group│...   │
│ 1 │  1  │ 3│1000 │ 1 │INT16 │ 0.1 │ RO   │ Yes │Equip│...   │
│ 2 │  1  │ 3│2000 │ 1 │INT16 │ 1.0 │ Write│ No  │Sett │...   │
│ 3 │  2  │ 4│3000 │ 2 │FLOAT │ 1.0 │ RO   │ Yes │Equip│...   │
└─────────────────────────────────────────────────────────────┘
📊 Total Registers: 3
```

### Generation Panel Tab

```
┌─────────────────────────────────────────┐
│  🔄 Generate All Configurations         │
├─────────────────────────────────────────┤
│  Output Preview:                        │
│  ✓ Generated_Modbus_Config.json        │
│  ✓ Generated_ParamMap_Config.json      │
│  ✓ Generated_Register_Config.json      │
└─────────────────────────────────────────┘
```

---

## ⚙️ Installation

### Prerequisites

- **Python 3.8 or higher**
- **No external libraries required!**

### Setup (Optional Virtual Environment)

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# No packages to install - uses built-in libraries only!
```

### Verify Installation

```bash
python modbus_tkinter_app_v6.6_complete.py
```

---

## 🧪 Testing

### Run Automated Tests

```bash
# Run Phase 1 auto-config tests
python Tests/test_phase1_autoconfig.py

# Run all tests (if pytest installed)
pytest Tests/ -v
```

### Load Sample Configuration

1. Click **📋 Load Sample** in application
2. Or manually: **📥 Import** → Select `Examples/Test_Phase1_Register_Config.json`

---

## 🐛 Troubleshooting

### Application Won't Start

**Issue:** `ModuleNotFoundError: No module named 'tkinter'`

**Solution (Ubuntu/Debian):**
```bash
sudo apt-get install python3-tk
```

**Solution (Fedora/RedHat):**
```bash
sudo dnf install python3-tkinter
```

### Import Fails

**Issue:** "Invalid JSON file" error

**Solution:**
- Verify JSON syntax with online validator
- Check required fields exist (slave_id, address, etc.)
- See [`USER_GUIDE.md`](USER_GUIDE.md) Section "Troubleshooting"

### Generated Files Have Errors

**Issue:** P2/P3 arrays missing expected parameters

**Solution:**
- Verify Phase 1 auto-config (Cloud Output, Access Type)
- Check "In Lua Buffer" and "Lua Category" fields
- See [`APPLICATION_ENGINEER_GUIDE.md`](APPLICATION_ENGINEER_GUIDE.md) Section "Advanced Configuration"

---

## 📋 Essential Fields Reference

| Field # | Name | Description | Example |
|---------|------|-------------|---------|
| 1 | Slave ID | Modbus device ID (1-247) | 1 |
| 2 | Function Code | 3=Holding, 4=Input | 3 |
| 3 | Address | Register address | 1000 |
| 4 | Length | Register count | 1 |
| 5 | Format | Data type | 8 (INT16) |
| 6 | Multiplier | Scale factor | 0.1 |
| 7 | Access | Read Only / Write | Read Only |
| 8 | Cloud Output | Send to cloud? | Yes |

---

## 🔗 Related Resources

### Main Project Documentation
- **Main README:** [`../README.md`](../README.md)
- **Firmware Repository:** https://github.com/Thermelgy-Repo/Firmware-Repo  
- **API Documentation:** [`../API Documentation/html/index.html`](../API%20Documentation/html/index.html)

### External Links
- **Main Documentation:** https://thermelgy-firmware.atlassian.net/wiki/x/RIA1
- **Error Codes:** https://thermelgy-firmware.atlassian.net/wiki/x/AgA0B

---

## 📞 Support

### Getting Help

1. **User Issues:** See [`USER_GUIDE.md`](USER_GUIDE.md) Troubleshooting section
2. **Integration Issues:** See [`APPLICATION_ENGINEER_GUIDE.md`](APPLICATION_ENGINEER_GUIDE.md)
3. **Development Questions:** See [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md)
4. **Bug Reports:** Contact firmware team

---

## 🔐 License

Copyright © 2026 Thermelgy  
Internal use only - Not for distribution

---

## 📝 Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| **6.6** | Feb 2026 | Phase 1 auto-config, improved UI, column symmetry |
| 6.5 | Jan 2026 | Lua Buffer integration, transparent packets |
| 6.0 | Dec 2025 | Initial GUI release |

---

## 🎓 Learning Path

### New to the Tool?
1. Read [`USER_GUIDE.md`](USER_GUIDE.md)
2. Load sample: `Examples/Test_Phase1_Register_Config.json`
3. Try adding/editing registers
4. Generate files and inspect output

### Deploying to Production?
1. Read [`APPLICATION_ENGINEER_GUIDE.md`](APPLICATION_ENGINEER_GUIDE.md)
2. Understand firmware blocks (B4, B5, B6, P2, P3)
3. Configure transparent packets and pairing
4. Test with Modbus simulator

### Contributing Code?
1. Read [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md)
2. Understand module architecture
3. Run existing tests
4. Follow coding guidelines

---

**🚀 Ready to start? Run `Start_Application.bat` (Windows) or `python modbus_tkinter_app_v6.6_complete.py`**

**Last Updated:** February 9, 2026  
**Maintainer:** Thermelgy Firmware Team

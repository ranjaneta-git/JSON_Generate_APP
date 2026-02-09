# Deployment Guide - v6.7+

## 📦 How to Share This Application

### Full Package (Recommended)
**When to use**: Share with team members who need all features

**What to include** (all files in V6.5_Version folder):
1. ✅ `modbus_tkinter_app_v6.7_complete.py` (Main application)
2. ✅ `reverse_engine.py` (Import engine)
3. ✅ `forward_engine.py` (Export engine)
4. ✅ `transform_wrapper.py` (Coordinator)
5. ✅ `json_formatter.py` (Compact JSON formatter)
6. ✅ `ui_helpers.py` (Tooltip system)
7. ✅ `bmiot_constants.py` (Validation rules)
8. ✅ `Start_Application.bat` (Windows launcher)
9. ✅ `README.md` (User guide)
10. ✅ `QUICK_START_ENHANCED.md` (Detailed guide)
11. ✅ `DEPLOYMENT_GUIDE.md` (This file)

**How to package**:
```bash
# Create a zip file with entire V6.5_Version folder
# Total size: ~350KB (all files included)
```

**Result**: Full functionality
- ✅ All import/export features (with Lua Buffer fix)
- ✅ Manual Override mode for P2/P3 control
- ✅ Enhanced packet calculation
- ✅ Configuration validation
- ✅ Compact JSON formatting
- ✅ Metadata preservation
- ✅ Interactive tooltips

---

## 🔍 What Recipients Will See

### Full Package Install
```
✅ JSON formatter loaded (embedded)
✅ Transformation engines loaded successfully
✅ bmiot_constants loaded successfully
```

**All features work perfectly!**
✅ Transformation engines loaded successfully
✅ bmiot_constants loaded successfully

[Application opens normally]
```

### Standalone Install
```
✅ JSON formatter loaded (embedded)
⚠️ Warning: Transformation engines not available: No module named 'transform_wrapper'
   Import/Export features will be limited
⚠️ Warning: Could not import bmiot_constants
   Using fallback constants

[Application opens with basic features]
```

**Important**: Warnings are NORMAL for standalone mode. Application still works!

---

## 📋 Deployment Checklist

### Before Sharing
- [ ] Test application launch (`python modbus_tkinter_app_v6.7_complete.py`)
- [ ] Verify all checkmarks in console output
- [ ] Test import workflow (if sharing full package)
- [ ] Test validation button
- [ ] Zip entire V6.5_Version folder
- [ ] Include all documentation files

### Recipient Requirements
- [ ] Python 3.7+ installed (`python --version`)
- [ ] tkinter available (usually included with Python)
- [ ] Basic understanding of Modbus registers
- [ ] Access to firmware JSON files (if importing)

---

## 🛠️ Troubleshooting for Recipients

### Issue 1: "No module named 'tkinter'"
**Solution**: Install tkinter
```bash
# Windows
pip install tk

# Linux  
sudo apt-get install python3-tk

# Mac
brew install python-tk
```

### Issue 2: Warnings about missing modules
**Check which files are missing**:
```
⚠️ Warning: Transformation engines not available
```
**Solution**: Copy all files from V6.5_Version folder

### Issue 3: Application won't start
**Diagnostic steps**:
```bash
# 1. Check Python version (need 3.7+)
python --version

# 2. Try running with full output
python modbus_tkinter_app_v6.7_complete.py

# 3. Check if tkinter works
python -c "import tkinter; print('OK')"
```

### Issue 4: Lua Buffer fields missing in exported JSON
**Solution**: Fixed in v6.7 - update from v6.6

### Issue 5: Mousewheel scroll not working
**Solution**: Update to v6.6+ - this bug was fixed

### Issue 6: ParamMap doesn't match after import
**Solution**: Update to v6.6+ - metadata validation fixed

---

## 📊 What's Included

| File | Size | Purpose |
|------|------|---------|
| `modbus_tkinter_app_v6.7_complete.py` | ~220KB | Main application (v6.7+) |
| `reverse_engine.py` | ~23KB | JSON → Registers |
| `forward_engine.py` | ~22KB | Registers → JSON |
| `transform_wrapper.py` | ~3KB | Engine coordinator |
| `json_formatter.py` | ~8KB | Compact formatter |
| `ui_helpers.py` | ~4KB | Tooltip system |
| `bmiot_constants.py` | ~17KB | Validation rules |
| `Start_Application.bat` | <1KB | Windows launcher |
| `README.md` | ~15KB | Overview guide |
| `QUICK_START_ENHANCED.md` | ~18KB | Detailed guide |
| `DEPLOYMENT_GUIDE.md` | ~12KB | This file |

**Total Package Size**: ~350KB

---

## 💡 Usage Instructions for Recipients

### First Time Setup
1. **Extract the zip file**
2. **Navigate to folder**:
   ```bash
   cd V6.5_Version
   ```

3. **Launch application**:
   - **Windows**: Double-click `Start_Application.bat`
   - **Command line**: `python modbus_tkinter_app_v6.7_complete.py`

4. **Verify startup**:
   ```
   ✅ JSON formatter loaded (embedded)
   ✅ Transformation engines loaded successfully
   ✅ bmiot_constants loaded successfully
   ```

### Daily Usage
- **Double-click** `Start_Application.bat` to launch
- **Import** firmware JSONs with "📥 Import Modbus+Paramap JSON"
- **Calculate** packets with "🔄 Calculate Packets" (optional)
- **Validate** config with "🔍 Validate Configuration"
- **Generate** JSONs with "⚡ Generate Configurations"
- **Save** with "💾 Save All Files"

---

## 🎯 Version Information

**Version**: v6.7+  
**Date**: February 9, 2026  
**Status**: Production Ready  

**Latest Features & Fixes (v6.7)**:
- ✅ Manual Override mode for per-register P2/P3 control
- ✅ Fixed 3 critical Lua Buffer save/load bugs
- ✅ Full field preservation in export/import (38 columns)
- ✅ Enhanced testing with verification scripts

**Previous Improvements (v6.6)**:
- ✅ Enhanced Packet Calculation with address span validation
- ✅ Simplified Add Register Dialog
- ✅ Configuration Validator
- ✅ Fixed metadata preservation (B1.NOP)
- ✅ Fixed mousewheel scrolling
- ✅ Fixed list index errors

**Upgrade from v6.6**:
Replace all files with v6.7 versions. Manual Override defaults to OFF, so existing configs work unchanged.

### For External Users (Demo/Basic Use)
```bash
# Send just:
modbus_tkinter_app_v6.7_complete.py

# Name: BMIoT_Config_Generator_v6.7_Standalone.py
# Size: ~220KB
```

### For Production Deployment
```bash
# Zip entire V6.5_Version folder
# Includes all files + tests + documentation
# Name: BMIoT_Config_Generator_v6.7_Complete.zip
# Size: ~380KB (includes Manual Override docs)
```

---

## 📧 Email Template for Recipients

**Subject**: BMIoT Configuration Generator v6.7+

**Body**:
```
Hi [Name],

Attached is the BMIoT Configuration Generator tool (v6.7 with Manual Override).

QUICK START:
1. Unzip the attached file
2. Open terminal/command prompt
3. Navigate to the folder
4. Run: python modbus_tkinter_app_v6.7_complete.py

REQUIREMENTS:
- Python 3.7 or higher
- No additional packages needed!

WHAT YOU'LL SEE:
- Application window opens
- Some warnings are normal (app still works)
- Full GUI with all features

HELP:
- Read README.md for detailed guide
- Hover over fields for tooltips
- Check console for status messages

Let me know if you have any issues!
```

---

## 🔄 Version Control

### When Updating
1. Increment version in header comments
2. Update README.md changelog
3. Test standalone mode
4. Test full package mode
5. Create new deployment zip
6. Send to 1-2 people for testing
7. Then distribute widely

### Naming Convention
```
BMIoT_Config_Generator_v6.6_YYYYMMDD_Full.zip        # Full package
BMIoT_Config_Generator_v6.6_YYYYMMDD_Standalone.py  # Single file
BMIoT_Config_Generator_v6.6_YYYYMMDD_Complete.zip   # Everything
```

---

## ✅ Final Checklist

Before sending to anyone:

**Testing**:
- [ ] Runs standalone (just .py file)
- [ ] Runs with full package
- [ ] No import errors on fresh Python install
- [ ] JSON formatting works
- [ ] CSV export works
- [ ] GUI displays correctly

**Documentation**:
- [ ] README.md updated
- [ ] Version number correct
- [ ] Date updated
- [ ] Deployment guide included

**Clean Package**:
- [ ] No test files
- [ ] No backup files (.backup, .old)
- [ ] No __pycache__ folders
- [ ] No temporary JSON files

**Ready to Deploy!** 🚀

---

**Last Updated**: February 9, 2026  
**Version**: v6.6 Enhanced  
**Deployment**: Production Ready

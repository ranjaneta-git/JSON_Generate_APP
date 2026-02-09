# Modbus Configuration Generator v6.6

**Production-Ready Bidirectional Transformation Tool**

## 🚀 Quick Start

### Full Install (Recommended):
```bash
# Copy entire V6.5_Version folder
cd V6.5_Version
python modbus_tkinter_app_v6.6_complete.py
```

Or double-click: **Start_Application.bat**

**Console should show:**
```
✅ JSON formatter loaded (embedded)
✅ Transformation engines loaded successfully
✅ bmiot_constants loaded successfully
```

### Required Files:
1. **modbus_tkinter_app_v6.6_complete.py** (Main application)
2. **reverse_engine.py** (Import from firmware JSON)
3. **forward_engine.py** (Export to firmware JSON)
4. **transform_wrapper.py** (Engine coordinator)
5. **bmiot_constants.py** (Validation constants)
6. **ui_helpers.py** (UI helper functions)

### Python Requirements:
- Python 3.7+
- tkinter (usually included with Python)
- No additional packages needed!

## ✨ Key Features

### Core Functionality
✅ **Bidirectional Transformation**: Import Modbus+Paramap JSON ⟷ Register Table  
✅ **Simplified Add Register Dialog**: Collapsible sections (8 essential + advanced + preview)  
✅ **Smart Validation**: Non-blocking warnings with detailed reports  
✅ **Compact JSON Output**: 50% smaller files, firmware-compatible format  
✅ **Equipment Hierarchy**: Automatic equipment grouping and classification  
✅ **Perfect Round-Trip**: Lossless metadata preservation (metadata-first mode)  
✅ **Multiple Export Formats**: JSON (compact), JSON (standard), CSV  

### Latest Improvements (v6.6)
🎨 **Simplified Dialog**: 68% complexity reduction with collapsible sections  
💡 **Interactive Tooltips**: Hover help for all fields  
📊 **Configuration Validator**: Detailed validation reports before generation  
⚡ **Fixed Metadata Handling**: Correct parameter count validation (B1.NOP)  
🐛 **UI Fixes**: Arrow display, mousewheel scrolling preserved  

## 📁 Project Structure

### Core Application Files
```
V6.5_Version/
├── modbus_tkinter_app_v6.6_complete.py  # Main GUI application (5077 lines)
├── reverse_engine.py                     # JSON → Registers import
├── forward_engine.py                     # Registers → JSON export
├── transform_wrapper.py                  # Engine coordinator
├── json_formatter.py                     # Compact JSON formatter
├── ui_helpers.py                         # UI tooltip system
├── bmiot_constants.py                    # Validation constants
└── Start_Application.bat                 # Windows launcher
```

### Documentation
```
├── README.md                            # This file - overview
├── QUICK_START_ENHANCED.md              # User guide with examples
└── DEPLOYMENT_GUIDE.md                  # Sharing instructions
```

## 🎯 Key Capabilities

### 1. Bidirectional Workflow

**Forward**: Register Entry → JSON
```
Enter registers → Generate → Get compact JSON files
```

**Reverse**: JSON → Register Entry  
```
Import firmware JSONs → Edit in table → Regenerate
```

### 2. Smart JSON Formatting

**Before (Standard)**:
```json
"LBI": [
  1,
  2,
  3,
  ...
]
```
365 lines, 4271 characters

**After (Compact)**:
```json
"LBI": [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  11, 12, 13, 14, 15, 16, 17, 18, 19, 20
]
```
51 lines, 2115 characters (50% reduction!)

### 3. Interactive Tooltips

Hover over any field to see helpful descriptions:
- **Baudrate**: "Communication speed in bits per second. Common: 9600, 19200, 38400, 115200"
- **Function Code**: "1=Read Coils, 3=Read Holding, 6=Write Register, 16=Write Multiple"
- **Format**: "1=UINT16, 2=INT16, 3=UINT32, 4=INT32, 5=FLOAT32, 6=STRING, 7=BIT, 8=ARRAY"

## 📋 Register Fields Reference

| Field | Description | Valid Values | Example |
|-------|-------------|--------------|---------|
| **Param ID** | Parameter identifier | 1-9999 | 1001 |
| **Slave ID** | Modbus device address | 1-247 | 1 |
| **FC** | Function code | 1,2,3,4,5,6,15,16 | 3 |
| **Address** | Register address | 0-65535 | 1000 |
| **Length** | Register count | 1-125 | 2 |
| **FMT** | Data format code | 1-8 | 5 (FLOAT32) |
| **Multiplier** | Scaling factor | Any float | 0.1 |
| **Access** | Read/Write type | RO, RW, WO | RW |
| **Cloud** | Send to cloud | Yes, No | Yes |
| **JSON Group** | Equipment group | String | AHU_RL |
| **JSON Unit** | Measurement unit | String | Temp |
| **JSON Key** | Cloud parameter name | String | Ch1_ChW_T |
| **Array Membership** | Multi-value group | String | CH1_AIE1 |

## 🔄 Common Workflows

### Workflow 1: Generate New Configuration

1. **Launch Application**
   ```bash
   python modbus_tkinter_app_v6.6_complete.py
   ```
   Or double-click **Start_Application.bat**

2. **Configure Communication**
   - Set baudrate (default: 19200)
   - Set data format (default: 8-E-1)
   - Set profile (default: RTU)

3. **Add Registers**
   - Click "➕ Add Register"
   - Fill 8 essential fields (hover for tooltips!)
   - Expand Advanced Options if needed
   - Expand Preview & Details to verify
   - Repeat for all parameters

4. **Validate Configuration** (Optional)
   - Click "🔍 Validate Configuration"
   - Review detailed validation report
   - Warnings won't block generation

5. **Generate & Save**
   - Click "⚡ Generate Configurations"
   - View compact JSON in tabs
   - Click "💾 Save All Files"

### Workflow 2: Import & Edit Existing Configuration

1. **Import Firmware Files**
   - Click "📥 Import Modbus+Paramap JSON"
   - Select `modbus_io.json`
   - Select `parameter_config.json`
   - Registers auto-populate!

2. **Edit Parameters**
   - Select row, click "✏️ Edit Register"
   - Modify fields as needed
   - Changes tracked automatically

3. **Regenerate with Metadata Preservation**
   - Click "⚡ Generate Configurations"
   - Console shows: "[ParamMap Generation] Mode: METADATA-FIRST..."
   - JSON automatically formatted (compact arrays)
   - Structure preserved exactly from import
   - Save updated files

### Workflow 3: Export for Documentation

1. **Export Options**
   - Click "📤 Export to CSV/JSON"
   - Choose format:
     - **CSV**: For Excel editing
     - **JSON (Compact)**: 50% smaller, readable
     - **JSON (Standard)**: Traditional format

2. **Use Cases**
   - CSV: Share with non-technical team
   - Compact JSON: Firmware deployment
   - Standard JSON: Legacy compatibility

## 🧪 Validation & Quality

### Built-in Configuration Validator
Click "🔍 Validate Configuration" to check:
- ✅ Duplicate parameters
- ✅ Overlapping registers  
- ✅ Address range conflicts
- ✅ Invalid field values
- ✅ Missing required fields
- ✅ Equipment group consistency

Warnings are non-blocking - you can still generate with warnings present.

### Metadata Preservation
The tool automatically detects imported configurations and preserves their exact structure:
- **METADATA-FIRST Mode**: Preserves imported JSON structure exactly
- **CALCULATE-FRESH Mode**: Calculates structure from scratch for manual entries

Console will show: `[ParamMap Generation] Mode: METADATA-FIRST...` when preserving structure.

## 📚 Documentation

### For Users
1. **README.md** (this file) - Overview and quick start
2. **QUICK_START_ENHANCED.md** - Detailed user guide with examples
3. **DEPLOYMENT_GUIDE.md** - How to share the application

### For Developers
- Code is well-commented with inline documentation
- All functions have docstrings
- Type hints where applicable
- See source files for implementation details

## 🔧 Troubleshooting

### Issue: Engines Not Loading
**Symptom**: Console shows "⚠️ Transformation engines not available"  
**Solution**: Ensure these files are in same directory:
- `reverse_engine.py`
- `forward_engine.py`  
- `transform_wrapper.py`
**Impact**: Import/Export features won't work, but manual entry still functions

### Issue: Tooltips Not Showing
**Symptom**: No hover descriptions appear  
**Solution**: 
1. Check `ui_helpers.py` exists in same directory
2. Hover for 500ms (default delay)
3. Check console for import errors

### Issue: Mousewheel Scroll Not Working
**Symptom**: Can't scroll main window after closing Add Register dialog  
**Solution**: This was fixed in v6.6 - update to latest version

### Issue: List Index Out of Range
**Symptom**: Error when generating after import then delete  
**Solution**: This was fixed in v6.6 - metadata now cleared properly on delete

### Issue: ParamMap Doesn't Match Import
**Symptom**: Generated ParamMap has different P2.MPI count than original  
**Solution**: This was fixed in v6.6 - now uses B1.NOP for correct validation
3. Files must match firmware structure

### Issue: Generation Failed
**Symptom**: "Generate Configurations" fails  
**Solution**:
1. Check all required fields filled
2. Validate data types (addresses = integers, etc.)
3. Ensure at least one register with Cloud=Yes for JKY

## 🎓 Best Practices

### DO:
✅ Use tooltips to understand fields  
✅ Save frequently (Ctrl+S not implemented, click save button)  
✅ Test round-trip (import → export → import)  
✅ Validate with verify_implementation.py  
✅ Review generated JSON before deployment  

### DON'T:
❌ Edit JSON files manually (use GUI)  
❌ Mix data formats in same parameter  
❌ Skip communication settings  
❌ Forget to set Cloud=Yes for telemetry params  
❌ Use invalid slave IDs (1-247 only)  

## 📈 Version History

### v6.6 Enhanced (February 5, 2026) - Current
- ✅ Compact JSON formatting (50% file size reduction)
- ✅ Interactive tooltip system
- ✅ Visual status indicators
- ✅ Enhanced user experience
- ✅ Firmware-compatible output format

### v6.5 (February 4, 2026)
- ✅ Bidirectional transformation (import/export)
## 📖 Version History

### v6.6 (Current - February 2026)
- ✅ Simplified Add Register Dialog (8 essential + collapsible sections)
- ✅ Configuration Validator with detailed reports
- ✅ Fixed metadata validation (B1.NOP for parameter count)
- ✅ Fixed mousewheel scroll after dialog close
- ✅ Fixed list index errors on delete + regenerate
- ✅ Compact JSON formatting (50% smaller files)
- ✅ Interactive tooltips system
- ✅ Perfect metadata preservation on import

### v6.5 (January 2026)
- ✅ Bidirectional transformation complete
- ✅ Equipment hierarchy support
- ✅ Round-trip preservation
- ✅ Comprehensive validation

## 🤝 Support

### Getting Help
1. Check tooltips in application (hover over fields)
2. Read QUICK_START_ENHANCED.md for detailed examples
3. Check console for error messages and mode indicators
4. Verify all required files are present

### Reporting Issues
Include:
- Console output (error messages, mode indicators)
- Sample data (anonymize if sensitive)
- Steps to reproduce
- Expected vs actual behavior

## ✅ Quality Assurance

### Latest Fixes (v6.6)
- ✅ Metadata validation now uses B1.NOP (total parameter count)
- ✅ Stale metadata cleared on delete operations
- ✅ Mousewheel binding fixed (widget-specific, not global)
- ✅ Arrow display fixed with proper padding
- ✅ Non-blocking validation warnings

### Production Status
- ✅ All major bugs resolved
- ✅ Full feature implementation
- ✅ Comprehensive documentation
- ✅ Validated with real firmware data
- ✅ Tested on Windows platform

## 📞 Quick Reference

**Launch**: `python modbus_tkinter_app_v6.6_complete.py` or double-click `Start_Application.bat`  
**Validate**: Click "🔍 Validate Configuration" button  
**Generate**: Click "⚡ Generate Configurations" button  
**Import**: Click "📥 Import Modbus+Paramap JSON"  
**Status**: ✅ Production Ready (v6.6)  
**Date**: February 6, 2026  

---

**Ready to use! 🚀 Start with Quick Start section above.**

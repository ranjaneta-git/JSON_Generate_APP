# Changelog - Modbus Register Configuration Tool

## Version 6.7+ (February 9, 2026)

### 🛡️ New Features

#### Manual Override Mode
**Per-Register Array Control**
- Added `manual_override` field to RegisterEntry class (Phase 5)
- New "🛡️ Manual Override" section in Add/Edit Register dialogs
- Checkbox to enable/disable manual control
- Info panel explaining automatic vs manual behavior
- Saves manual_override flag to tree column 37 (38 total columns now)

**P2/P3 Generation Skipping**
- Registers with `manual_override=True` are SKIPPED during:
  - Lua Buffer collection (P2.MPI / P2.RPCI)
  - Cloud parameter collection (P3.MPI)
  - P3.LBI calculation (automatically excluded via filtered lists)
- Console logging shows: `[Manual Override] Param X - skipping auto-generation (user-controlled)`

**Export/Import Support**
- `manual_override` field saved to Register_Config.json
- Import loads manual_override from JSON (backwards compatible - defaults to False)
- Fallback condition updated to handle 38 columns (>= 38)

**Use Cases**
- Migrate legacy configurations with special array memberships
- Support custom firmware with non-standard arrays
- Temporarily exclude parameters from auto-generation for testing
- Mix automatic and manual parameter management

**Documentation**
- Created comprehensive testing guide: `MANUAL_OVERRIDE_TESTING_GUIDE.md`
- Updated all user-facing documentation
- 5 test scenarios with expected results

### 🐛 Critical Bug Fixes

#### Fix #1: Add Register Creates RegisterEntry Objects
**Problem:** 
- Add Register dialog only updated TreeView, not `self.registers` list
- Export couldn't find RegisterEntry objects to read Lua Buffer fields
- All transparentfields and Lua Buffer fields were MISSING in exported JSON

**Solution:**
- Added RegisterEntry object creation in Add Register dialog (lines 6063-6102)
- Populates all 31 fields including Lua Buffer and manual_override
- Appends to `self.app.registers` list for export to find

**Impact:** 
- Lua Buffer fields now properly saved to JSON
- Transparent fields (packet_num, parameter_type, etc.) now exported
- Manual Override flag preserved

#### Fix #2: Export Fallback Condition Impossible to Satisfy
**Problem:**
- Condition `len(values) > 37` required 38+ columns
- Tree only has 37 columns (0-36) in v6.6
- Tree now has 38 columns (0-37) in v6.7 with manual_override
- Fallback code path NEVER executed

**Solution:**
- Changed condition from `> 37` to `>= 38` (lines 3029-3050)
- Corrected column indices for Lua Buffer fields:
  - in_lua_buffer: column 23 (was incorrectly 24)
  - lua_category: column 24 (was 25)
  - lbi_position: column 25 (was 26)
  - lbi_data_type: column 26 (was 27)
  - lua_buffer_note: column 36 (was 37)
  - manual_override: column 37 (NEW)

**Impact:**
- Fallback now executes when RegisterEntry not in self.registers
- Correct Lua Buffer values read from tree
- Export works for both RegisterEntry and tree-only registers

#### Fix #3: Edit Register Updates RegisterEntry Objects
**Problem:**
- Edit Register dialog only updated TreeView
- Underlying RegisterEntry objects in `self.registers` not updated
- Export read stale values from RegisterEntry instead of edited tree values

**Solution:**
- Added RegisterEntry update loop in save_changes() (lines 6826-6847)
- Finds register by param_id and updates all edited fields
- Updates Lua Buffer fields and manual_override flag

**Impact:**
- Edits now properly propagated to RegisterEntry objects
- Export reflects latest edited values
- Lua Buffer changes preserved

### 📊 Schema Updates

#### Tree Structure (38 Columns Total)
**Columns 0-23: Basic Fields**
- 0: S.No (param_id)
- 1-12: Modbus fields (slave_id, fc, address, etc.)
- 13-17: Packet metadata
- 18-22: Transparent fields (visible)
- 23: In Lua Buffer (NEW position - was unclear before)

**Columns 24-27: Lua Buffer Fields**
- 24: Lua Category (Equipment / User Variable)
- 25: LBI Position  
- 26: LBI Data Type
- 27: (Reserved/spacing)

**Columns 28-37: Internal Metadata (Hidden)**
- 28-35: Parameter type, pairing, P2/P3 indices, equipment info
- 36: lua_buffer_note
- 37: manual_override (NEW IN v6.7)

#### RegisterEntry Class (31 Fields)
**Phase 1-4 Fields (30 total - v6.6)**
- Original 13 fields
- Phase 1: Parameter type classification (4 fields)
- Phase 2: Packet metadata (3 fields)
- Phase 3: Equipment hierarchy (4 fields)
- Phase 4: Lua Buffer configuration (5 fields)

**Phase 5 Field (1 field - v6.7)**
- `manual_override`: bool - Prevents auto-generation from recalculating arrays

### 🔍 Verification

#### Test Script: test_save_load_fix.py
**Purpose:** Verify Lua Buffer fields are saved/loaded correctly

**Usage:**
```bash
python test_save_load_fix.py                    # Test original buggy file
python test_save_load_fix.py your_export.json    # Test your export
```

**Expected Output:**
```
✅ SUCCESS: All registers have Lua Buffer fields!
```

#### Console Logging
**P2 Generation:**
```
[Manual Override] Param 7 - skipping auto-generation (user-controlled)
[Lua Buffer] Flexible Configuration Detected:
  - Equipment params (P2.MPI): 15
  - User Variable params (P2.RPCI): 4
  - Total Lua Buffer size (P1.NLB): 19
[P2] Calculated: 15 MPI entries (LBI 1-15), 4 RPCI entries (LBI 16-19)
```

**P3 Generation:**
```
[P3] Cloud Equipment Parameters (for P3.MPI): 10
[P3.LBI] Calculated: 2 User Variable cloud outputs at LBI positions: [18, 19]
[P3.MDI] Extended: 12 total MDI entries (10 from P3.MPI + 2 from P3.LBI)
```

### 📚 Documentation Updates

**New Files:**
- `MANUAL_OVERRIDE_TESTING_GUIDE.md` - Comprehensive testing guide with 5 scenarios

**Updated Files:**
- `README.md` - Added v6.7 features, updated field count to 38
- `USER_GUIDE.md` - Added "Manual Override Mode" section with examples
- `How_to_Add_Registers.md` - Complete rewrite with Manual Override instructions
- `CHANGELOG.md` - This file

### 🔧 Technical Details

#### Files Modified
| File | Lines Changed | Purpose |
|------|--------------|---------|
| RegisterEntry class | 232-310 | Added manual_override field |
| Add Register Dialog | 6063-6102 | Create RegisterEntry + manual_override UI |
| Edit Register Dialog | 6826-6847 | Update RegisterEntry + manual_override UI |
| export_registers() | 3029-3050 | Export manual_override + fix fallback |
| import_registers() | 2872-2935 | Import manual_override + preserve |
| P2 generation | 868-920 | Skip manual_override parameters |
| P3 generation | 1000-1010 | Skip manual_override parameters |

#### Backwards Compatibility
- ✅ Old JSON files without `manual_override` field work correctly (defaults to False)
- ✅ Import handles missing Lua Buffer fields gracefully
- ✅ Export preserves all fields for forward compatibility
- ✅ Mixed v6.6/v6.7 configs supported (auto-upgrade on import)

---

## Version 6.6 (February 2026)

### New Features
- Enhanced packet calculation with 70 address span validation
- "Calculate Packets" button with preview dialog
- Real-time validation (errors and warnings)
- Direct "Proceed to Generate" from preview
- Smart auto-configuration (Cloud/Write triggers Lua Buffer)
- Scrollable Add/Edit dialogs (600x750)
- Fixed mousewheel binding issues

### Improvements
- Import handles legacy field names
- Empty string safety (converts to 0)
- Format string conversion ("INT16" → 8)
- 37 configuration fields (v6.6) / 38 fields (v6.7+)

---

## Version 6.5 (January 2026)

### Features
- Initial Lua Buffer support
- P2/P3 array auto-generation
- Equipment grouping (JKY/JKA)
- Phase 1 transparent fields
- Write/feedback pairing (B6)
- Packet assignment (B4/B5)

---

## Version 6.0 (December 2025)

### Features
- GUI application with Tkinter
- Import/Export Register_Config.json
- Generate Modbus_Config.json and ParamMap_Config.json
- Basic validation and error handling

---

## Migration Guide

### From v6.6 to v6.7+

**What's New:**
1. Manual Override feature available in Add/Edit dialogs
2. 38 columns instead of 37 (manual_override added)
3. Lua Buffer fields properly saved/loaded
4. Console logging for manual override parameters

**Action Required:**
- **None** - Import your v6.6 configs directly
- Optional: Enable Manual Override for special cases
- Optional: Verify Lua Buffer fields with test script

**Breaking Changes:**
- **None** - Fully backwards compatible

### From v6.5 to v6.7+

**What's New:**
1. Everything from v6.6 (packet calculation, smart auto-config)
2. Manual Override (v6.7)
3. Bug fixes for Lua Buffer save/load

**Action Required:**
- Import your v6.5 configs
- Review packet assignments (may differ with new algorithm)
- Optional: Run "Calculate Packets" to optimize

---

## Known Issues

**None reported for v6.7+**

---

## Roadmap

### v6.8 (Planned)
- [ ] Bulk edit mode for multiple registers
- [ ] Undo/Redo functionality
- [ ] Register templates library
- [ ] Enhanced validation rules

### v7.0 (Future)
- [ ] Multi-file project support
- [ ] Version control integration
- [ ] Collaborative editing
- [ ] Cloud sync

---

## Support

**Issues:** Report via GitHub Issues  
**Documentation:** See README.md and USER_GUIDE.md  
**Testing:** See MANUAL_OVERRIDE_TESTING_GUIDE.md  

---

*Last Updated: February 9, 2026*

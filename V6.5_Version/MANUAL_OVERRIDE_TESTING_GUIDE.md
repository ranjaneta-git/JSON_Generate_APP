"""
MANUAL OVERRIDE FEATURE - TESTING GUIDE
========================================

Version: 6.7+ (with Manual Override support)
Date: February 9, 2026

## Feature Overview
Manual Override allows you to manually control which ParamMap arrays (P2.MPI, P2.RPCI, P3.MPI, P3.LBI) 
a parameter belongs to, preventing the automatic generation from recalculating them.

## What Was Implemented

### 1. RegisterEntry Class (lines 232-310)
- Added `manual_override` field (bool) - Phase 5

### 2. Add Register Dialog (lines 5320-5360)
- Manual Override checkbox with information panel
- Saves manual_override flag to tree column 37
- Creates RegisterEntry with manual_override field

### 3. Edit Register Dialog (lines 6376-6425)
- Manual Override checkbox (preserves existing value)
- Updates both tree and RegisterEntry on save

### 4. Export/Import (lines 3026-3050, 2872-2935)
- Export saves manual_override to JSON
- Import loads manual_override from JSON
- Backwards compatible with old configs (defaults to False)

### 5. P2/P3 Generation Logic (lines 868-1010)
- Skips registers with manual_override=True during:
  - Lua Buffer collection (P2.MPI / P2.RPCI)
  - Cloud parameter collection (P3.MPI)
  - P3.LBI is automatically skipped (uses filtered lua_buffer_user_vars)

## How It Works

### Automatic Mode (Default - manual_override=False)
1. Array Membership is calculated from:
   - Lua Buffer fields (in_lua_buffer, lua_category)
   - Cloud settings (cloud=Yes)
   - Access type (R/W/RW)

2. During ParamMap/Modbus generation:
   - Parameter is evaluated for P2.MPI
/ P2.RPCI based on lua_category
   - Parameter is evaluated for P3.MPI if cloud=Yes and NOT User Variable
   - Array Membership field is OVERWRITTEN with auto-calculated value

### Manual Override Mode (manual_override=True)
1. Array Membership is PRESERVED as-is from user input

2. During ParamMap/Modbus generation:
   - Parameter is SKIPPED in P2/P3 collection loops
   - Lua Buffer calculations proceed WITHOUT this parameter
   - P3.MPI/P3.LBI calculations proceed WITHOUT this parameter
   - Array Membership field stays EXACTLY as user typed it

## Testing Scenarios

### Test 1: Basic Manual Override
**Steps:**
1. Add a new register (Slave=1, FC=3, Address=100)
2. Set:
   - Cloud Output = Yes
   - In Lua Buffer = Yes
   - Lua Category = Equipment
   - Manual Override = ✓ CHECKED
   - Array Membership = P2.MPI,P3.MPI (manually type this)

3. Generate ParamMap/Modbus Config
4. Check Generated_ParamMap_Config.json:
   - P2.MPI should NOT include this parameter's param_id
   - P3.MPI should NOT include this parameter's param_id
   - P1.NLB should reflect reduced Lua Buffer size

5. Check Register_Config.json:
   - array_membership should be "P2.MPI,P3.MPI" (exactly as typed)
   - manual_override should be true

**Expected Result:** Parameter is excluded from automatic arrays but retains user's manual membership string.

### Test 2: Mixed Mode (Some Manual, Some Automatic)
**Steps:**
1. Add 4 registers:
   - Param 1: Lua Buffer=Yes, Category=Equipment, Manual Override=False
   - Param 2: Lua Buffer=Yes, Category=Equipment, Manual Override=True, Array Membership="P2.CUSTOM"
   - Param 3: Lua Buffer=Yes, Category=User Variable, Manual Override=False
   - Param 4: Cloud=Yes, Manual Override=True, Array Membership="P3.OVERRIDE"

2. Generate ParamMap
3. Check:
   - P2.MPI = [1] (only Param 1)
   - P2.RPCI = [3] (only Param 3)
   - P3.MPI = [] or only non-User Variable cloud params (excludes Param 4)
   - Param 2 array_membership = "P2.CUSTOM"
   - Param 4 array_membership = "P3.OVERRIDE"

**Expected Result:** Manual and automatic parameters coexist without interference.

### Test 3: Edit Existing Parameter
**Steps:**
1. Add a register with Manual Override=False, Lua Buffer=Yes
2. Generate ParamMap → note P2.MPI includes this parameter
3. Edit the register:
   - Change Manual Override to ✓ CHECKED
   - Manually set Array Membership = "CUSTOM_ARRAY"
4. Save and Generate ParamMap again
5. Check:
   - P2.MPI should NO LONGER include this parameter
   - array_membership should be "CUSTOM_ARRAY"
   - manual_override should be true

**Expected Result:** Parameter transitions from automatic to manual mode correctly.

### Test 4: Export/Import Preserves Manual Override
**Steps:**
1. Create config with mix of manual/automatic parameters
2. Export to JSON
3. Check JSON file:
   - manual_override field present for all registers
   - array_membership preserved exactly
4. Clear all registers
5. Import the JSON
6. Verify:
   - Manual Override checkboxes reflect saved state
   - Array Membership fields match original
   - Generate produces same output as before

**Expected Result:** Manual override state persists through save/load cycles.

### Test 5: Backwards Compatibility
**Steps:**
1. Import an OLD config file (without manual_override field)
2. Check that:
   - All registers default to manual_override=False
   - Automatic generation works normally
   - No errors or warnings

**Expected Result:** Old configs work seamlessly with new version.

## Validation Checklist

✓ Manual Override checkbox appears in Add Register dialog
✓ Manual Override checkbox appears in Edit Register dialog
✓ Manual Override info box displays correct instructions
✓ Checkbox state saves to tree column 37
✓ RegisterEntry object includes manual_override field
✓ Export saves manual_override to JSON
✓ Import loads manual_override from JSON
✓ P2/P3 generation skips manual_override=True registers
✓ Console logs show "[Manual Override] Param X - skipping auto-generation"
✓ Array Membership field preserved on manual override registers
✓ Mixed manual/automatic parameters work together
✓ Edit dialog preserves existing manual_override value
✓ Backwards compatible with old JSON files

## Known Behavior

1. **Manual Override + Lua Buffer Fields:**
   - Even with Manual Override, you can still set Lua Buffer fields
   - These fields are saved but NOT used for auto-generation
   - This allows documentation of intended behavior

2. **Console Logging:**
   - Manual override skips are logged: "[Manual Override] Param 7 - skipping auto-generation (user-controlled)"
   - Look for these messages during Generate to confirm feature is working

3. **Validation:**
   - No automatic validation of manual array_membership values
   - User is responsible for typing correct array names (P2.MPI, P2.RPCI, P3.MPI, P3.LBI)
   - Typos or invalid arrays will be preserved as-is

## Common Use Cases

1. **Legacy Configuration Migration:**
   - Old configs with special array_membership → Enable Manual Override to preserve them

2. **Custom Firmware Modifications:**
   - Firmware with custom arrays beyond P2/P3 → Use Manual Override to specify them

3. **Testing/Debugging:**
   - Temporarily force a parameter out of auto-generation → Enable Manual Override

4. **Partial Automation:**
   - Most parameters auto-generated, few special cases manual → Mix both modes

## Troubleshooting

**Problem:** Manual Override enabled but parameter still appears in P2.MPI
**Solution:** Verify checkbox is actually checked (should show ✓). Re-generate ParamMap. Check console logs for "[Manual Override]" message.

**Problem:** Array Membership gets overwritten even with Manual Override
**Solution:** Ensure you're editing the correct parameter. Check tree column 37 value. Re-import if needed.

**Problem:** Old config import fails
**Solution:** Manual Override feature is backwards compatible. If import fails, check for other issues (JSON syntax, missing fields).

**Problem:** Console doesn't show "[Manual Override]" logs
**Solution:** Parameter may not have manual_override=True. Double-check in Edit dialog. Verify JSON export shows "manual_override": true.

## File Changes Summary

| File | Lines Changed | Description |
|------|---------------|-------------|
| RegisterEntry class | 232-310 | Added manual_override field |
| AddRegisterDialog | 5320-5360 | Manual Override UI section |
| EditRegisterDialog | 6376-6425 | Manual Override UI section |
| export_registers() | 3026-3050 | Save manual_override to JSON |
| import_registers() | 2872-2935 | Load manual_override from JSON |
| P2 generation | 868-920 | Skip manual_override registers |
| P3 generation | 1000-1010 | Skip manual_override registers |

## Version History

- v6.7+ (Feb 9, 2026): Manual Override feature added
- v6.6 (Feb 9, 2026): Lua Buffer save/load bug fixed
- v6.5: Initial Lua Buffer support

## Next Steps After Testing

1. Test all 5 scenarios above
2. Verify console logs show correct behavior
3. Export and inspect JSON structure
4. Test with real firmware configurations
5. Update user documentation with Manual Override usage

## Questions/Support

If Manual Override isn't working as expected:
1. Check console for "[Manual Override]" log messages
2. Verify tree column 37 contains True/False values
3. Export to JSON and inspect manual_override fields
4. Test with simple 2-register config first (1 manual, 1 auto)
"""

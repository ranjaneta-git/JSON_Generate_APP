# Import Examples - Updated for v6.6

This folder contains example configurations that demonstrate the Modbus Gateway configuration system with Lua Buffer support.

## What's Updated (v6.6)

All `Register_Config.json` files have been updated to include the new Lua Buffer fields:
- `in_lua_buffer`: "Yes" or "No"
- `lua_category`: "Equipment", "User Variable", or "N/A"
- `lbi_position`: Position in Lua Buffer Index array (e.g., "1", "2", "Auto")
- `lbi_data_type`: Data type in Lua array (e.g., "Number", "Boolean")

## Examples Overview

### Example2_163params
- **Total Parameters**: 163
- **Lua Buffer**: 72 parameters (68 unique + 4 dual-category)
  - 13 User Variables (RPCI)
  - 59 Equipment parameters (MPI)
  - 4 parameters appear in BOTH categories*
- **Use Case**: Large multi-chiller system with extensive Lua integration

### Example3_25params
- **Total Parameters**: 25
- **Lua Buffer**: 11 parameters
  - 1 User Variable (RPCI)
  - 10 Equipment parameters (MPI)
- **P3.LBI**: 1 Lua-calculated output
- **Use Case**: Simple chiller with Lua control logic

### Example4_56params
- **Total Parameters**: 56
- **Lua Buffer**: 20 parameters (all Equipment)
  - 0 User Variables
  - 20 Equipment parameters (MPI)
- **Use Case**: Multi-device system (chillers, air handling units)

### Example5_25params_8E1
- **Total Parameters**: 25
- **Lua Buffer**: 12 parameters (11 unique + 1 dual-category)
  - 2 User Variables (RPCI)
  - 10 Equipment parameters (MPI)
  - 1 parameter appears in BOTH categories*
- **P3.LBI**: 2 Lua-calculated outputs
- **Serial Config**: 8E1 (8 data bits, Even parity, 1 stop bit)
- **Use Case**: Similar to Example3 but with different serial settings

### Example6_21params
- **Total Parameters**: 21
- **Lua Buffer**: 19 parameters
  - 4 User Variables (RPCI)
  - 15 Equipment parameters (MPI)
- **P3.LBI**: 4 Lua-calculated outputs
- **Use Case**: Demonstration of extensive Lua Buffer usage with calculated outputs

## Special Cases: Dual-Category Parameters

Some examples (Example2, Example5) have parameters that appear in **BOTH** User Variable (RPCI) and Equipment (MPI) arrays:

- **Example2**: Parameters 3, 4, 12, 13
- **Example5**: Parameter 2

These parameters occupy **TWO LBI positions**:
1. One position in the User Variable range (RPCI)
2. Another position in the Equipment range (MPI)

In the `Register_Config.json`, these parameters are marked with:
- Primary category in `lua_category` field (User Variable)
- Primary LBI position in `lbi_position` field
- Additional `lua_buffer_note` field explaining the dual usage

**Example:**
```json
{
  "param_id": 3,
  "in_lua_buffer": "Yes",
  "lua_category": "User Variable",
  "lbi_position": "3",
  "lua_buffer_note": "Multi-category: User Variable LBI=3, Equipment LBI=14"
}
```

## Using These Examples

### Import into Application
1. Open the Modbus Configuration Generator v6.6
2. Click "📂 Import Registers"
3. Select the `Register_Config.json` from any example folder
4. Click "🚀 Generate Configuration Files"
5. Compare the generated JSON with the existing files in the example folder

### Verifying Correctness
The generated `Modbus_Config.json` and `ParamMap_Config.json` should match the existing files in each example folder (except for dual-category parameters which may have slight differences due to the limitation of storing only one category per parameter in the register config).

## Notes for Advanced Users

### Lua Buffer Architecture
- **P2.LBI**: Sequential indices [1, 2, 3, ..., N] for ALL Lua Buffer entries
- **P2.RPCI**: User Variable param IDs (Lua script can write to these)
- **P2.MPI**: Equipment param IDs (read from Modbus, used in Lua logic)
- **P3.LBI**: Lua-calculated outputs (not direct Modbus params)

### P2 Structure
```
P2.LBI: [1, 2, 3, ..., N]
         ↓   ↓   ↓       ↓
RPCI:   [p1, p2, ...]  (User Variables, first M entries)
MPI:              [...] (Equipment params, remaining N-M entries)
```

### Dual-Category Parameters Explained
When a parameter appears in both RPCI and MPI, the firmware uses it differently:
- In RPCI context: Lua script can write to it (user variable)
- In MPI context: Used for equipment control logic

This is an advanced pattern typically used for setpoint parameters that can be:
1. Set by Lua script (RPCI)
2. Read for control logic (MPI)

## Regenerating Examples
If you need to regenerate these examples:
1. Run `python update_register_configs.py` to add Lua Buffer fields
2. Run `python verify_examples.py` to check correctness
3. Load each Register_Config.json into the GUI and generate outputs

## Troubleshooting

**Q: Why don't my generated files exactly match the examples?**  
A: Dual-category parameters may be represented slightly differently. The GUI currently stores only one category per parameter, while the firmware JSON can reference the same parameter multiple times.

**Q: Can I create my own dual-category parameters?**  
A: This is an advanced feature. Currently, you need to manually edit the generated JSON files to add a parameter to both RPCI and MPI arrays with different LBI positions.

**Q: What if I don't need Lua Buffer?**  
A: Set `in_lua_buffer = "No"` for all parameters. The system will generate empty P2 arrays, which is valid for configurations without Lua scripting.

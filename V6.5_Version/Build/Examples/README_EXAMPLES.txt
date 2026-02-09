# 📦 Example Configurations

This folder contains sample configuration files for testing and learning.

---

## Files Overview

### Test_Phase1_Register_Config.json

**Purpose:** Demonstrates Phase 1 auto-configuration features

**Contents:**
- 3 registers with different configurations
- Examples of Cloud Output triggering Lua Buffer
- Examples of Write Access triggering User Variable category

**Use Case:** Load this file to test import and generation

**How to Use:**
1. Open application
2. Click **📥 Import Registers**
3. Select `Test_Phase1_Register_Config.json`
4. Verify registers appear in table
5. Click **🔄 Generate All Configurations**
6. Check generated files match expected output

### Test_Phase1_Generated_ParamMap_Config.json

**Purpose:** Expected output after generating from Test_Phase1_Register_Config.json

**Contents:**
- P2.MPI array (Equipment parameters)
- P2.RPCI array (User Variables)
- P3.MPI array (Cloud parameters)
- JKY array (Equipment types)
- JKA array (Parameter assignments)

**Use Case:** Validate that generation produces expected output

**How to Verify:**
```bash
# Generate from register config
python modbus_tkinter_app_v6.6_complete.py
# Import Test_Phase1_Register_Config.json
# Generate files
# Compare Generated_ParamMap_Config.json with this file
```

---

## Creating Your Own Examples

### Minimal Example (Single Register)

```json
{
  "registers": [
    {
      "slave_id": 1,
      "function_code": 3,
      "address": 1000,
      "length": 1,
      "format": 8,
      "multiplier": 1.0,
      "access_type": "Read Only",
      "cloud_output": "Yes",
      "json_group": "Equipment",
      "json_unit": "Device-1",
      "json_key": "Temperature",
      "array_membership": "Sensor"
    }
  ]
}
```

### Multi-Slave Example

```json
{
  "registers": [
    {
      "slave_id": 1,
      "address": 1000,
      ...
    },
    {
      "slave_id": 2,
      "address": 1000,
      ...
    },
    {
      "slave_id": 3,
      "address": 1000,
      ...
    }
  ]
}
```

### Write/Feedback Pair Example

```json
{
  "registers": [
    {
      "b5_id": 1,
      "slave_id": 1,
      "address": 2000,
      "access_type": "Write",
      "param_type": "write",
      "paired_with": "2"
    },
    {
      "b5_id": 2,
      "slave_id": 1,
      "address": 2001,
      "access_type": "Read Only",
      "param_type": "feedback",
      "paired_with": "1"
    }
  ]
}
```

---

## Field Descriptions

### Essential Fields (Required)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `slave_id` | int | Modbus device ID | 1 |
| `function_code` | int | 3 or 4 | 3 |
| `address` | int | Register address | 1000 |
| `length` | int | Register count | 1 |
| `format` | int | Data type code | 8 |
| `multiplier` | float | Scale factor | 1.0 |
| `access_type` | string | "Read Only" or "Write" | "Read Only" |
| `cloud_output` | string | "Yes" or "No" | "Yes" |

### JSON Mapping Fields (Optional)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `json_group` | string | Group name | "Equipment" |
| `json_unit` | string | Unit name | "Chiller-1" |
| `json_key` | string | Key name | "Temperature" |
| `array_membership` | string | Equipment type | "Chiller" |

### Advanced Fields (Optional)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `in_lua_buffer` | string | "Yes" or "No" | "Yes" |
| `lua_category` | string | "Equipment" or "User Variable" | "Equipment" |
| `param_type` | string | "write", "feedback", or "read_only" | "write" |
| `paired_with` | string | B5 ID of paired param | "5" |
| `jka_param_index` | int | Equipment index | 0 |

---

## Testing Checklist

When creating new examples:

- [ ] Valid JSON syntax (use online validator)
- [ ] All essential fields present
- [ ] Slave IDs in range 1-247
- [ ] Function codes are 3 or 4
- [ ] Addresses in range 0-65535
- [ ] Format codes valid (see bmiot_constants.py)
- [ ] Multiplier is valid float
- [ ] Access type is "Read Only" or "Write"
- [ ] Cloud output is "Yes" or "No"

---

## Additional Resources

- **User Guide:** See `../USER_GUIDE.md`
- **Field Reference:** See `../APPLICATION_ENGINEER_GUIDE.md`
- **Constants:** See `../bmiot_constants.py`

---

**Last Updated:** February 8, 2026

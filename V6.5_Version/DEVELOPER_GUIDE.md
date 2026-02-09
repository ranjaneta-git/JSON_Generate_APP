# 💻 Modbus Register Configuration Tool - Developer Guide

**Version:** 6.6  
**Date:** February 2026  
**Target Audience:** Software Developers, Contributors

---

## 🏗️ Architecture Overview

### Directory Structure

```
V6.5_Version/
├── modbus_tkinter_app_v6.6_complete.py  [5965 lines] MAIN APPLICATION
├── forward_engine.py                    Forward transformation logic
├── reverse_engine.py                    Reverse transformation (import)
├── transform_wrapper.py                 Unified transformation API
├── bmiot_constants.py                   Shared constants and mappings
├── json_formatter.py                    JSON output formatting
├── ui_helpers.py                        UI utility functions
├── Start_Application.bat                Windows launcher
├── requirements.txt                     Python dependencies
├── USER_GUIDE.md                        End user documentation
├── APPLICATION_ENGINEER_GUIDE.md        System integration guide
├── DEVELOPER_GUIDE.md                   This file
├── DEPLOYMENT_GUIDE.md                  Installation instructions
├── QUICK_START_ENHANCED.md              Quick reference
├── CHANGELOG_v6.6.md                    Version history
├── README.md                            Project overview
├── Examples/                            Sample configurations
├── Tests/                               Test suite
└── __pycache__/                         Python cache
```

---

## 🔧 Technology Stack

### Core Technologies
- **Python:** 3.8+
- **GUI Framework:** Tkinter/ttk
- **Data Format:** JSON
- **Testing:** pytest

### Dependencies

```python
# requirements.txt
tkinter (built-in)
json (built-in)
typing (built-in)
copy (built-in)
collections (built-in)
datetime (built-in)
```

**No external dependencies required!** All modules use Python standard library.

---

## 📦 Module Architecture

### 1. modbus_tkinter_app_v6.6_complete.py

**Main application entry point - Monolithic architecture for simplicity**

#### Key Classes

```python
class ModbusConfigApp:
    """Main application class - manages entire GUI and state"""
    
    # State Management
    self.registers = []           # List of RegisterEntry objects
    self.next_id = 1              # Auto-increment ID
    
    # UI Components
    self.root                     # Tkinter root window
    self.tree                     # Treeview table widget
    self.notebook                 # Tab container
    
    # Key Methods
    def __init__(self, root)       # Initialize GUI
    def add_register()             # Open Add Register dialog
    def edit_selected_row()        # Open Edit dialog
    def calculate_packets()        # Auto-assign packet numbers
    def generate_files()           # Forward transformation
    def import_registers()         # Load Register_Config.json
    def export_registers()         # Save Register_Config.json
```

#### Data Structure

```python
@dataclass
class RegisterEntry:
    """Immutable register configuration"""
    slave_id: int
    function_code: int
    address: int
    length: int
    format: int
    multiplier: float
    access_type: str
    cloud_output: str
    json_group: str
    json_unit: str
    json_key: str
    array_membership: str
    # ... 25 more fields (37 total)
```

#### Architecture Decisions

**Why Monolithic:**
- ✅ Simpler deployment (single .py file)
- ✅ Easier for non-programmers to modify
- ✅ No module import issues
- ✅ Complete context in one file

**Trade-offs:**
- ❌ Large file (5965 lines)
- ❌ Harder to test individual components
- ❌ Some code duplication

### 2. forward_engine.py

**Transforms Register_Config.json → Modbus_Config + ParamMap_Config**

#### Key Functions

```python
def generate_modbus_config(registers: List[RegisterEntry]) -> dict:
    """
    Creates firmware Modbus_Config.json
    
    Returns:
    {
        "B4": {"SA": [...]},           # Slave addresses
        "B5": {                        # Parameters
            "s_Indx": [...],
            "modID": [...],
            ...
        },
        "B6": {"RP": [...]},           # Verification reads
        "Modbus_Config": {             # Polling config
            "slaves": [...]
        }
    }
    """

def generate_paramap_config(registers: List[RegisterEntry]) -> dict:
    """
    Creates firmware ParamMap_Config.json
    
    Returns:
    {
        "P2": {
            "MPI": [...],              # Equipment params
            "RPCI": [...]              # User variables
        },
        "P3": {"MPI": [...]},          # Cloud params
        "JKY": [...],                  # Equipment types
        "JKA": [[...]]                 # Param assignments
    }
    """
```

#### Generation Logic

**Block 4 (B4) - Slave Addresses:**
```python
# Extract unique slave IDs
slave_ids = sorted(set(reg.slave_id for reg in registers))
B4 = {"SA": slave_ids}
```

**Block 5 (B5) - Parameters:**
```python
B5 = {}
for i, reg in enumerate(registers, start=1):
    B5.setdefault("s_Indx", []).append(i)
    B5.setdefault("modID", []).append(reg.address)
    B5.setdefault("func_c", []).append(reg.function_code)
    # ... etc for all fields
```

**Block 6 (B6) - Verification Reads:**
```python
# Read-only params OR feedback params
verification_reads = []
for reg in registers:
    if reg.access_type == "Read Only":
        verification_reads.append(reg.b5_id)
    elif reg.param_type == "feedback":
        verification_reads.append(reg.b5_id)
B6 = {"RP": verification_reads}
```

**P2 Split Logic (CRITICAL):**
```python
P2_MPI = []   # Equipment params
P2_RPCI = []  # User variables

for reg in registers:
    if reg.in_lua_buffer == "Yes":
        if reg.lua_category == "Equipment":
            P2_MPI.append(reg.b5_id)
        elif reg.lua_category == "User Variable":
            P2_RPCI.append(reg.b5_id)
```

**P3 Cloud Logic:**
```python
P3_MPI = []
for reg in registers:
    if reg.cloud_output == "Yes":
        P3_MPI.append(reg.b5_id)
```

### 3. reverse_engine.py

**Transforms Modbus_Config + ParamMap_Config → Register_Config.json**

#### Reconstruction Logic

```python
def reconstruct_registers(modbus_config: dict, paramap_config: dict) -> List[dict]:
    """
    Reverse transformation: JSON blocks → Register list
    
    Process:
    1. Extract B5 arrays (s_Indx, modID, func_c, etc.)
    2. Zip arrays into parameter objects
    3. Merge P2/P3/B6 metadata
    4. Reconstruct full register definitions
    """
    registers = []
    B5 = modbus_config.get("B5", {})
    
    # Zip all B5 arrays
    num_params = len(B5.get("s_Indx", []))
    for i in range(num_params):
        reg = {
            "b5_id": B5["s_Indx"][i],
            "address": B5["modID"][i],
            "function_code": B5["func_c"][i],
            # ... extract all fields
        }
        registers.append(reg)
    
    return registers
```

#### Packet Calculation System (v6.6+)

**Auto-assigns packet numbers with firmware constraint validation**

```python
def auto_assign_packet_numbers(registers: List[RegisterEntry]) -> None:
    """
    Automatically calculates and assigns packet_num, packet_sa, packet_nrt
    
    Algorithm:
    1. Group by (Slave ID, Function Code)
    2. For each group:
       - Sort by address
       - Create packets with max 70 registers
       - Enforce 70 address span constraint
       - Calculate packet_sa (minimum address)
       - Calculate packet_nrt (max_addr - min_addr + 1)
    3. Validate address span ≤ 70
    
    Firmware Constraints:
    - Max 70 registers per packet (count limit)
    - Max 70 address span per packet (max_addr - min_addr + 1 ≤ 70)
    - Handles multi-register parameters (length > 1)
    - Reads contiguous address blocks
    """
    packets_by_group = {}
    
    # Group registers by (slave_id, function_code)
    for reg in registers:
        key = (reg.slave_id, reg.function_code)
        packets_by_group.setdefault(key, []).append(reg)
    
    packet_counter = 1
    
    for group_key, group_regs in packets_by_group.items():
        # Sort by address
        group_regs.sort(key=lambda r: r.address)
        
        current_packet = []
        
        for reg in group_regs:
            current_packet.append(reg)
            
            # Collect all addresses (including multi-register params)
            addresses = []
            for r in current_packet:
                for offset in range(r.length):
                    addresses.append(r.address + offset)
            
            # Calculate span
            addr_span = max(addresses) - min(addresses) + 1
            
            # Check constraints
            if len(current_packet) > 70 or addr_span > 70:
                # Start new packet
                current_packet.pop()
                assign_packet_fields(current_packet, packet_counter)
                packet_counter += 1
                current_packet = [reg]
        
        # Assign remaining registers
        if current_packet:
            assign_packet_fields(current_packet, packet_counter)
            packet_counter += 1

def assign_packet_fields(packet: List[RegisterEntry], packet_num: int):
    """Assign packet_num, packet_sa, packet_nrt to all registers in packet"""
    addresses = []
    for reg in packet:
        for offset in range(reg.length):
            addresses.append(reg.address + offset)
    
    min_addr = min(addresses)
    max_addr = max(addresses)
    nrt = max_addr - min_addr + 1
    
    for reg in packet:
        reg.packet_num = packet_num
        reg.packet_sa = min_addr
        reg.packet_nrt = nrt
```

**Property Aliases (Backwards Compatibility):**

```python
@dataclass
class RegisterEntry:
    # Internal fields (used in code)
    packet_start_addr: Optional[int] = None
    packet_register_count: Optional[int] = None
    
    # Property aliases (for JSON import/export)
    @property
    def packet_sa(self) -> Optional[int]:
        return self.packet_start_addr
    
    @packet_sa.setter
    def packet_sa(self, value: Optional[int]):
        self.packet_start_addr = value
    
    @property
    def packet_nrt(self) -> Optional[int]:
        return self.packet_register_count
    
    @packet_nrt.setter
    def packet_nrt(self, value: Optional[int]):
        self.packet_register_count = value
```

### 4. bmiot_constants.py

**Shared constants and type definitions**

```python
# Data format mapping
FORMAT_NAMES = {
    8: "INT16",
    9: "UINT16",
    10: "INT32",
    11: "UINT32",
    12: "FLOAT",
    13: "BOOLEAN",
    # ... etc
}

# Function codes
FC_HOLDING = 3
FC_INPUT = 4

# Access types
ACCESS_READ_ONLY = "Read Only"
ACCESS_WRITE = "Write"

# Cloud output
CLOUD_YES = "Yes"
CLOUD_NO = "No"

# Lua categories
LUA_EQUIPMENT = "Equipment"
LUA_USER_VAR = "User Variable"
```

### 5. json_formatter.py

**Pretty-print JSON with custom formatting**

```python
def format_json(data: dict, indent: int = 2) -> str:
    """
    Custom JSON formatter:
    - Arrays on single line if short
    - Nested objects indented
    - Consistent spacing
    """
```

---

## 🎨 UI Architecture

### Layout Hierarchy

```
TkRoot
└── Notebook (Tabs)
    ├── Tab 1: Register Configuration
    │   ├── Control Bar (Add/Edit/Delete/Clear buttons)
    │   ├── Table Frame
    │   │   └── Treeview (27 visible columns + 10 hidden)
    │   │       ├── Vertical Scrollbar
    │   │       └── Horizontal Scrollbar
    │   └── Status Bar
    ├── Tab 2: Generation Panel
    │   ├── Generate Button
    │   ├── Output Preview (Text widget)
    │   └── File Operations
    └── Tab 3: About/Help
```

### Dialog Architecture

#### Add Register Dialog (scrollable)

```python
class RegisterDialog:
    """Modal dialog for adding registers"""
    
    Structure:
    Dialog (600x750)
    └── Canvas (scrollable)
        └── Frame (scrollable_frame)
            ├── Info Panel
            ├── Essential Fields (8 fields)
            ├── Advanced Options (collapsible)
            │   ├── JSON Mapping
            │   ├── Transparent Config
            │   └── Lua Buffer Settings
            └── Button Frame (Add/Cancel)
    
    Features:
    - Mousewheel scrolling (when mouse over dialog)
    - Auto-configuration (Phase 1 logic)
    - Field validation
    - Format-based length calculation
```

#### Edit Register Dialog (scrollable)

```python
class EditRegisterDialog:
    """Modal dialog for editing existing registers"""
    
    Same structure as RegisterDialog but:
    - Pre-filled with existing values
    - Save button instead of Add
    - All fields editable
```

### Scrolling Implementation

**Fixed Issue: Mousewheel binding cleanup**

```python
# CORRECT Implementation (widget-specific binding)
def on_mousewheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")

canvas.bind("<MouseWheel>", on_mousewheel)
frame.bind("<MouseWheel>", on_mousewheel)

# Bind to all children
def bind_tree(widget):
    widget.bind("<MouseWheel>", on_mousewheel)
    for child in widget.winfo_children():
        bind_tree(child)

# Cleanup on close
def on_dialog_close():
    canvas.unbind("<MouseWheel>")
    frame.unbind("<MouseWheel>")
    dialog.destroy()
```

**WRONG Implementation (causes bugs):**
```python
# ❌ DON'T USE bind_all - persists after dialog closes
canvas.bind_all("<MouseWheel>", handler)  # BAD!
```

---

## 🧪 Testing Framework

### Test Files

```
Tests/
├── test_phase1_autoconfig.py          Phase 1 logic tests
├── test_gui_integration.py            GUI interaction tests
├── verify_examples.py                 Example config validation
├── test_forward_generation.py         Forward transform tests
└── test_reverse_generation.py         Reverse transform tests
```

### Test Structure

```python
# test_phase1_autoconfig.py
import unittest
from modbus_tkinter_app_v6.6_complete import RegisterEntry

class TestPhase1AutoConfig(unittest.TestCase):
    """Test Phase 1 smart configuration logic"""
    
    def test_cloud_output_triggers_lua_buffer(self):
        """Cloud=Yes → Lua Buffer=Yes, Category=Equipment"""
        reg = RegisterEntry(
            cloud_output="Yes",
            # ... other fields
        )
        # Apply auto-config
        reg = apply_phase1_defaults(reg)
        
        self.assertEqual(reg.in_lua_buffer, "Yes")
        self.assertEqual(reg.lua_category, "Equipment")
    
    def test_write_access_triggers_lua_buffer(self):
        """Access=Write → Lua Buffer=Yes, Category=User Variable"""
        # ... similar test
```

### Running Tests

```bash
# Run all tests
python -m pytest Tests/

# Run specific test file
python test_phase1_autoconfig.py

# Run with verbose output
python -m pytest Tests/ -v

# Run with coverage
python -m pytest Tests/ --cov=. --cov-report=html
```

---

## 🔍 Code Navigation

### Finding Key Functions

**Import Logic:**
- Lines 2433-2493: `safe_int()`, `safe_float()`, `convert_format_to_code()`
- Lines 2575-2610: Field mapping with fallbacks
- Lines 2636-2680: Tree insertion from imported data

**Generation Logic:**
- Lines 805-830: B6 verification read detection
- Lines 850-950: P2 Lua Buffer split (MPI vs RPCI)
- Lines 960-980: P3 cloud parameter detection
- Lines 3300-3450: `get_register_data()` reads from tree

**UI Dialogs:**
- Lines 4178-4800: RegisterDialog (Add) with scrollable canvas
- Lines 5208-5550: EditRegisterDialog with scrollable canvas

**Table Management:**
- Lines 2016-2130: Tree setup, column definitions
- Lines 2636-2680: Insert rows into tree
- Lines 3380-3420: Update existing rows

### Important State Variables

```python
# In ModbusConfigApp class:
self.registers = []          # Registered parameters
self.next_id = 1             # B5 ID auto-increment
self.tree                    # Treeview widget (table)
self.current_editing_item    # Row being edited
```

---

## 🛠️ Development Workflow

### Setting Up Dev Environment

```bash
# 1. Clone repository
git clone <repo_url>
cd Thermelgy-Gway-BMIoT/V6.5_Version

# 2. Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install dependencies (none required!)
# All modules use Python standard library

# 4. Run application
python modbus_tkinter_app_v6.6_complete.py
```

### Making Changes

#### 1. Adding New Field

**Step 1: Update RegisterEntry**
```python
@dataclass
class RegisterEntry:
    # ... existing fields
    new_field: str = ""  # Add your field
```

**Step 2: Update Tree Columns**
```python
columns = (..., 'New Field')  # Add to tuple
```

**Step 3: Update Add/Edit Dialogs**
```python
# In RegisterDialog and EditRegisterDialog
self.new_field_var = tk.StringVar()
ttk.Entry(..., textvariable=self.new_field_var)
```

**Step 4: Update Import/Export**
```python
# In import_registers()
new_field = reg.get('new_field', '')

# In export_registers()
reg_dict['new_field'] = reg.new_field
```

**Step 5: Update Generation**
```python
# In forward_engine.py
B5.setdefault("newField", []).append(reg.new_field)
```

#### 2. Adding New Auto-Config Rule

**Location:** Lines 4750-4850 (in RegisterDialog)

```python
def auto_configure_fields(self):
    """Apply Phase 1 smart defaults"""
    
    # Existing rules...
    
    # NEW RULE: Your custom logic
    if self.some_field_var.get() == "Trigger Value":
        self.target_field_var.set("Auto Value")
        # Update dependent fields
```

#### 3. Adding New Generation Block

**Location:** forward_engine.py

```python
def generate_modbus_config(registers):
    # ... existing blocks (B4, B5, B6)
    
    # NEW BLOCK: B7 example
    B7_data = []
    for reg in registers:
        if reg.some_condition:
            B7_data.append(reg.some_value)
    
    result["B7"] = {"Data": B7_data}
    return result
```

---

## 🐛 Debugging Tips

### Debug Logging

```python
# Add debug prints
import sys

def debug_print(msg):
    print(f"[DEBUG] {msg}", file=sys.stderr)

# In critical sections
debug_print(f"Processing register: {reg.address}")
debug_print(f"P2.MPI: {P2_MPI}")
```

### Common Issues

#### Issue: Dialog won't scroll
**Solution:** Check mousewheel binding - use widget-specific `.bind()` not `.bind_all()`

#### Issue: Import fails with KeyError
**Solution:** Add fallback in field mapping:
```python
value = reg.get('new_field', reg.get('old_field', default_value))
```

#### Issue: Generated JSON has wrong structure
**Solution:** Check array zipping in forward_engine.py:
```python
# Ensure all arrays same length
assert len(B5["s_Indx"]) == len(B5["modID"])
```

#### Issue: Tree not updating
**Solution:** Force refresh:
```python
self.tree.delete(*self.tree.get_children())
# Re-insert all rows
```

---

## 📐 Design Patterns

### 1. Data Transfer Objects (DTO)

```python
@dataclass
class RegisterEntry:
    """Immutable data container"""
    # Pros: Type hints, immutability, easy serialization
    # Cons: Verbose for large objects
```

### 2. Model-View separation

```python
# Model: RegisterEntry objects in self.registers list
# View: Treeview widget displays data
# Updates: Explicit insertions when model changes
```

### 3. Command Pattern (buttons)

```python
button = tk.Button(..., command=self.method_name)
# Decouples UI event from handler
```

### 4. Factory Pattern (dialog creation)

```python
def create_dialog(parent, mode="add"):
    if mode == "add":
        return RegisterDialog(parent)
    elif mode == "edit":
        return EditRegisterDialog(parent, existing_data)
```

---

## 🔒 Security Considerations

### Input Validation

```python
def safe_int(value, default=0):
    """Prevent injection via type coercion"""
    try:
        return int(value) if value != '' else default
    except (ValueError, TypeError):
        return default
```

### File Handling

```python
def safe_json_load(filepath):
    """Validate JSON before parsing"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        # Validate structure
        assert isinstance(data, dict)
        return data
    except Exception as e:
        messagebox.showerror("Error", f"Invalid JSON: {e}")
        return None
```

---

## 🚀 Performance Optimization

### Treeview Optimization

```python
# Batch insert (fast)
for reg in registers:
    self.tree.insert('', 'end', values=(...))

# DON'T: Update tree for each field change (slow)
# DO: Update model, then refresh tree once
```

### Generation Optimization

```python
# Use list comprehensions (faster)
slave_ids = [reg.slave_id for reg in registers]

# Avoid repeated dict access
B5_s_Indx = B5["s_Indx"]  # Cache reference
for i in range(len(registers)):
    B5_s_Indx.append(i + 1)
```

---

## 📚 Code Style Guidelines

### Python Style (PEP 8)

```python
# Class names: PascalCase
class RegisterDialog:

# Function names: snake_case
def generate_modbus_config():

# Constants: UPPER_SNAKE_CASE
ACCESS_READ_ONLY = "Read Only"

# Variables: snake_case
register_count = len(registers)
```

### Docstrings

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief description of function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ExceptionType: When this exception occurs
    """
```

### Type Hints

```python
from typing import List, Dict, Optional

def process_registers(
    registers: List[RegisterEntry],
    config: Dict[str, any]
) -> Optional[dict]:
    """Use type hints for better IDE support"""
```

---

## 🔄 Version Control

### Git Workflow

```bash
# Feature branch
git checkout -b feature/new-auto-config-rule
# Make changes
git add .
git commit -m "feat: Add XYZ auto-configuration rule"
git push origin feature/new-auto-config-rule
# Create pull request
```

### Commit Message Format

```
type(scope): brief description

Extended description if needed

Fixes #123
```

**Types:** feat, fix, docs, style, refactor, test, chore

---

## 📞 Contributing

### Reporting Bugs

Include:
1. Python version
2. Operating system
3. Steps to reproduce
4. Expected vs actual behavior
5. Sample Register_Config.json (if relevant)

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass (`python -m pytest Tests/`)
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] No debug print statements
- [ ] Type hints added for new functions

---

## 📖 Additional Resources

- **Python Tkinter Docs:** https://docs.python.org/3/library/tkinter.html
- **JSON Format Spec:** https://www.json.org/
- **BMIoT Firmware Docs:** See main README.md
- **Modbus Protocol:** See Modbus specification docs

---

**Last Updated:** February 9, 2026  
**Application Version:** v6.6  
**Maintainer:** Thermelgy Firmware Team

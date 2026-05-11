# BMIoT Config Tool v2.0 — Complete Development Plan

**Document Type:** Application Planning & Engineering Specification  
**Application Version:** 2.0  
**Reference Example:** TFA_15_16_17 (used throughout for concrete illustrations — the app is designed to work with **any** BMIoT gateway configuration)  
**Companion Document:** `BMIoT_Config_Logic_Guide.md` (firmware logic reference)

---

## TABLE OF CONTENTS

1. [Goals and Design Principles](#1-goals-and-design-principles)
2. [Technology Decision](#2-technology-decision)
3. [Internal Data Model](#3-internal-data-model)
4. [Application Screen Flow — 8 Steps](#4-application-screen-flow--8-steps)
5. [The Two Register Linkage Types](#5-the-two-register-linkage-types)
6. [Generation Engine — Section Build Order](#6-generation-engine--section-build-order)
7. [Modbus_Config.json — Step-by-Step Algorithms](#7-modbusconfigjson--step-by-step-algorithms)
8. [ParamMap_Config.json — Step-by-Step Algorithms](#8-parammapconfigjson--step-by-step-algorithms)
9. [Lua Generation](#9-lua-generation)
10. [Validation Rules — Complete Checklist](#10-validation-rules--complete-checklist)
11. [Code File Structure](#11-code-file-structure)
12. [Development Phases](#12-development-phases)

---

## 1. Goals and Design Principles

### 1.1  The Core Problem Being Solved

A field engineer needs to configure a BMIoT gateway for a new installation. They know:
- The physical device Modbus register addresses (from the device's manual)
- Which registers are for control vs. sensing vs. status
- Which registers need to appear on the cloud dashboard

They do **not** know:
- What B1/B2/B3/B4/B5/B6 mean
- How P2.MPI interleaved pairing works
- What NMD, NLB, NOR, NPT mean
- How JKA structure determines cloud JSON
- How LBI slots are assigned
- How Lua device tables map to JSON config

This application translates what the engineer knows into the exact JSON and Lua files the firmware requires.

### 1.4  Application Scope — Supported Configurations

This tool is **not** limited to TFA-type units. It must handle any BMIoT gateway configuration:

| Dimension | Supported range |
|---|---|
| Device types | Any: TFA, AHU, VFD, heat pump, chiller, meter, sensor — whatever has a Modbus register map |
| Number of devices per project | 1 to N (no hard limit) |
| Slaves per device | 1 to M (typically 1–4; sensor boards, sub-units) |
| Register types | FC1/2/3/4 (read), FC5/6 (write), any mix |
| Data formats | 16-bit unsigned/signed, 32-bit int/float (both byte orders) |
| Cloud groups | Any EqType/EqNm/key structure the project requires |
| NVS-backed values | Any key name (≤15 chars), any default |
| Writable registers | Any mix: some with hardware feedback (Link B), some without |
| Action types | Direct write, write-with-feedback, NVS-persisted value, firmware sequence |
| Lua cluster names | User-defined per project (engineer assigns cluster names in Step 3) |

The TFA_15_16_17 project is used throughout this document as a **concrete worked example**. It happens to be a well-documented real project with known-good JSON outputs that can serve as a verification target. The algorithms, data model, and generation engine described here produce correct output for **any** project that follows the BMIoT firmware JSON format.

### 1.2  Design Principles

| Principle | Implementation |
|---|---|
| Engineer sees device language, not firmware language | Labels: "Valve Write", "Position Feedback" — never "B5.PN" or "P2.MPI" |
| Derived data is never entered twice | If the app can compute it, the engineer never types it |
| Wrong ordering = wrong firmware output — so ordering is the app's job | B4 ordering, B5 ordering, P2.MPI ordering, P3.MPI ordering all auto-computed |
| The two linkage types are explicitly separated | Link A (B6 verify) auto-detected; Link B (hardware feedback) always manually entered |
| Every validation failure is explained in plain English | Not "NOR mismatch" — "Total register count doesn't match. Recalculate?" |

### 1.3  What the App Auto-Computes (Zero User Input)

| Item | Rule |
|---|---|
| B1.NOS | Count distinct slave IDs |
| B1.NOP | Count all register entries |
| B1.NPT | Count distinct B4 packets |
| B1.NOR | Sum of all B4.NRT values |
| B4 SA, NRT, FC, SID | Grouped from register entries |
| B4 ordering | All READ-FC before WRITE-FC per slave — enforced by algorithm |
| B5 ordering | Follows B4 packet order |
| B5.PN for every param | From packet assignment in B4 algorithm |
| B6.WP, B6.RP | From Link A connections (auto-detected + engineer confirms) |
| P2.LBI | Sequential 1..NLB |
| P2 slot count (NLB) | Counted from MPI + RPCI |
| P3.MDI | Sequential 1..NMD |
| P1.NLB, NLBIN, NMD | Counted from P2 and P3 lengths |
| JKC.JKH, JKC.EKS | Always `"properties"` and `"DKEY"` |
| MST.PRF | Always `0` |
| B3.SP (slave start packets) | Computed from packet grouping |
| Lua boilerplate | All state variables, constant definitions |
| Lua device table LBI numbers | From assigned LBI slots |
| Lua Act_Com function body | From action command assignments |
| Lua NVS init block | From NVS settings |

---

## 2. Technology Decision

### 2.1  Recommendation: PySide6 (Qt for Python)

**Reasons:**

| Need | PySide6 capability |
|---|---|
| Editable table with dropdowns per cell | `QTableWidget` with `QComboBox` delegates |
| Inline validation (red border on error) | `setStyleSheet()` per field, live `textChanged` signal |
| Wizard-style navigation | `QStackedWidget` with custom nav bar |
| Live JSON preview panel | `QTextEdit` in read-only mode, updated via signals |
| Drag-to-reorder rows | `QTableWidget.setDragDropMode()` + custom `dropEvent` |
| Modern appearance | `QSS` stylesheets (CSS for Qt widgets) |
| Single .exe packaging | PyInstaller — same as before |
| License | PySide6 = LGPL (free for commercial use) |

**Why not Tkinter again:**  
`ttk.Treeview` is a display widget, not a spreadsheet. Building editable cells with per-cell dropdowns in Tkinter requires custom popup dialogs per cell — the previous app hit this wall. PySide6 solves this natively.

**Why not pywebview+Flask:**  
More polished UI possible, but requires HTML/CSS/JS knowledge alongside Python. PySide6 is closer to existing Python skills and still produces a professional result.

### 2.2  Dependencies

```
PySide6          # UI framework
PyInstaller      # .exe packaging
```

No other runtime dependencies. All JSON generation and Lua generation is pure Python.

---

## 3. Internal Data Model

The entire application state lives in a `Project` object. All screens read from and write to this object. Generation engine takes this object and produces files.

### 3.1  Data Classes

```python
@dataclass
class Project:
    name: str = ""
    site: str = ""
    gateway_device_id: str = ""     # -> NTC.DI, Config_File DEV_ID
    machine_id: str = ""            # -> NTC.MI[0], Config_File MCN_ID
    baudrate: int = 19200           # -> B2.BR
    serial_format: str = "8E1"      # -> B2.DF
    protocol: str = "MQTT"          # -> Config_File PRTCL_TYPE
    mqtt_topic: str = ""            # -> Config_File MQTT_TOPIC
    mqtt_sub: str = ""              # -> Config_File MQTTACT_SUB
    mqtt_pub: str = ""              # -> Config_File MQTTACT_PUB
    devices: List[Device] = field(default_factory=list)

@dataclass
class Device:
    name: str = ""                  # Human label: "TFA15", "AHU1"
    lua_index: int = 0              # 1, 2, 3... — the Lua constant value
    slaves: List[Slave] = field(default_factory=list)
    registers: List[Register] = field(default_factory=list)

@dataclass
class Slave:
    modbus_address: int = 0         # The actual Modbus slave address (1-247)
    label: str = ""                 # "Main", "Sensor" — human label

@dataclass
class Register:
    # Engineer-entered fields
    name: str = ""                  # Human label: "Valve Position Feedback"
    slave_ref: Slave = None         # Which slave this register belongs to
    address: int = 0                # Modbus register/coil address
    fc: int = 0                     # Function code (1/2/3/4/5/6)
    length: int = 1                 # 1 for 16-bit, 2 for 32-bit
    fmt: int = 3                    # FMT code (3=UINT16 default)
    multiplier: float = 1.0         # MLT scaling
    unit: str = ""                  # Display unit
    direction: str = "read"         # "read" | "write" | "readwrite"

    # Link A — B6 verify pair (auto-detected, engineer confirms)
    link_a_verify: 'Register' = None   # The register used to verify this write

    # Link B — hardware feedback (engineer must select)
    link_b_feedback: 'Register' = None  # The actual hardware state register

    # Lua cluster grouping (Step 3 / Step 4 — set by engineer)
    cluster_name: str = ""     # User-defined cluster name: "Valve", "Fan", "Damper", "Speed", etc.
    cluster_slot: str = ""     # User-defined slot within cluster: "Write", "Stat", "Cmd", "FB", etc.
                               # The Link B feedback register auto-inherits cluster_name with slot "Stat"
                               # if the engineer does not override it.

    # Cloud output assignment (Step 5)
    cloud_enabled: bool = False
    cloud_group: str = ""           # JKA EqType: "TFA15_AIE1"
    cloud_name: str = ""            # JKA device name: "valve_Fb"
    cloud_key: str = ""             # JKA key: "per"
    cloud_order: int = 0            # Position in JKA cloud output sequence

    # Action command assignment (Step 6)
    action_enabled: bool = False
    action_id: int = 0              # Aid 1-N
    action_type: str = ""           # "direct_write" | "write_with_feedback" | "nvs_setpoint" | "nvs_mode" | "firmware_sequence"
    action_scale_min: float = 0.0   # Input range from cloud
    action_scale_max: float = 100.0
    action_raw_min: float = 0.0     # Raw value to send to device
    action_raw_max: float = 1000.0

    # NVS settings (Step 7)
    nvs_enabled: bool = False
    nvs_key: str = ""               # NVS flash key string: "STP15"
    nvs_default: float = 0.0        # Value to restore if NVS is empty
    nvs_restore_on_boot: bool = True

    # Computed fields (set by engine, not user)
    param_id: int = 0               # B5 position (1-indexed)
    packet_id: int = 0              # B4 packet number assigned
    lbi_slot: int = 0               # P2 LBI slot assigned
    mdata_index: int = 0            # P3 M_data[] index
```

---

## 4. Application Screen Flow — 9 Steps

```
Step 1: Project Setup
Step 2: Devices & Slaves
Step 3: Registers
Step 4: Link B (Feedback)
Step 5: LBI Slots
Step 6: Cloud Groups
Step 7: NVS Setpoints
Step 8: Network / MQTT
Step 9: Generate JSON
```

Navigation: `[<- Back]  [Step 4 of 9]  [Next ->]`  
At any step, `[Save Project]` saves all data to `.bmiot` file.

---

### Step 1 — Project Setup

| Field | Type | Example | Notes |
|---|---|---|---|
| Project name | Text | "2nd Floor TFA Bank" | For file naming |
| Site location | Text | "Madurai HB2F" | Documentation only |
| Gateway Device ID | Text | "GW01" | -> NTC.DI |
| Machine ID | Text | "GWAY01" | -> NTC.MI[0] |
| Baud rate | Dropdown | 9600 / **19200** / 38400 / 115200 | -> B2.BR |
| Serial format | Dropdown | **8E1** / 8N1 / 8O1 / 8E2 | -> B2.DF |
| Protocol | Dropdown | **MQTT** / HTTPS | -> Config_File |
| MQTT publish topic | Text | "NBTST" | -> Config_File |
| MQTT action subscribe | Text | "S_NBTST1" | -> Config_File |
| MQTT action publish | Text | "P_NBTST2" | -> Config_File |

Bold = default selection.

---

### Step 2 — Add Devices

Engineer sees a card for each device. `[+ Add Device]` button opens a dialog:

| Field | Type | Example |
|---|---|---|
| Device name | Text | "TFA15" / "AHU1" / "VFD3" / any label |
| Number of slaves | Number | 1 (most common), 2 (main + sensor board), up to M |
| Slave 1 address | Number | Any valid Modbus address (1–247) |
| Slave 1 label | Text | "Main" (default) |
| Slave 2 address (if needed) | Number | Any valid Modbus address |
| Slave 2 label | Text | "Sensor" (default) |
| Template (optional) | Dropdown | None / TFA / AHU / VFD / Heat Pump / (user templates) |

Device order can be reordered by drag. Order determines:
- The Lua device index values (Device1=1, Device2=2, Device3=3 ...)
- The Action ID sequencing (Aid 1,2,3 for device 1, Aid 4,5,6 for device 2 ...)

**Device Templates** pre-fill Step 3 with typical registers for that device type. Engineer only changes addresses. Any number of devices may be added; the engine handles N devices with M slaves each.

> **TFA_15_16_17 example:** 3 devices (TFA15, TFA16, TFA17), each with 2 slaves (Main + Sensor). This produces 6 slave IDs and 30 packets. Other projects may have 1 device with 1 slave or 10 devices with 3 slaves each — the engine handles all cases.

---

### Step 3 — Add Registers

For each device, a register table with `[+ Add Register]` button.

**Add Register dialog:**

| Field | Type | Options | Notes |
|---|---|---|---|
| Register name | Text | — | "Valve Position Feedback" / "Discharge Pressure" / "Speed Reference" |
| Slave | Dropdown | lists device slaves | "Main (addr 1)" |
| Register address | Number | 0-65535 | The Modbus address |
| Register type | Dropdown | Holding Reg (FC3) / Input Reg (FC4) / Output Coil (FC1) / Discrete Input (FC2) / Write Holding (FC6) / Write Coil (FC5) | |
| Direction | Dropdown | Read Only / **Write Only** / Read+Write | Write Only = write register. Read+Write = register that is both written and its echo is read |
| Data size | Dropdown | **16-bit** / 32-bit | 16-bit = LN=1, 32-bit = LN=2 |
| Data format | Dropdown | **Unsigned Int** / Signed Int / IEEE Float | Maps to FMT |
| Scaling | Dropdown | **Raw (x1)** / divide by 10 / divide by 100 / Custom | Maps to MLT |
| Custom MLT | Number (if Custom) | 0.01 | Only shown for Custom |
| Unit label | Text | "%" / "degC" / "kPa" / "rpm" / "Hz" | Display only |
| Cluster name | Text (optional) | "Valve" / "Fan" / "Damper" / "Speed" / any label | Groups this register into a named Lua device table. Write registers and their Link B feedback registers share the same cluster name. Leave blank for read-only monitoring registers. |
| Cluster slot | Text (optional, auto if blank) | "Write" / "Stat" / "Cmd" / "FB" / any label | The slot key within the cluster. Defaults to "Write" for write registers; Link B feedback registers auto-receive "Stat". Can be overridden for custom slot names. |

**Inline validation (live):**
- Same address + same FC + same slave already exists -> Warning: "Register at address 4066 with FC3 already defined for this slave"
- Write register at same address as existing Read register of different FC -> Info: "A matching read register exists at 4066 FC3 — Link A will be auto-suggested"
- Address = 0 -> Error: "Address cannot be zero"
- No registers with direction Write or Read+Write -> Warning at step exit: "No writable registers defined"

**Register row color coding:**
- Blue = Read Only
- Orange = Write Only (FC5/FC6)
- Purple = Read+Write (write register that also has a read at same address)
- Green = will be NVS-backed (set later in Step 7)

---

### Step 4 — Connect Registers

This is the most important new step. For every register with direction "Write" or "Read+Write", the app shows a connection card with **two separate link questions**.

```
+--------------------------------------------------------------------+
|  VALVE WRITE  |  Addr: 4066  |  FC6  |  Slave: Main (1)          |
+--------------------------------------------------------------------+
|                                                                     |
|  LINK A - Write Confirm  (B6 verify pair)                          |
|  Purpose: Firmware reads this register to confirm the command was  |
|           accepted by the device (same address, read function code)|
|                                                                     |
|  [AUTO] addr 4066, FC3 - "Valve Write Echo"                        |
|         [Use this]  [Override...]                                  |
|                                                                     |
|  LINK B - Hardware Feedback  (P2 LBI pair)                         |
|  Purpose: Lua reads this to know the ACTUAL physical valve         |
|           position. May be at a different address than the command |
|           register. Check your device datasheet.                   |
|                                                                     |
|  Select feedback register: [  addr 1561, FC3 - Valve FB  v]       |
|                                                                     |
|  (i) If Link B is empty, app generates CntrlDev_NoFB2             |
|      (write without feedback confirmation in Lua).                 |
|                                                                     |
+--------------------------------------------------------------------+
```

**Status badges per connection card:**
- OK: Both links set — ready for generation
- WARN: Link A only — write will work, no hardware feedback check in Lua
- ERROR: No links — write register exists but is unverifiable and unmonitored
- INFO: Link A auto-detected, Link B still needs selection

**Link B dropdown** shows only registers from the same device (both slaves) with a Read FC.  
Registers already used as Link A are still available for Link B (same register can be both).

**Cannot advance to Step 5** if any write register has ERROR status (no Link A at minimum).

---

### Step 5 — Cloud Output Assignment

For each register, a checkbox: "Publish to cloud dashboard?"

When checked, three fields appear inline:

| Field | Example | Maps to |
|---|---|---|
| Cloud group | "TFA15_AIE1" | JKA EqType |
| Device label | "valve_Fb" | JKA device name (EqNm) |
| Property key | "per" | JKA key |

**Live cloud JSON preview panel** (right side, updates in real time):

```json
{
  "properties": {
    "TFA15_DIE1": {
      "OFF":  { "St": 0 },
      "ON":   { "St": 1 },
      "AM":   { "St": 0 }
    },
    "TFA15_AIE1": {
      "valve_Fb":  { "per": 75.0 },
      "EC_Fan_Fb": { "per": 80.0 }
    }
  }
}
```

**Cloud group order panel** (below register table):  
All unique cloud groups (JKA EqType entries) listed with drag handles for reordering.  
This ordering directly determines P3.MPI sequence.

**Counter at bottom:**  
`Cloud parameters: 42 Modbus + 9 NVS-backed = 51 total | NMD will be: 51`

---

### Step 6 — Action Commands

For each register with direction "Write" or "Read+Write" — a row with checkbox "Control from cloud?"

When checked:

| Field | Type | Example |
|---|---|---|
| Action ID | Auto-assigned (editable) | 1 |
| Control type | Dropdown | Direct write / Write with hardware feedback / NVS-persisted setpoint / NVS-persisted mode / Firmware sequence |
| Input range | Numbers | 0 to 100 |
| Raw output range | Numbers | 0 to 1000 (auto-filled based on scaling) |
| NVS key (if NVS type) | Text | "STP15" / "SPEED1" / any ≤15 char key |

**Control type definitions (general):**

| Control type | When to use | Link B required? | Lua function generated |
|---|---|---|---|
| Direct write | Write a value to device, no hardware confirmation needed | No | `CntrlDev_NoFB2` |
| Write with hardware feedback | Write + check hardware actually moved to commanded position | **Yes** | `CntrlDev4` |
| NVS-persisted setpoint | Write to device AND persist to flash (survives power loss); use for numeric setpoints | No (NVS) | `ValWrt_Pt` |
| NVS-persisted mode | Write a mode/flag AND persist to flash; use for binary modes | No (NVS) | `ValWrt_bm` |
| Firmware sequence | Call a firmware-specific Lua function (project-specific; engineer provides function name) | Depends | User-specified |

**Notes:**
- "Direct write" and "Write with hardware feedback" differ only by whether Link B is set
- If the engineer selects "Write with hardware feedback" but has not set Link B in Step 4, the app auto-downgrades to "Direct write" with a warning
- "NVS-persisted" types require the engineer to enter a key name (≤15 characters)
- "Firmware sequence" is for project-specific firmware functions not covered by the above (e.g., custom enable sequences); the engineer types the Lua function name manually

> **TFA_15_16_17 example:** 3 valve position actions (Write with hardware feedback), 3 fan speed actions (Write with hardware feedback), 3 fan enable actions (Direct write), 3 setpoint actions (NVS-persisted setpoint), 3 BMS mode actions (NVS-persisted mode), 3 valve tracker actions (Firmware sequence: `TFA_Enable`). Total 18 actions (Aid 1–18).

---

### Step 7 — NVS / Setpoints

Any action with type "NVS-persisted setpoint", "NVS-persisted mode", or a firmware-sequence type with NVS implied will appear here. This step shows all NVS-backed slots and lets the engineer set:

| Field | Example | Notes |
|---|---|---|
| NVS key | "STP15" / "SP_AHU1" / any string | Must be <= 15 chars (ESP32 Preferences limit) |
| Default value | 250 / 0 / 100 | Used if NVS is empty on first boot |
| Also publish to cloud? | yes/no | Includes this in M_data / cloud JSON |

NVS LBI slot numbers are auto-assigned after all Modbus-backed LBI slots are filled (Phase 3 of P2.MPI assignment).

> **TFA_15_16_17 example:** 9 NVS slots (3 setpoints + 3 BMS modes + 3 valve trackers), assigned LBI 31–39.

---

### Step 8 — Review & Generate

**Summary panel** (example shows TFA_15_16_17 values; actual values are computed from the current project):
```
Devices:          3  (TFA15, TFA16, TFA17)     ← varies per project
Total slaves:     6  (Slave IDs: 1,2,3,4,5,6)  ← 1 per device minimum
Registers:       63                             ← depends on device complexity
Packets:         30  (NPT)                      ← computed by engine
Register slots:  63  (NOR = sum of NRT)         ← computed by engine
LBI slots:       39  (30 Modbus + 9 NVS-backed) ← computed by engine
Cloud params:    51  (42 Modbus + 9 NVS-backed) ← computed by engine
Action IDs:      18  (Aid 1-18)                 ← set by engineer
NVS keys:         9  (STP15/16/17, BMS15/16/17, VALR15/16/17)
```

**Validation summary (green/orange/red for each):**
- OK  NOR (63) = sum of all NRT (63) — match
- OK  NMD (51) = JKA(keys x names) (51) — match
- OK  All write registers have Link A (B6 verify)
- OK  All write registers have Link B (hardware feedback)
- OK  All P3.MPI param IDs exist in B5

**[Generate Files]** -> folder picker -> creates:
- `Modbus_Config.json`
- `ParamMap_Config.json`
- `MainScript.lua`
- `FuncScript.lua`
- `output_preview.json` (sample cloud JSON with placeholder values)

---

## 5. The Two Register Linkage Types

### 5.1  Link A — Write Confirm (B6 Verify Pair)

```
Write register:  addr 4066, FC6  (Lua writes the command here)
Link A partner:  addr 4066, FC3  (same address, firmware reads back to verify)
```

- **Purpose:** Firmware verification after write. `Modbus_ParmWrite()` sends FC6, then reads back the echo register to confirm the slave accepted the value.
- **Detection logic:** Same slave, same address, different FC where one is write-FC (5/6) and the other is read-FC (3/1).
- **App action:** Auto-detect and show as a suggestion. Engineer must confirm (or override).
- **Effect on output:** Populates B6.WP and B6.RP arrays.

**Auto-detection rules:**

| Write FC | Expected verify FC | Rule |
|---|---|---|
| FC6 (Write Holding Register) | FC3 (Read Holding Register) | Same slave, same address |
| FC5 (Write Single Coil) | FC1 (Read Coils) | Same slave, same address |

If no matching read register exists at the same address -> Link A is empty -> show warning. User can still generate but B6 won't include this write register, meaning Modbus_ParmWrite will return READ_PARAM_NOT_FOUND(2) and the write will silently fail on the device.

### 5.2  Link B — Hardware Feedback (P2 LBI Pair)

```
Write register:     addr 4066, FC6  (command valve to target position)
Link B partner:     addr 1561, FC3  (actual physical valve position sensor)
```

- **Purpose:** Lua uses this to verify that the physical hardware actually moved to the commanded position. Different address entirely — determined by the device's hardware design.
- **Detection logic:** Cannot be auto-detected. Only the engineer knows this from the device datasheet.
- **App action:** Required manual selection. Dropdown shows all read-only registers of same device.
- **Effect on output:**
  - Determines the interleaved pairing in P2.MPI: `[writeParamID, feedbackParamID, ...]`
  - Determines which LBI slots are paired in Lua device tables
  - If present: app generates `CntrlDev4` (write + timed feedback check)
  - If absent: app generates `CntrlDev_NoFB2` (write only, no feedback)

### 5.3  Why They Are Different

| | Link A (B6) | Link B (P2 LBI) |
|---|---|---|
| What it verifies | Modbus register echo (immediate) | Physical hardware state (may have delay) |
| Same address? | Yes always | No — usually different |
| Auto-detectable? | Yes | No |
| Who knows? | App (from address+FC match) | Field engineer (from datasheet) |
| If missing | Firmware write silently unverified | Lua has no hardware state feedback |
| Output location | B6.WP + B6.RP | P2.MPI ordering |

---

## 6. Generation Engine — Section Build Order

### 6.1  Why Order Matters

Each section depends on previously built sections:

```
User enters registers in Steps 3-7
             |
             v
B2  <- Step 1 project data (independent)
B3  <- Step 2 device data (slave addresses)
             |
             v
B4  <- ALL registers (group into packets) <- MUST BE FIRST JSON section built
             |
             +-- B5  <- needs B4 packet numbers assigned
             |         |
             |         +-- B6  <- needs B5 param IDs
             |
             +-- B1  <- needs B4 (for NPT and NOR) AND B5 (for NOP)
                        <- ALWAYS BUILT LAST for Modbus
             |
             v
JKA  <- Step 5 cloud assignments (cloud groups/names/keys)
             |
             +-- P2.MPI  <- needs B5 param IDs + Link B connections
             |
             +-- P3.MPI  <- needs JKA order + B5 param IDs
             |
             +-- P1  <- needs P2 length + P3 length
                        <- ALWAYS BUILT LAST for ParamMap
```

### 6.2  Required Build Sequence

**Modbus_Config.json:**
```
Step 1: B2  (baud, format — from project settings)
Step 2: B3  (slave list — from device definitions)
Step 3: B4  (packet table — from all registers, applies ordering rules)
Step 4: B5  (param table — from all registers, uses B4 packet numbers)
Step 5: B6  (write/verify pairs — from Link A connections, uses B5 param IDs)
Step 6: B1  (counts — derived from B3, B4, B5)
```

**ParamMap_Config.json:**
```
Step 7:  JKA  (cloud hierarchy — from cloud assignments)
Step 8:  JKC  (hardcoded)
Step 9:  NTC  (from project settings)
Step 10: MST  (hardcoded)
Step 11: P2   (LBI mapping — needs B5 param IDs + Link B connections + NVS list)
Step 12: P3   (M_data mapping — needs JKA order + B5 param IDs + NVS LBI slots)
Step 13: P1   (counts — from P2 and P3 lengths)
```

---

## 7. Modbus_Config.json — Step-by-Step Algorithms

### 7.1  B2 — Serial Settings

Simplest section. Directly from Step 1:

```python
def build_B2(project) -> dict:
    return {
        "BR": project.baudrate,       # e.g. 19200
        "DF": project.serial_format   # e.g. "8E1"
    }
```

---

### 7.2  B3 — Slave Configuration

B3 requires knowing how many packets each slave will have (for SP calculation). But packets come from B4, which hasn't been built yet. **Solution:** B3.SP is calculated from B4 results. So B3 is partially built before B4 (just SI), and SP is filled after B4.

**Step 1 — Build SI (slave address list):**
```python
def build_B3_SI(devices) -> list:
    # Collect all slave Modbus addresses in device order, slave order
    all_slaves = []
    for device in devices:               # device order as entered by engineer
        for slave in device.slaves:      # slave order within device (main first, sensor second)
            all_slaves.append(slave.modbus_address)
    return all_slaves
    # TFA result: [1, 2, 3, 4, 5, 6]
```

**Step 2 — Build SP (start packet per slave) — after B4 is built:**
```python
def build_B3_SP(packets_per_slave) -> list:
    # packets_per_slave[i] = how many packets slave i owns
    # SP[0] = 1 always
    # SP[i] = SP[i-1] + packets_per_slave[i-1]
    sp = []
    current = 1
    for count in packets_per_slave:
        sp.append(current)
        current += count
    return sp
    # TFA: packets_per_slave = [9, 1, 9, 1, 9, 1]
    # SP = [1, 10, 11, 20, 21, 30]
```

---

### 7.3  B4 — Packet Table (Most Complex)

B4 groups registers into Modbus transactions. This is the most complex part of the engine and the most critical to get right — because B5.PN and B1.NOR both depend on it.

#### 7.3.1  Definitions

- **Packet** = a single Modbus transaction request (read or write) to one slave address
- **Read packet** = FC 1, 2, 3, or 4 — polls registers continuously in background
- **Write packet** = FC 5 or 6 — dispatched on-demand when a value needs writing
- **SA** = start address of the packet = address of the first register in the group
- **NRT** = number of registers the transaction covers = (last_address - first_address + length_of_last_register)
- **MAX_NRT** = **60** — the maximum number of register slots a single packet may cover. If adding the next contiguous register would push NRT above 60, the current packet is closed and a new packet begins at that register.

#### 7.3.2  Contiguous Address Grouping Rule

Two registers on the same slave with same FC can be in the same packet if their addresses form a contiguous block:

```
Register A: addr=1, LN=1  -> occupies addr slots [1]
Register B: addr=2, LN=1  -> occupies addr slots [2]
-> Contiguous: YES -> same packet

Register A: addr=1,    LN=1  -> occupies [1]
Register C: addr=4066, LN=1  -> occupies [4066]
-> Contiguous: NO -> separate packets (gap of 4064 addresses)

Register D: addr=1561, LN=1  -> occupies [1561]
Register E: addr=1562, LN=1  -> occupies [1562]
-> Contiguous: YES -> same packet, NRT=2
```

**Contiguity test:**
```python
def is_contiguous(prev_addr, prev_ln, next_addr) -> bool:
    return next_addr == prev_addr + prev_ln
```

**For 32-bit params (LN=2):** the register occupies two address slots.  
Example: 32-bit float at addr 100 occupies slots 100 and 101. Next contiguous register starts at 102.

**Packet size limit — MAX_NRT = 60:**  
Even when addresses are contiguous and FC matches, a packet must be split once its NRT would exceed 60.  
The new packet starts at the register that would have pushed NRT over the limit.

```
Example: 70 contiguous FC3 holding registers at addrs 100-169
  Packet A: SA=100, NRT=60  (addrs 100-159)
  Packet B: SA=160, NRT=10  (addrs 160-169)
  -> Two packets instead of one
```

**Why this limit exists:** The Modbus specification caps a single read transaction at 125 registers (for FC3/FC4) and 2000 coils (for FC1/FC2), but the BMIoT firmware imposes a tighter internal buffer limit of 60 register slots. Exceeding this causes the firmware to silently truncate or corrupt the read results.

#### 7.3.3  B4 Build Algorithm — Step by Step

**Input:** All `Register` objects from all devices  
**Output:** Ordered list of packets with SA, NRT, FC, SID

```
ALGORITHM: build_B4(all_registers)

PHASE 1: Build read packets (preserve engineer entry order)
----------------------------------------------------------
For each slave (in B3.SI order):
    Collect all registers belonging to this slave with FC in {1, 2, 3, 4}
    In the ORDER the engineer added them (do NOT sort by FC or address)
    
    Scan in order — start new packet when FC changes OR address not contiguous OR packet would exceed MAX_NRT:
        
        would_be_nrt = reg.address - current_packet.SA + reg.length
        
        if reg.fc == prev.fc AND is_contiguous AND would_be_nrt <= 60:
            Extend current packet (add register, update NRT)
        else:
            Close current packet, save to list
            Start new current packet with this register
            (If only reason for split was MAX_NRT, new packet has same FC — it is
             still contiguous with the previous one, just in a separate transaction)
    Save final current packet

PHASE 2: Build write packets (one packet per write register)
------------------------------------------------------------
For each slave (in B3.SI order):
    Collect all registers belonging to this slave with FC in {5, 6}
    In the ORDER the engineer added them
    For each write register:
        Create individual packet: SA=reg.address, NRT=reg.length, FC=reg.fc, SID=slave.address
        (Write registers are never grouped with each other)

PHASE 3: Order all packets
--------------------------
Final ordered list = [slave1 read pkts, slave1 write pkts,
                      slave2 read pkts, slave2 write pkts, ...]
This guarantees ALL read packets before write packets per slave.
Assign sequential packet numbers 1, 2, 3... to this ordered list.

PHASE 4: Record packet number back on each register
---------------------------------------------------
For each packet in the list:
    For each register that belongs to this packet:
        register.packet_id = packet.number

OUTPUT ARRAYS (parallel arrays, index 0 = packet 1):
    SA  = [packet.start_address for packet in packets]
    NRT = [packet.num_registers  for packet in packets]
    FC  = [packet.fc             for packet in packets]
    SID = [packet.slave_address  for packet in packets]
```

#### 7.3.4  TFA Example Trace

Engineer added registers for Slave 1 in this order:
```
Coils 1-8    (FC1, addrs 1,2,3,4,5,6,7,8)
Echo regs    (FC3, addrs 4066,4067)
Fan analog   (FC4, addr  4067)
Valve FB     (FC3, addrs 1561,1562)
Enable coil  (FC1, addr  301)
Discrete     (FC2, addr  301)
--- then write registers ---
Valve cmd    (FC6, addr  4066)
Fan cmd      (FC6, addr  4067)
Enable cmd   (FC5, addr  301)
```

Read packet scan:
```
FC1@1 -> new pkt. FC1@2,3,4,5,6,7,8 -> contiguous -> extend (NRT grows to 8). 
FC3@4066 -> FC changed -> close pkt1(FC1,SA=1,NRT=8). New pkt2.
FC3@4067 -> same FC, contiguous (4067=4066+1) -> extend pkt2 (NRT=2).
FC4@4067 -> FC changed -> close pkt2(FC3,SA=4066,NRT=2). New pkt3(FC4,SA=4067,NRT=1).
FC3@1561 -> FC changed -> close pkt3. New pkt4.
FC3@1562 -> same FC, contiguous -> extend pkt4 (NRT=2). End of reads.
Close pkt4(FC3,SA=1561,NRT=2).
FC1@301 -> new pkt5(FC1,SA=301,NRT=1).
FC2@301 -> FC changed -> close pkt5. New pkt6(FC2,SA=301,NRT=1).

Slave 1 read packets:  pkt1(FC1,SA=1,NRT=8), pkt2(FC3,SA=4066,NRT=2),
                        pkt3(FC4,SA=4067,NRT=1), pkt4(FC3,SA=1561,NRT=2),
                        pkt5(FC1,SA=301,NRT=1), pkt6(FC2,SA=301,NRT=1)

Slave 1 write packets: pkt7(FC6,SA=4066,NRT=1), pkt8(FC6,SA=4067,NRT=1),
                        pkt9(FC5,SA=301,NRT=1)

Global order for slave 1: pkts 1-9
```

This matches the TFA B4 exactly:  
`SA=[1,4066,4067,1561,301,301, 4066,4067,301, ...]`  
`FC=[1,3,4,3,1,2, 6,6,5, ...]`  
`NRT=[8,2,1,2,1,1, 1,1,1, ...]`

#### 7.3.5  Python Implementation

```python
def build_packets_for_slave_reads(read_regs_in_engineer_order):
    """
    Input:  list of read-FC registers in the order engineer added them
    Output: list of Packet objects
    """
    packets = []
    if not read_regs_in_engineer_order:
        return packets
    
    current_regs = [read_regs_in_engineer_order[0]]
    
    MAX_NRT = 60   # firmware internal buffer limit — never exceed this
    
    for reg in read_regs_in_engineer_order[1:]:
        prev = current_regs[-1]
        same_fc    = (reg.fc == prev.fc)
        contiguous = (reg.address == prev.address + prev.length)
        
        # Calculate what NRT would be if we add this register to the current packet
        first = current_regs[0]
        would_be_nrt = reg.address - first.address + reg.length
        
        if same_fc and contiguous and would_be_nrt <= MAX_NRT:
            current_regs.append(reg)
        else:
            # Split: either FC changed, gap in addresses, or packet would exceed 60
            packets.append(make_packet(current_regs))
            current_regs = [reg]
    
    packets.append(make_packet(current_regs))
    return packets

def make_packet(regs):
    first = regs[0]
    last  = regs[-1]
    nrt   = last.address - first.address + last.length
    return Packet(
        fc             = first.fc,
        slave_address  = first.slave_ref.modbus_address,
        start_address  = first.address,
        num_registers  = nrt,
        member_registers = regs
    )

def build_B4(devices):
    all_packets = []
    packet_counter = 1
    packets_per_slave = []
    
    for device in devices:
        for slave in device.slaves:
            slave_regs = [r for r in device.registers if r.slave_ref == slave]
            read_regs  = [r for r in slave_regs if r.fc in [1, 2, 3, 4]]
            write_regs = [r for r in slave_regs if r.fc in [5, 6]]
            
            read_packets  = build_packets_for_slave_reads(read_regs)
            write_packets = [make_packet([r]) for r in write_regs]
            
            slave_packets = read_packets + write_packets  # reads ALWAYS before writes
            packets_per_slave.append(len(slave_packets))
            
            for pkt in slave_packets:
                pkt.number = packet_counter
                packet_counter += 1
                for reg in pkt.member_registers:
                    reg.packet_id = pkt.number
                all_packets.append(pkt)
    
    return all_packets, packets_per_slave
```

---

### 7.4  B5 — Parameter Table

B5 is built **after** B4 because every B5 entry needs a PN (packet number) which only exists after B4 assigns packet numbers.

#### 7.4.1  Algorithm

```
param_counter = 1

For each packet (in packet number order 1..NPT):
    For each register belonging to this packet (in address order within packet):
        Create B5 entry:
            ID  = param_counter
            PN  = this packet's number
            STA = register.address
            LN  = register.length     (1 or 2)
            FMT = register.fmt        (from data format field)
            MLT = register.multiplier (from scaling field)
        
        register.param_id = param_counter
        param_counter += 1

IMPORTANT: B5 ordering follows B4 packet order exactly.
Write packets come at the end of each slave's packet block,
so write-type params always get the HIGHEST param IDs within each slave block.
```

#### 7.4.2  FMT Code Mapping

| UI Selection | FMT Code |
|---|---|
| Unsigned Int 16-bit | 3 (UINT16bit) — default |
| Signed Int 16-bit | 8 (INT16bit) |
| IEEE Float 32-bit (low-word first) | 1 (FP32bit_BA) |
| IEEE Float 32-bit (high-word first) | 2 (FP32bit_AB) |
| Signed Int 32-bit (low-word first) | 4 (INT32bit_BA) |
| Signed Int 32-bit (high-word first) | 5 (INT32bit_AB) |
| Unsigned Int 32-bit (low-word first) | 6 (UINT32bit_BA) |
| Unsigned Int 32-bit (high-word first) | 7 (UINT32bit_AB) |

#### 7.4.3  MLT Mapping

| UI Selection | MLT value |
|---|---|
| Raw (x1) | 1 |
| Divide by 10 | 0.1 |
| Divide by 100 | 0.01 |
| Custom | user-entered float |

#### 7.4.4  TFA Example Trace (partial)

```
Pkt 1 (FC1, SA=1, NRT=8, slave=1):  addrs 1,2,3,4,5,6,7,8
    -> B5 params 1,2,3,4,5,6,7,8  |  PN=1 for all  |  FMT=3, MLT=1

Pkt 2 (FC3, SA=4066, NRT=2, slave=1):  addrs 4066,4067
    -> B5 params 9,10  |  PN=2  |  FMT=3, MLT=1

Pkt 3 (FC4, SA=4067, NRT=1, slave=1):  addr 4067
    -> B5 param 11  |  PN=3  |  MLT=0.1 (fan analog FB: raw 0-1000 = 0-100%)

Pkt 4 (FC3, SA=1561, NRT=2, slave=1):  addrs 1561,1562
    -> B5 params 12,13  |  PN=4
    -> param 12: MLT=0.1 (valve FB, raw 0-1000 -> 0-100%)

Pkt 5 (FC1, SA=301, NRT=1, slave=1): addr 301
    -> B5 param 14  |  PN=5  |  FMT=3, MLT=1

Pkt 6 (FC2, SA=301, NRT=1, slave=1): addr 301
    -> B5 param 15  |  PN=6  |  FMT=3, MLT=1

Pkt 7 (FC6, SA=4066, NRT=1, slave=1): <- WRITE
    -> B5 param 16  |  PN=7

Pkt 8 (FC6, SA=4067, NRT=1, slave=1): <- WRITE
    -> B5 param 17  |  PN=8

Pkt 9 (FC5, SA=301,  NRT=1, slave=1): <- WRITE
    -> B5 param 18  |  PN=9

Pkt 10 (FC3, SA=1561, NRT=3, slave=2):  addrs 1561,1562,1563
    -> B5 params 19,20,21  |  PN=10
    -> param 20: MLT=0.01 (RAT sensor, high precision)

Then TFA16 (pkts 11-20, params 22-42) and TFA17 (pkts 21-30, params 43-63).
Final: NOP=63, NOR=sum(NRT)=(8+2+1+2+1+1+1+1+1+3)*3 = 63
```

---

### 7.5  B6 — Write/Verify Pairs

Built from Link A connections confirmed in Step 4.

```python
def build_B6(registers):
    WP = []
    RP = []
    
    # Collect write registers that have a Link A connection, sorted by param_id
    write_regs = [r for r in registers if r.fc in [5, 6] and r.link_a_verify is not None]
    write_regs.sort(key=lambda r: r.param_id)
    
    for wr in write_regs:
        WP.append(wr.param_id)
        RP.append(wr.link_a_verify.param_id)
    
    return {"WP": WP, "RP": RP}

# TFA result:
# WP = [16,17,18, 37,38,39, 58,59,60]  <- write params in param_id order
# RP = [ 9,10,14, 30,31,35, 51,52,56]  <- their verify-read partners
```

**Critical rule:** WP[i] and RP[i] are always index-paired. The firmware does:  
`RP = BL6[i].RP where BL6[i].WP == writeParamID`  
Never reorder WP or RP independently.

---

### 7.6  B1 — Global Counts (Always Last)

B1 is computed after B3, B4, and B5 are fully built.

```python
def build_B1(b3_si, b4_packets, b5_params):
    NOS = len(b3_si)                           # Count of slaves
    NPT = len(b4_packets)                      # Count of packets
    NOP = len(b5_params["ID"])                 # Count of params
    NOR = sum(b4_packets["NRT"])               # Sum of all NRT values
    
    return {"NOS": NOS, "NOP": NOP, "NPT": NPT, "NOR": NOR}

# TFA result: {"NOS": 6, "NOP": 63, "NPT": 30, "NOR": 63}
```

**Validation before finalizing:**
```
assert NOR == sum(all B4.NRT values)   # if wrong, Reg[] layout is corrupt
assert NPT == count(B4 rows)
assert NOP == count(B5 rows)
assert NOS == len(B3.SI)
```

---

## 8. ParamMap_Config.json — Step-by-Step Algorithms

### 8.1  JKA — Cloud JSON Hierarchy

Built from cloud assignments in Step 5. JKA structure:
```
JKA[i] = [EqType, [key1, key2, ...], [name1, name2, ...]]
```

#### 8.1.1  JKA Build Algorithm

```
Input: All registers with cloud_enabled=True, sorted by cloud_order

Step 1: Walk through registers in cloud_order sequence
Step 2: Group into JKA entries:
    - Same group AND same key set -> same JKA entry
    - Different groups -> different JKA entries
    - Entries ordered by the first appearance of each group in cloud_order

Step 3: Within each JKA entry:
    keys = unique key values, in order of first appearance
    names = unique name values, in cloud_order within the group

Output: List of [EqType, [keys], [names]] arrays
```

**M_data slots consumed by one JKA entry:**  
`slots = len(keys) * len(names)`

**TFA example:**
```json
["TFA15_DIE1",      ["St"],   ["OFF","ON","AM","Fire_Pu","Fire_damp"]]  -> 5 slots
["TFA15_DIE1_Trip", ["Tr"],   ["Trip"]]                                  -> 1 slot
["TFA15_DIE1_Fire", ["Ar"],   ["Fire"]]                                  -> 1 slot
["TFA15_DIE1_DPS",  ["Ar"],   ["DPS"]]                                   -> 1 slot
["TFA15_AIE1",      ["per"],  ["valve_Fb","EC_Fan_Fb"]]                  -> 2 slots
["TFA15_DOE1",      ["St"],   ["EC_Fan_Enable"]]                          -> 1 slot
...
Total across all JKA entries = 51 = P1.NMD
```

---

### 8.2  P2.MPI — LBI Slot Assignment

P2.MPI determines the LBI slot numbers used in Lua device tables.

#### 8.2.1  Algorithm

```
Phase 1: Write + Hardware Feedback pairs (from Link B connections)
------------------------------------------------------------------
current_lbi = 1

For each device (in device order as entered by engineer):
    For each write register of this device (in engineer entry order):
        P2.MPI.append(write_register.param_id)
        write_register.lbi_slot = current_lbi
        current_lbi += 1
        
        if write_register.link_b_feedback is not None:
            P2.MPI.append(link_b_feedback.param_id)
            link_b_feedback.lbi_slot = current_lbi
            current_lbi += 1

Phase 2: Read-only registers (not already assigned in Phase 1)
--------------------------------------------------------------
For each device (in device order):
    For each read register of device (in engineer entry order):
        if register.lbi_slot == 0:   # not yet assigned
            P2.MPI.append(register.param_id)
            register.lbi_slot = current_lbi
            current_lbi += 1

Phase 3: NVS-backed slots -> go to P2.RPCI (not MPI)
-----------------------------------------------------
nvs_counter = 1
For each NVS slot (in order from Step 7):
    P2.RPCI.append(nvs_counter)
    nvs_slot.lbi_slot = current_lbi
    current_lbi += 1
    nvs_counter += 1

P2.LBI = list(range(1, current_lbi))   # always [1, 2, 3, ..., NLB]
```

#### 8.2.2  TFA Example Trace

```
current_lbi = 1

Phase 1 - Device TFA15:
  Valve Write (param 16) + Link B: Valve FB (param 12) -> LBI 1,2  | MPI: [16, 12]
  Fan Write   (param 17) + Link B: Fan FB   (param 11) -> LBI 3,4  | MPI: [17, 11]
  Enable Write(param 18) + Link B: Discrete (param 15) -> LBI 5,6  | MPI: [18, 15]

Phase 1 - Device TFA16 (same pattern, params shifted +21):
  Valve Write (param 37) + FB (param 33) -> LBI 7,8   | MPI: [37,33]
  Fan Write   (param 38) + FB (param 32) -> LBI 9,10  | MPI: [38,32]
  Enable Write(param 39) + FB (param 36) -> LBI 11,12 | MPI: [39,36]

Phase 1 - Device TFA17 (params +42):
  Valve Write (param 58) + FB (param 54) -> LBI 13,14 | MPI: [58,54]
  Fan Write   (param 59) + FB (param 53) -> LBI 15,16 | MPI: [59,53]
  Enable Write(param 60) + FB (param 57) -> LBI 17,18 | MPI: [60,57]

current_lbi = 19

Phase 2 - Read-only registers (all devices in device order):
  TFA15 param 5  -> LBI 19 | MPI: [5]
  TFA15 param 20 -> LBI 20 | MPI: [20]   <- SEN[Stat][TFA15] = 20 in Lua
  TFA15 param 26 -> LBI 21 | MPI: [26]
  TFA16 param 41 -> LBI 22 | MPI: [41]
  TFA16 param 47 -> LBI 23 | MPI: [47]
  TFA17 param 62 -> LBI 24 | MPI: [62]
  TFA15 param 2  -> LBI 25 | MPI: [2]
  TFA16 param 23 -> LBI 26 | MPI: [23]
  TFA17 param 44 -> LBI 27 | MPI: [44]
  TFA15 param 1  -> LBI 28 | MPI: [1]
  TFA16 param 22 -> LBI 29 | MPI: [22]
  TFA17 param 43 -> LBI 30 | MPI: [43]

current_lbi = 31

Phase 3 - NVS slots:
  STP15 -> LBI 31 | RPCI: [1]
  BMS15 -> LBI 32 | RPCI: [2]
  STP16 -> LBI 33 | RPCI: [3]
  BMS16 -> LBI 34 | RPCI: [4]
  STP17 -> LBI 35 | RPCI: [5]
  BMS17 -> LBI 36 | RPCI: [6]
  VALR15-> LBI 37 | RPCI: [7]
  VALR16-> LBI 38 | RPCI: [8]
  VALR17-> LBI 39 | RPCI: [9]

FINAL P2.MPI:
[16,12, 17,11, 18,15, 37,33, 38,32, 39,36, 58,54, 59,53, 60,57,
 5,20,26, 41,47,62, 2,23,44, 1,22,43]   <- matches TFA exactly

FINAL P2.RPCI: [1,2,3,4,5,6,7,8,9]
P2.LBI: [1,2,3,...,39]  (always sequential)
```

---

### 8.3  P3.MPI — M_data[] Mapping

P3.MPI ordering **must exactly match JKA sequential consumption order**.  
This is the most critical constraint in the entire ParamMap generation.

#### 8.3.1  Algorithm

```python
def build_P3_MPI(registers, jka):
    P3_MPI = []
    
    for jka_entry in jka:           # in JKA order — do NOT change this order
        eq_type = jka_entry[0]
        keys    = jka_entry[1]
        names   = jka_entry[2]
        
        for name in names:          # outer loop: device name
            for key in keys:        # inner loop: property key
                reg = find_register(registers,
                                    cloud_group=eq_type,
                                    cloud_name=name,
                                    cloud_key=key)
                P3_MPI.append(reg.param_id)
                reg.mdata_index = len(P3_MPI) - 1
    
    return P3_MPI

def find_register(registers, cloud_group, cloud_name, cloud_key):
    for r in registers:
        if r.cloud_group == cloud_group and r.cloud_name == cloud_name and r.cloud_key == cloud_key:
            return r
    raise ValueError(f"No register for {cloud_group}/{cloud_name}/{cloud_key}")
```

#### 8.3.2  TFA Example Trace

```
JKA[0] = ["TFA15_DIE1", ["St"], ["OFF","ON","AM","Fire_Pu","Fire_damp"]]
  name="OFF",       key="St" -> param 1  | P3.MPI[0] = 1
  name="ON",        key="St" -> param 2  | P3.MPI[1] = 2
  name="AM",        key="St" -> param 5  | P3.MPI[2] = 5  <- skips 3,4 (other JKA entries)
  name="Fire_Pu",   key="St" -> param 7  | P3.MPI[3] = 7
  name="Fire_damp", key="St" -> param 8  | P3.MPI[4] = 8

JKA[1] = ["TFA15_DIE1_Trip", ["Tr"], ["Trip"]]
  name="Trip", key="Tr" -> param 3 | P3.MPI[5] = 3

JKA[2] = ["TFA15_DIE1_Fire", ["Ar"], ["Fire"]]
  name="Fire", key="Ar" -> param 4 | P3.MPI[6] = 4

JKA[3] = ["TFA15_DIE1_DPS",  ["Ar"], ["DPS"]]
  name="DPS",  key="Ar" -> param 6 | P3.MPI[7] = 6

JKA[4] = ["TFA15_AIE1", ["per"], ["valve_Fb","EC_Fan_Fb"]]
  name="valve_Fb",  key="per" -> param 12 | P3.MPI[8]  = 12
  name="EC_Fan_Fb", key="per" -> param 11 | P3.MPI[9]  = 11  <- 11 after 12 (name order)

... (continues for all TFA15 groups, then TFA16, TFA17) ...

P3.MPI starts: [1,2,5,7,8, 3, 4, 6, 12,11, 15, 19, 20,21, ...]   <- matches TFA exactly
```

Note: P3.MPI is NOT sorted by param_id. Its order is 100% determined by JKA iteration.

---

### 8.4  P3.LBI — NVS Cloud Slots

After the Modbus-backed M_data slots, NVS-backed slots that are cloud-enabled go into P3.LBI.

```python
def build_P3_LBI(nvs_registers_with_cloud_enabled):
    # Only NVS-backed registers marked cloud-enabled in Step 5
    # In the order their LBI slots were assigned (Phase 3 order)
    return [reg.lbi_slot for reg in nvs_registers_with_cloud_enabled]

# TFA: all 9 NVS slots are cloud-enabled
# P3.LBI = [31,32,33,34,35,36,37,38,39]
```

---

### 8.5  P3.MDI — Always Sequential

```python
def build_P3_MDI(p3_mpi, p3_lbi):
    total = len(p3_mpi) + len(p3_lbi)
    return list(range(1, total + 1))   # [1, 2, 3, ..., NMD]
# TFA: [1, 2, 3, ..., 51]
```

---

### 8.6  P1 — Global Counts (Always Last)

```python
def build_P1(p2_mpi, p2_rpci, p3_mpi, p3_lbi):
    NLB   = len(p2_mpi) + len(p2_rpci)    # Total LBI slots
    NLBIN = NLB                             # Always equals NLB
    NMD   = len(p3_mpi) + len(p3_lbi)     # Total M_data slots
    
    return {"NLB": NLB, "NLBIN": NLBIN, "NMD": NMD}

# TFA: {"NLB": 39, "NLBIN": 39, "NMD": 51}
```

**Mandatory cross-validation before writing the file:**
```python
jka_nmd = sum(len(entry[1]) * len(entry[2]) for entry in jka)
assert jka_nmd == NMD, f"FATAL: JKA expects {jka_nmd} M_data slots but NMD={NMD}. Firmware will refuse to boot."
```

---

### 8.7  NTC, JKC, MST — Simple Fields

```python
def build_NTC(project):
    return {
        "IP": "",                          # MQTT broker IP (Config_File overrides this)
        "PT": "",                          # Port
        "CI": "",                          # Client ID
        "SN": [1],                         # Always [1]
        "MI": [project.machine_id],        # Machine ID
        "MT": ["GWAY"],                    # Always ["GWAY"]
        "DI": project.gateway_device_id    # Device ID
    }

def build_JKC():
    return {"JKH": "properties", "EKS": "DKEY"}   # Always hardcoded

def build_MST():
    return {"PRF": 0}   # Always hardcoded
```

---

## 9. Lua Generation

### 9.1  MainScript.lua Structure

The app generates MainScript.lua fully. Sections in order:

```
Section 1: Device index constants    (from device names and lua_index assignments)
Section 2: Device structure constants (hardcoded: Write=1, Stat=2, EnWrite=5, EnStat=6)
Section 3: Value constants           (hardcoded: NO_DATA=-1, OFF=0, ON=1, etc.)
Section 4: Device cluster tables     (generated from Phase 1 LBI slot assignments)
Section 5: LBI table                 (NVS-backed slots: LBI={[1]=31,[2]=32,...})
Section 6: NVS key tables            (VALR keys for valve position persistence)
Section 7: Timer and state variables (boilerplate)
Section 8: Initialization block      (NVS restore + initial valve position commands)
Section 9: Main while loop           (Act_Com, device logic calls, setpoint reads, debug)
```

#### 9.1.1  Device Cluster Table Generation (from LBI slots)

After LBI slot assignment completes, Lua device tables are auto-generated. The cluster names and slot names come from the `cluster_name` and `cluster_slot` fields set by the engineer in Step 3. The engine groups registers by cluster name, then by slot name, across all devices.

```python
def generate_cluster_tables(devices):
    """
    Builds Lua device cluster table definitions.
    Cluster names and slot names come from Register.cluster_name / Register.cluster_slot
    — set by the engineer in Step 3 (not hardcoded by the app).
    
    Example for TFA project:
      Valve cluster: Write slot (write regs) + Stat slot (Link B feedback regs)
      ECFan cluster: Write, Stat, EnWrite, EnStat slots
      SEN cluster:   Stat slot (read-only sensor)
    
    Example for AHU project:
      Damper cluster: Cmd slot + FB slot
      Fan cluster:    Speed slot + Status slot
      Temp cluster:   Reading slot
    """
    from collections import defaultdict
    
    # cluster_groups[cluster_name][slot_name][device_lua_index] = lbi_slot
    cluster_groups = defaultdict(lambda: defaultdict(dict))
    
    for device in devices:
        dev_idx = device.lua_index
        for reg in device.registers:
            if reg.cluster_name:
                cn = reg.cluster_name
                cs = reg.cluster_slot if reg.cluster_slot else "Write"
                cluster_groups[cn][cs][dev_idx] = reg.lbi_slot
                
                # Link B feedback register auto-gets same cluster with "Stat" slot
                # (unless the feedback register has its own cluster_slot override)
                if reg.link_b_feedback:
                    fb = reg.link_b_feedback
                    fb_slot = fb.cluster_slot if fb.cluster_slot else "Stat"
                    cluster_groups[cn][fb_slot][dev_idx] = fb.lbi_slot
    
    def lua_table(d):
        # d = {device_lua_index: lbi_slot, ...}
        entries = ",".join(f"[{k}]={v}" for k, v in sorted(d.items()))
        return "{" + entries + "}"
    
    lines = []
    for cluster_name, slots in cluster_groups.items():
        slot_parts = []
        for slot_name, dev_map in slots.items():
            slot_parts.append(f"[{slot_name}]={lua_table(dev_map)}")
        lines.append(f"{cluster_name} = {{{', '.join(slot_parts)}}}")
    
    return "\n".join(lines)
```

> **TFA_15_16_17 example output** (engineer assigned cluster names "Valve", "ECFan", "SEN"):
```lua
Valve = {[Write]={[TFA15]=1,[TFA16]=7,[TFA17]=13}, [Stat]={[TFA15]=2,[TFA16]=8,[TFA17]=14}}
ECFan = {[Write]={[TFA15]=3,[TFA16]=9,[TFA17]=15}, [Stat]={[TFA15]=4,[TFA16]=10,[TFA17]=16},
         [EnWrite]={[TFA15]=5,[TFA16]=11,[TFA17]=17}, [EnStat]={[TFA15]=6,[TFA16]=12,[TFA17]=18}}
SEN   = {[Stat]={[TFA15]=20,[TFA16]=22,[TFA17]=24}}
LBI   = {[1]=31,[2]=32,[3]=33,[4]=34,[5]=35,[6]=36,[7]=37,[8]=38,[9]=39}
```

> **AHU example output** (engineer assigned cluster names "Damper", "Fan"):
```lua
Damper = {[Cmd]={[AHU1]=1,[AHU2]=5}, [FB]={[AHU1]=2,[AHU2]=6}}
Fan    = {[Speed]={[AHU1]=3,[AHU2]=7}, [Status]={[AHU1]=4,[AHU2]=8}}
LBI    = {[1]=9,[2]=10}  -- NVS slots (if any)
```

#### 9.1.2  Act_Com Line Generation

For each action command (sorted by Aid number), the Lua function is chosen based on the control type and whether Link B is set:

```python
def generate_act_com_line(action):
    aid = action.action_id
    dev = action.device.lua_index       # e.g., TFA15, AHU1 — the Lua constant value
    cn  = action.register.cluster_name  # e.g., "Valve", "Fan", "Damper"
    
    sc = (f"Scale_Value(Aval,"
          f"{action.action_scale_min},{action.action_scale_max},"
          f"{action.action_raw_min},{action.action_raw_max})")
    
    if action.action_type == "write_with_feedback":
        # CntrlDev4: write + timed feedback check (Link B must be set)
        return (f"Insrt_ActCom2(Aid,Aval,{aid},Aval, "
                f"CntrlDev4, {cn},{dev},Write,Stat, {sc},Aval,FB_TYM)")
    
    elif action.action_type == "direct_write":
        # CntrlDev_NoFB2: write only, no hardware feedback
        return (f"Insrt_ActCom2(Aid,Aval,{aid},Aval, "
                f"CntrlDev_NoFB2, {cn},{dev},Write, {sc})")
    
    elif action.action_type == "nvs_setpoint":
        # ValWrt_Pt: write value + persist to NVS flash
        lbi_idx = action.nvs_lbi_index
        return (f'Insrt_ActCom2(Aid,Aval,{aid},Aval, '
                f'ValWrt_Pt, Aval, "{action.nvs_key}", LBI[{lbi_idx}])')
    
    elif action.action_type == "nvs_mode":
        # ValWrt_bm: write mode flag + persist to NVS flash
        lbi_idx = action.nvs_lbi_index
        return (f'Insrt_ActCom2(Aid,Aval,{aid},Aval, '
                f'ValWrt_bm, Aval, "{action.nvs_key}", LBI[{lbi_idx}])')
    
    elif action.action_type == "firmware_sequence":
        # User-specified Lua function (project-specific firmware function)
        func = action.firmware_function_name  # entered by engineer
        return action.firmware_sequence_template.format(
            Aid=aid, Dev=dev, Func=func)
```

> **Note:** For firmware-sequence actions (e.g., TFA's `TFA_Enable`), the engineer enters the Lua function name and a template for the Act_Com line in Step 6. This avoids hardcoding TFA-specific logic into the engine.

#### 9.1.3  NVS Init Block Generation

```python
def generate_nvs_init_block(nvs_slots, valve_devices):
    lines = ["do", "    delay(5000)", ""]
    
    # Restore setpoints and BMS modes
    for slot in nvs_slots:
        if slot.nvs_type in ["setpoint", "bms_mode"]:
            lines.append(f'    NVS_Read("{slot.nvs_key}", {slot.lbi_slot})   -- {slot.name}')
    
    lines.append("")
    
    # Restore valve position trackers
    for device in valve_devices:
        lines.append(f'    VAL_PS[{device.lua_index}] = NVS_GetVal("{device.nvs_valr_key}")')
    
    lines.append("")
    
    # Restore valve positions to hardware
    for device in valve_devices:
        lines.append(
            f"    CntrlDev_NoFB2(Valve, {device.lua_index}, Write, "
            f"Scale_Value(VAL_PS[{device.lua_index}], 0, 100, 0, 1000))"
        )
    
    lines.append("end")
    return "\n".join(lines)
```

### 9.2  FuncScript.lua

FuncScript.lua contains the firmware helper functions. The **core helper functions** are common across all BMIoT projects and are treated as static boilerplate — the app ships `FuncScript_template.lua` and copies it as-is to the output folder. The `Act_Com()` function body is the only part that varies per project (generated from Step 6 action assignments).

**Common helper functions (present in all projects):**  
`CntrlDev4`, `CntrlDev_NoFB2`, `ValWrt_Pt`, `ValWrt_bm`, `NVS_Read`, `NVS_GetVal`,  
`Scale_Value`, `Val_Set`, `Insrt_ActCom2`, `Buff_Write_Wait`

**Project-specific helper functions** (only present when the firmware supports them):  
`TFA_Logic`, `TFA_Enable`, `Valv_Logic`, `Cmd_Seq3`, `GetValvePercentage`  
These are included in `FuncScript_template.lua` if the target firmware version provides them.  
Future firmware versions may add new helper functions — the tool should allow selecting a firmware version when creating a project, and ship a matching `FuncScript_template.lua` for each version.

The `Act_Com()` function body is always generated. Everything else is static for the selected firmware version.

---

## 10. Validation Rules — Complete Checklist

### 10.1  Blocking Errors (prevent file generation)

| Rule | Check | Error message shown to user |
|---|---|---|
| V1 | `B1.NOR == sum(all B4.NRT)` | "Register count mismatch: NOR={x} but sum of NRT={y}. The firmware Reg[] buffer will be corrupt. Check for missing or overlapping registers." |
| V2 | `B1.NPT == count(B4 packets)` | "Packet count mismatch: expected {x} packets but built {y}." |
| V3 | `B1.NOP == count(B5 params)` | "Parameter count mismatch: expected {x} params but built {y}." |
| V4 | `P1.NMD == Σ(JKA keys×names)` | "Cloud parameter count mismatch: NMD={n} but JKA structure requires {m}. Firmware will refuse to start." |
| V5 | `P1.NLB == len(P2.MPI) + len(P2.RPCI)` | "LBI slot count mismatch." |
| V6 | `P1.NMD == len(P3.MPI) + len(P3.LBI)` | "M_data slot count mismatch." |
| V7 | All B6.WP param IDs have write FC (5 or 6) | "Param {id} is in B6.WP but has FC{fc} (read-only). WP only accepts write params." |
| V8 | All B6.RP param IDs have read FC (1-4) | "Param {id} is in B6.RP but has FC{fc} (write). RP only accepts read params." |
| V9 | All P3.MPI values exist in B5.ID | "P3.MPI references param {id} which does not exist in B5." |
| V10 | All NVS keys <= 15 characters | "NVS key '{key}' is {n} characters. ESP32 Preferences limit is 15 characters." |
| V11 | No duplicate NVS keys | "NVS key '{key}' is assigned to both '{r1}' and '{r2}'." |
| V12 | B5.LN matches B5.FMT | "Param {id}: FMT={fmt} requires LN={expected} but register has LN={actual}." |
| V13 | All devices have at least 1 register | "Device '{name}' has no registers defined." |
| V14 | All B4 packets have NRT <= 60 | "Packet {n} (slave {sid}, FC{fc}, SA={sa}): NRT={nrt} exceeds the maximum of 60. This is a generation bug — report it." (Should never appear if the algorithm is correct; acts as a safety net.) |

### 10.2  Warnings (shown but allow generation)

| Rule | Warning message |
|---|---|
| W1 | Write register missing Link A (no B6 verify pair) | "'{name}': No verify pair. Modbus_ParmWrite will return error 2 (READ_PARAM_NOT_FOUND) on writes to this register." |
| W2 | Write register missing Link B (no hardware feedback) | "'{name}': No hardware feedback register. App will use CntrlDev_NoFB2 (write without physical confirmation)." |
| W3 | Cloud-enabled register not matched to any JKA slot | "'{name}': Marked cloud-enabled but not found in any cloud group assignment." |
| W4 | NVS key defined but restore-on-boot is disabled | "'{key}': NVS key will not be restored on boot. Device will start with default value {default}." |

---

## 11. Code File Structure

```
bmiot_configtool_v2/
|
+-- main.py                        <- Entry point, creates QApplication, launches MainWindow
+-- __init__.py                    <- Package init
|
+-- engine/
|   +-- __init__.py
|   +-- constants.py               <- FC codes, FMT codes, default values
|   +-- models.py                  <- Project, Device, Register, CloudGroup, NvsSlot dataclasses
|   +-- importer.py                <- Import from Modbus/ParamMap JSON files
|   +-- exporter.py                <- Export to Modbus/ParamMap JSON files (reverse of importer)
|   +-- generator.py               <- Generate Modbus_Config.json and ParamMap_Config.json
|   +-- validator.py               <- Validate project: returns errors and warnings
|
+-- ui/
|   +-- __init__.py
|   +-- main_window.py             <- QMainWindow, QStackedWidget, 9-step wizard nav bar
|   +-- project_io.py              <- Save/load .bmiot_project files
|   +-- styles.py                  <- QSS stylesheet for modern UI appearance
|   +-- pages/
|       +-- __init__.py
|       +-- base_page.py           <- Base class for all wizard pages
|       +-- page_project.py        <- Step 1: Project name, baud rate, serial format
|       +-- page_devices.py        <- Step 2: Device/slave management
|       +-- page_registers.py      <- Step 3: Register table per device (address, FC, FMT, MLT)
|       +-- page_link_b.py         <- Step 4: Link B feedback pairing for write registers
|       +-- page_lbi.py            <- Step 5: LBI slot assignment for Lua script access
|       +-- page_cloud_groups.py   <- Step 6: Cloud group (cluster) configuration for MQTT
|       +-- page_nvs.py            <- Step 7: NVS setpoint configuration
|       +-- page_network.py        <- Step 8: MQTT broker, device ID, machine ID
|       +-- page_generate.py       <- Step 9: Validate and generate JSON output files
|
+-- tests/
    +-- __init__.py
    +-- test_generator.py          <- Unit tests for the generation engine
```
|
+-- project_io.py                  <- save_project() / load_project() for .bmiot files
|
+-- requirements.txt               <- PySide6
```

### 11.1  Engine Module Interfaces

All engine modules: pure Python, zero UI dependency, independently testable.

```python
# packet_builder.py
def build_B4(devices: List[Device]) -> Tuple[List[Packet], List[int]]:
    # Returns (all_packets, packets_per_slave_count)
    # Side effect: sets register.packet_id on all registers

# param_builder.py
def assign_param_ids(packets: List[Packet]) -> None:
    # Side effect: sets register.param_id on all registers, in packet order

# b6_builder.py
def build_B6(registers: List[Register]) -> dict:
    # Returns {"WP": [...], "RP": [...]}

# lbi_builder.py
def assign_lbi_slots(devices: List[Device], nvs_slots: List[Register]) -> None:
    # Side effect: sets register.lbi_slot on all registers

# jka_builder.py
def build_JKA(registers: List[Register]) -> List[list]:
    # Returns JKA array: [[EqType,[keys],[names]], ...]

# mdata_builder.py
def build_P3(registers: List[Register], jka: List[list],
             nvs_cloud: List[Register]) -> dict:
    # Returns {"MDI": [...], "MPI": [...], "LBI": [...]}

# modbus_gen.py
def generate_modbus_config(project: Project) -> dict:
    # Runs full build sequence B2->B3->B4->B5->B6->B1
    # Returns complete Modbus_Config.json dict, ready for json.dumps()

# paramap_gen.py
def generate_paramap_config(project: Project) -> dict:
    # Runs full build sequence JKA->JKC->NTC->MST->P2->P3->P1
    # Returns complete ParamMap_Config.json dict

# validator.py
class ValidationResult:
    errors: List[str]
    warnings: List[str]
    is_valid: bool   # True if errors is empty

def validate(project: Project) -> ValidationResult:
    # Runs all V1-V13 checks and W1-W4 checks
```

---

## 12. Development Phases

| Phase | Deliverables | Test criteria |
|---|---|---|
| 1 — Engine Core | All engine modules, models.py | Unit test: TFA project object → exact JSON match with known-good files; simple 1-device project also tested |
| 2 — UI Shell | main_window.py, wizard nav, empty step pages | Click through all 8 steps without crash |
| 3 — Steps 1-3 | Project/Device/Register entry (incl. cluster_name/slot fields) | Enter TFA manually; inspect models.py object state |
| 4 — Step 4 | Link A auto-detect, Link B dropdown | All write registers show correct auto-suggestions; test FC5/FC6 both |
| 5 — Steps 5-7 | Cloud, Actions, NVS | Live preview panel matches expected cloud JSON; test both NVS types |
| 6 — Step 8 + Generate | Validation + file output | Generated files diff against known-good TFA JSONs: zero differences; also test a minimal 1-device project |
| 7 — Save/Load + Templates | .bmiot project file, device templates, export-as-template | Round-trip: save → load → generate → same output; test with AHU or VFD template |
| 8 — Packaging | PyInstaller .exe | Runs on clean Windows machine with no Python installed |

### Phase 1 Unit Test Pattern

```python
# tests/test_engine.py
#
# TFA_15_16_17 is used as the primary integration test because it is a
# real project with known-good JSON outputs. The engine must also pass
# tests for simpler configurations (1 device, 1 slave, no NVS, no Link B).

def build_tfa_test_project() -> Project:
    """Manually coded TFA_15_16_17 project — used as ground truth for engine verification."""
    project = Project(name="TFA_15_16_17", baudrate=19200, serial_format="8E1",
                      machine_id="GWAY01", gateway_device_id="GW01")
    
    tfa15 = Device(name="TFA15", lua_index=1)
    slave1 = Slave(modbus_address=1, label="Main")
    slave2 = Slave(modbus_address=2, label="Sensor")
    tfa15.slaves = [slave1, slave2]
    
    # Add registers in engineer entry order (matches TFA B4 order)
    # Coils 1-8 on slave1 FC1
    for addr in range(1, 9):
        tfa15.registers.append(Register(name=f"coil_{addr}", slave_ref=slave1,
                                         address=addr, fc=1, fmt=3, multiplier=1))
    # ... (all 63 registers with cluster_name and cluster_slot fields)
    
    project.devices = [tfa15, tfa16, tfa17]
    return project

def build_minimal_test_project() -> Project:
    """Single device, single slave, 3 registers — minimum viable project."""
    project = Project(name="TestMinimal", baudrate=9600, serial_format="8N1",
                      machine_id="GW001", gateway_device_id="DEV1")
    
    dev = Device(name="Sensor1", lua_index=1)
    slave = Slave(modbus_address=1, label="Main")
    dev.slaves = [slave]
    dev.registers = [
        Register(name="Temp", slave_ref=slave, address=100, fc=4, fmt=3, multiplier=0.1),
        Register(name="Pressure", slave_ref=slave, address=101, fc=4, fmt=3, multiplier=0.01),
    ]
    project.devices = [dev]
    return project

def test_tfa_modbus_generation():
    project = build_tfa_test_project()
    result = validate(project)
    assert result.errors == [], f"Validation errors: {result.errors}"
    
    modbus = generate_modbus_config(project)
    
    import json
    with open("tests/expected/TFA_Modbus_Config.json") as f:
        expected = json.load(f)
    
    assert modbus == expected, "Generated Modbus_Config.json does not match expected output"

def test_tfa_paramap_generation():
    project = build_tfa_test_project()
    paramap = generate_paramap_config(project)
    
    import json
    with open("tests/expected/TFA_ParamMap_Config.json") as f:
        expected = json.load(f)
    
    assert paramap == expected, "Generated ParamMap_Config.json does not match expected output"

def test_minimal_project_generation():
    """Smoke test — ensure engine works for a single-device, no-NVS, no-Link-B project."""
    project = build_minimal_test_project()
    result = validate(project)
    assert result.errors == []
    
    modbus   = generate_modbus_config(project)
    paramap  = generate_paramap_config(project)
    
    # Structural checks (no golden file for this — verify computed properties)
    assert modbus["B1"]["NOS"] == 1
    assert modbus["B1"]["NOP"] == 2
    assert paramap["P1"]["NLB"] == 2
```

---

## Appendix A — Algorithm Correctness Verification Table

Use this table to verify the engine output for any project. The "General formula" column applies to all configurations. The "TFA example" column shows expected values for the TFA_15_16_17 test case.

| Check | General formula | TFA example |
|---|---|---|
| B1.NOR | `sum(B4.NRT)` | 63 |
| B1.NPT | `len(B4 packets)` | 30 |
| B1.NOP | `len(B5 params)` | 63 |
| B1.NOS | `len(B3.SI)` | 6 |
| B3.SP[0] | Always 1 | 1 |
| B3.SP[i] | `SP[i-1] + packets_for_slave[i-1]` | [1,10,11,20,21,30] |
| Packets for slave 1 | Count pkts where SID=slave1_address | 9 (6 read + 3 write) |
| Packets for slave 2 | Count pkts where SID=slave2_address | 1 (sensor reads only) |
| P1.NLB | `len(P2.MPI) + len(P2.RPCI)` | 30+9=39 |
| P1.NMD | `len(P3.MPI) + len(P3.LBI)` | 42+9=51 |
| JKA NMD check | `sum(len(keys)*len(names) for JKA)` | 51 |
| P2.LBI | Always [1..NLB] | [1..39] |
| P3.MDI | Always [1..NMD] | [1..51] |
| B6.WP params | All have FC 5 or 6 | [16,17,18,37,38,39,58,59,60] |
| B6.RP params | All have FC 1-4 | [9,10,14,30,31,35,51,52,56] |
| Reg[] offset pkt 1 | 0 (always) | 0 |
| Reg[] offset pkt 2 | `NRT[0]` | 8 |
| Reg[] offset pkt k | `sum(NRT[0..k-2])` | pkt3=10, pkt4=11, pkt10=22 |

---

## Appendix B — LBI Slot Assignment Example (TFA_15_16_17)

The complete LBI slot assignment and the Lua device tables it produces for the TFA_15_16_17 project. **This is a project-specific example, not a fixed layout.** For a different project (e.g., 2 AHU units with a damper and a fan), the LBI slots would be different — but the assignment algorithm (Phase 1 → Phase 2 → Phase 3) always follows the same rules.

For TFA (3 devices × 3 write registers each with Link B, + 12 read-only registers, + 9 NVS slots):

```
Phase 1 - Write + Hardware Feedback pairs:
  LBI  1 -> Valve Write  TFA15 (param 16, FC6 @ addr 4066)
  LBI  2 -> Valve FB     TFA15 (param 12, FC3 @ addr 1561) <- Link B from engineer
  LBI  3 -> Fan Write    TFA15 (param 17, FC6 @ addr 4067)
  LBI  4 -> Fan FB       TFA15 (param 11, FC4 @ addr 4067) <- Link B
  LBI  5 -> Enable Write TFA15 (param 18, FC5 @ addr 301)
  LBI  6 -> Enable FB    TFA15 (param 15, FC2 @ addr 301)  <- Link B
  LBI  7 -> Valve Write  TFA16 (param 37)
  LBI  8 -> Valve FB     TFA16 (param 33)
  LBI  9 -> Fan Write    TFA16 (param 38)
  LBI 10 -> Fan FB       TFA16 (param 32)
  LBI 11 -> Enable Write TFA16 (param 39)
  LBI 12 -> Enable FB    TFA16 (param 36)
  LBI 13 -> Valve Write  TFA17 (param 58)
  LBI 14 -> Valve FB     TFA17 (param 54)
  LBI 15 -> Fan Write    TFA17 (param 59)
  LBI 16 -> Fan FB       TFA17 (param 53)
  LBI 17 -> Enable Write TFA17 (param 60)
  LBI 18 -> Enable FB    TFA17 (param 57)

Lua device tables generated from Phase 1:
  Valve[Write]   = {[TFA15]=1,  [TFA16]=7,  [TFA17]=13}
  Valve[Stat]    = {[TFA15]=2,  [TFA16]=8,  [TFA17]=14}
  ECFan[Write]   = {[TFA15]=3,  [TFA16]=9,  [TFA17]=15}
  ECFan[Stat]    = {[TFA15]=4,  [TFA16]=10, [TFA17]=16}
  ECFan[EnWrite] = {[TFA15]=5,  [TFA16]=11, [TFA17]=17}
  ECFan[EnStat]  = {[TFA15]=6,  [TFA16]=12, [TFA17]=18}

Phase 2 - Read-only registers:
  LBI 19 -> param 5  (TFA15 AM coil)
  LBI 20 -> param 20 (TFA15 RAT sensor)  <- SEN[Stat][TFA15] = 20 in Lua
  LBI 21 -> param 26 (TFA15 ...)
  LBI 22 -> param 41 (TFA16 RAT)         <- SEN[Stat][TFA16] = 22
  LBI 23 -> param 47 (TFA16 ...)
  LBI 24 -> param 62 (TFA17 RAT)         <- SEN[Stat][TFA17] = 24
  LBI 25 -> param 2  (TFA15 ON coil)
  LBI 26 -> param 23 (TFA16)
  LBI 27 -> param 44 (TFA17)
  LBI 28 -> param 1  (TFA15 OFF coil)
  LBI 29 -> param 22 (TFA16)
  LBI 30 -> param 43 (TFA17)

Phase 3 - NVS-backed slots (go to P2.RPCI, not MPI):
  LBI 31 -> NVS key "STP15"  | LBI table: LBI[1]=31
  LBI 32 -> NVS key "BMS15"  | LBI table: LBI[2]=32
  LBI 33 -> NVS key "STP16"  | LBI table: LBI[3]=33
  LBI 34 -> NVS key "BMS16"  | LBI table: LBI[4]=34
  LBI 35 -> NVS key "STP17"  | LBI table: LBI[5]=35
  LBI 36 -> NVS key "BMS17"  | LBI table: LBI[6]=36
  LBI 37 -> NVS key "VALR15" | LBI table: LBI[7]=37
  LBI 38 -> NVS key "VALR16" | LBI table: LBI[8]=38
  LBI 39 -> NVS key "VALR17" | LBI table: LBI[9]=39

Generated Lua LBI table:
  LBI = {[1]=31,[2]=32,[3]=33,[4]=34,[5]=35,[6]=36,[7]=37,[8]=38,[9]=39}
```

---

*Document version: 1.0 | Date: 2026-05-03 | Reference project: TFA_15_16_17*

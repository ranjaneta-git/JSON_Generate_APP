# BMIoT Config Tool v2.0 — Visual Step-by-Step Guide

**Application Version:** 2.0  
**Who this is for:** Anyone who wants to understand the complete flow from  
"engineer fills in fields" → "app produces Modbus_Config.json + ParamMap_Config.json + Lua files"

> **About the examples:** Parts 2–3 use the **TFA_15_16_17** project (3 TFA air-handling units,  
> 6 Modbus slaves, 63 registers) as a concrete illustration. The algorithms and rules shown  
> apply identically to **any configuration** — 1 device or 10, any device type, any register layout.

---

## PART 1 — THE BIG PICTURE

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        WHAT THE ENGINEER KNOWS                                 ║
║                                                                                  ║
║   • Device register addresses (from datasheet)                                  ║
║   • Which registers to read vs. write                                           ║
║   • Which registers appear on cloud dashboard                                   ║
║   • What the device physically controls (valve, fan, sensor...)                 ║
╚══════════════════════════════════════════════════════════════════════════════════╝
                                       │
                                       ▼
╔══════════════════════════════════════════════════════════════════════════════════╗
║                           8-STEP WIZARD UI                                      ║
║                                                                                  ║
║  Step 1        Step 2        Step 3        Step 4        Step 5                 ║
║  Project    →  Devices    →  Registers  →  Connect   →  Cloud                  ║
║  Setup         & Slaves       Entry        Registers     Output                 ║
║                                                                                  ║
║  Step 6        Step 7        Step 8                                             ║
║  Actions    →  NVS        →  Review &                                          ║
║  Commands      Setpoints     Generate                                           ║
╚══════════════════════════════════════════════════════════════════════════════════╝
                                       │
                                       ▼
╔══════════════════════════════════════════════════════════════════════════════════╗
║                        GENERATION ENGINE                                        ║
║                                                                                  ║
║  BUILD ORDER for Modbus_Config.json:                                            ║
║  ─────────────────────────────────                                              ║
║  B2 → B3-SI → B4 → B3-SP → B5 → B6 → B1                                       ║
║                                                                                  ║
║  BUILD ORDER for ParamMap_Config.json:                                          ║
║  ──────────────────────────────────────                                         ║
║  JKA → JKC → NTC → MST → P2 → P3 → P1                                         ║
╚══════════════════════════════════════════════════════════════════════════════════╝
                                       │
                                       ▼
╔══════════════════════════════════════════════════════════════════════════════════╗
║                          OUTPUT FILES                                           ║
║                                                                                  ║
║   Modbus_Config.json   ParamMap_Config.json   MainScript.lua   FuncScript.lua   ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## PART 2 — WHAT THE ENGINEER ENTERS AT EACH STEP

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 1 — PROJECT SETUP                                                          │
│                                                                                 │
│  Engineer types:          Example value:        Goes into:                      │
│  ─────────────────────    ──────────────────    ─────────────────               │
│  Gateway Device ID        "GW01"               NTC.DI                          │
│  Machine ID               "GWAY01"             NTC.MI[0]                        │
│  Baud Rate                19200                B2.BR                            │
│  Serial Format            "8E1"                B2.DF                            │
│  MQTT Publish Topic       "NBTST"              Config file                      │
│  MQTT Subscribe           "S_NBTST1"           Config file                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 2 — ADD DEVICES  (any number of devices, any type)                        │
│                                                                                 │
│  For each physical device the engineer adds:                                    │
│                                                                                 │
│  Device Name     Slave 1 Addr    Slave 2 Addr    Order (drag)                  │
│  ─────────────   ────────────    ────────────    ────────────                  │
│  (any name)      any 1–247       any 1–247       any order                     │
│                                                                                 │
│  ★ TFA_15_16_17 example:                                                       │
│     "TFA15"         1 (Main)        2 (Sensor)      1st → lua_index = 1       │
│     "TFA16"         3 (Main)        4 (Sensor)      2nd → lua_index = 2       │
│     "TFA17"         5 (Main)        6 (Sensor)      3rd → lua_index = 3       │
│                                                                                 │
│  ★ Device ORDER matters (regardless of device count):                          │
│    → Sets Lua constants: Device1=1, Device2=2, Device3=3 ...                  │
│    → Sets the LBI slot assignment order (Phase 1 pairs)                        │
│    → Sets the Aid (Action ID) sequencing                                        │
│                                                                                 │
│  Each device can have 1..M slaves (sensor boards, sub-modules, etc.)            │
│  Templates pre-fill registers for known device types (TFA, AHU, VFD, etc.)     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 3 — ADD REGISTERS  (any device type, any register map)                    │
│                                                                                 │
│  For each register the engineer fills in:                                       │
│                                                                                 │
│  Name           Slave   Addr   FC   Direction   Format    Scale   Unit  Cluster │
│  ────────────   ─────   ────   ──   ─────────   ──────    ─────   ────  ─────── │
│  any label      any     any    any  any         any       any     any   any     │
│                                                                                 │
│  ★ TFA_15_16_17 example values (register map from TFA device datasheet):       │
│                                                                                 │
│  "Valve Write"  Main    4066    6   Write        UINT16   ×1      -    Valve   │
│  "Valve Echo"   Main    4066    3   Read         UINT16   ×1      -    -       │
│  "Valve FB"     Main    1561    3   Read         UINT16   ×0.1    %    -       │
│  "Fan Write"    Main    4067    6   Write        UINT16   ×1      -    ECFan   │
│  "Fan FB"       Main    4067    4   Read         UINT16   ×0.1    %    -       │
│  "Enable Write" Main     301    5   Write        UINT16   ×1      -    ECFan   │
│  "Enable FB"    Main     301    2   Read         UINT16   ×1      -    -       │
│  "Coil 1-8"     Main    1-8     1   Read         UINT16   ×1      -    -       │
│  "RAT Sensor"   Sensor  1561    3   Read         UINT16   ×0.01   °C   SEN     │
│  ... (repeat for TFA16, TFA17)                                                 │
│                                                                                 │
│  CLUSTER NAME: Engineer assigns write registers to named groups                │
│    "Valve" = the valve position cluster                                         │
│    "ECFan" = the EC fan cluster                                                 │
│    "SEN"   = sensor read-only registers                                         │
│    (For an AHU project: "Damper", "Fan", "Heater" etc.)                        │
│                                                                                 │
│  ★ ORDER the engineer adds registers = B4 packet grouping order                │
│  ★ App shows ORANGE rows for Write, BLUE for Read, GREEN for NVS               │
│  ★ If Write addr matches a Read addr at same FC pair → Blue info hint shown    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 4 — CONNECT REGISTERS  (The Most Important Step)                          │
│                                                                                 │
│  For every WRITE register, engineer answers TWO questions:                      │
│                                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │ VALVE WRITE (FC6 @ addr 4066)                                          │    │
│  │                                                                        │    │
│  │  LINK A — Firmware verify register (B6 pair)                          │    │
│  │  Q: "Which read register confirms this write was accepted?"           │    │
│  │  [AUTO-DETECTED] → "Valve Echo" (FC3 @ addr 4066, same address)       │    │
│  │                                                                        │    │
│  │  LINK B — Hardware feedback register (P2 LBI pair)                    │    │
│  │  Q: "Which register shows the actual physical position?"              │    │
│  │  [ENGINEER PICKS] → "Valve FB" (FC3 @ addr 1561, different address)   │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│  Link A auto-detect rule:                                                       │
│    FC6 write @ addr X → look for FC3 read @ same addr X = Link A partner       │
│    FC5 write @ addr X → look for FC1 read @ same addr X = Link A partner       │
│                                                                                 │
│  Link B = always manual (only the engineer knows from the datasheet)            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 5 — CLOUD OUTPUT ASSIGNMENT  (any cloud structure)                        │
│                                                                                 │
│  For each register to publish to cloud, engineer sets:                          │
│                                                                                 │
│  Register         Cloud Group      Device Label    Property Key   Order        │
│  ──────────────   ──────────────   ────────────    ────────────   ─────        │
│  (any register)   (any group name) (any label)     (any key)      (drag order) │
│                                                                                 │
│  ★ TFA_15_16_17 example:                                                       │
│  "Valve FB"       "TFA15_AIE1"     "valve_Fb"      "per"          1            │
│  "Fan FB"         "TFA15_AIE1"     "EC_Fan_Fb"     "per"          2            │
│  "Enable Stat"    "TFA15_DOE1"     "EC_Fan_En"     "St"           3            │
│  "RAT Sensor"     "TFA15_AIE3"     "RAT"           "DegC"         4            │
│  "OFF coil"       "TFA15_DIE1"     "OFF"           "St"           5            │
│  ...                                                                            │
│                                                                                 │
│  ★ ORDER of cloud groups (drag-to-reorder panel) = JKA order = P3.MPI order   │
│  ★ App shows live JSON preview on the right side                                │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 6 — ACTION COMMANDS  (general — any write register, any device type)      │
│                                                                                 │
│  For each write register controlled from cloud, engineer sets:                  │
│                                                                                 │
│  Register         Aid   Control Type              Input Range   Raw Range       │
│  ──────────────   ───   ─────────────────────     ───────────   ─────────       │
│  (any write reg)  N     Direct write              any           any             │
│  (with Link B)    N     Write with HW feedback    any           any             │
│  (NVS-backed)     N     NVS-persisted setpoint    raw           raw             │
│  (NVS mode)       N     NVS-persisted mode        raw           raw             │
│  (special)        N     Firmware sequence         depends on function           │
│                                                                                 │
│  ★ TFA_15_16_17 example:                                                       │
│  "Valve Write"    1     Write with HW feedback    0–100%        0–1000         │
│  "Fan Write"      2     Write with HW feedback    0–100%        0–1000         │
│  "Enable Write"   3     Direct write              0 or 1        0 or 1         │
│  (NVS setpoint)   10    NVS-persisted setpoint    raw           raw             │
│  (NVS BMS mode)   13    NVS-persisted mode        raw           raw             │
│  (Valve tracker)  16    Firmware sequence         1/0           1/0             │
│                                                                                 │
│  ★ Aid numbers auto-assigned in order, can be overridden                        │
│  ★ Lua function is chosen automatically from control type + Link B presence     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STEP 7 — NVS / SETPOINTS  (any NVS key, any default, any device type)          │
│                                                                                 │
│  For each NVS-backed value:                                                     │
│                                                                                 │
│  Purpose             NVS Key    Default   Publish to Cloud?                    │
│  ─────────────────   ────────   ───────   ─────────────────                   │
│  (any purpose)       ≤15 chars  any       yes/no                               │
│                                                                                 │
│  ★ TFA_15_16_17 example:                                                       │
│  TFA15 Setpoint      "STP15"    250       Yes → LBI 31                         │
│  TFA15 BMS Mode      "BMS15"    0         Yes → LBI 32                         │
│  TFA16 Setpoint      "STP16"    250       Yes → LBI 33                         │
│  TFA17 Setpoint      "STP17"    250       Yes → LBI 35                         │
│  TFA15 Valve Track   "VALR15"   0         Yes → LBI 37                         │
│  ...                                                                            │
│                                                                                 │
│  ★ NVS key must be <= 15 characters (ESP32 limit)                               │
│  ★ These become P2.RPCI entries and P3.LBI entries                              │
│  ★ NVS LBI slots are assigned AFTER all Modbus-backed LBI slots are filled     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## PART 3 — ENGINE: HOW THE APP BUILDS EACH JSON SECTION

### STAGE 1 — START WITH B2 AND B3-SI  (Simplest, no dependencies)

```
Engineer entered: Baud=19200, Format="8E1"        ← from Step 1 (TFA example values)
                  Devices: TFA15(slaves 1,2), TFA16(slaves 3,4), TFA17(slaves 5,6)
                  ← from Step 2 (TFA has 3 devices × 2 slaves; other projects differ)
                  ┌─────────────────┐        ┌──────────────────────────────────┐
                  │   B2 (Serial)   │        │   B3.SI (Slave ID list)          │
                  │                 │        │                                  │
                  │  BR: 19200      │        │  Walk devices in order:          │
                  │  DF: "8E1"      │        │  TFA15.slave1 = 1                │
                  │                 │        │  TFA15.slave2 = 2                │
                  │  ← copied from  │        │  TFA16.slave1 = 3                │
                  │    Step 1 data  │        │  TFA16.slave2 = 4                │
                  └─────────────────┘        │  TFA17.slave1 = 5                │
                                             │  TFA17.slave2 = 6                │
                                             │                                  │
                                             │  Result: SI = [1,2,3,4,5,6]     │
                                             └──────────────────────────────────┘
```

---

### STAGE 2 — BUILD B4 PACKETS  (Most critical step — everything depends on this)

**Input:** All register entries from Step 3, in the order the engineer added them.

```
THE PACKET GROUPING DECISION TREE
(Applied to every consecutive pair of registers for the same slave)

                         ┌──────────────────────────────────┐
                         │  Take next register in entry order│
                         └──────────────────────────────────┘
                                          │
                         ┌───────────────▼───────────────────┐
                         │  Is there a current open packet?   │
                         └──────────────────────────────────-─┘
                           No │                      Yes │
                              ▼                          ▼
                     ┌─────────────────┐    ┌──────────────────────────────┐
                     │  Start new      │    │  Check 3 conditions:         │
                     │  packet with    │    │                              │
                     │  this register  │    │  A. Same FC as packet?       │
                     └─────────────────┘    │  B. Address contiguous?      │
                                            │     next.addr ==             │
                                            │     prev.addr + prev.LN      │
                                            │  C. would-be NRT <= 60?      │
                                            │     (next.addr - pkt.SA      │
                                            │      + next.LN) <= 60        │
                                            └──────────────────────────────┘
                                                         │
                                    ┌────────────────────┤
                               ALL 3│                    │ANY fails
                                TRUE▼                    ▼
                          ┌──────────────┐   ┌───────────────────────────┐
                          │ EXTEND this  │   │ CLOSE current packet      │
                          │ packet:      │   │ (save SA, NRT, FC, SID)   │
                          │ NRT grows    │   │                           │
                          │ by reg.LN    │   │ START new packet with     │
                          └──────────────┘   │ this register             │
                                             └───────────────────────────┘

CONDITION A FAILS (FC mismatch):
  Example: prev was FC3, next is FC4 → new packet

CONDITION B FAILS (address gap):
  Example: prev was addr 4067, next is addr 1561 → new packet

CONDITION C FAILS (size limit):
  Example: current NRT=58, next.LN=3 → would be 61 → exceeds 60 → new packet
```

**READ PACKETS BEFORE WRITE PACKETS — always:**

```
For each slave:

  ┌──────────────────────────────────────────────────────────────────────┐
  │  SCAN 1: Only registers with FC 1/2/3/4 (READ FCs)                  │
  │          Apply grouping decision tree above                          │
  │          → Produces read packets in engineer entry order            │
  └──────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ appended after
  ┌──────────────────────────────────────────────────────────────────────┐
  │  SCAN 2: Only registers with FC 5/6 (WRITE FCs)                     │
  │          Each write register → ONE individual packet (never grouped) │
  │          → Produces write packets in engineer entry order           │
  └──────────────────────────────────────────────────────────────────────┘

  WHY reads first?
  → Firmware Reg[] buffer is laid out: all read values first, then write slots
  → Write packets at the end ensures write param IDs are always the highest
    numbers in their slave block — which the Lua device tables rely on
```

**TFA Example — Slave 1 packet building:**

```
Engineer's register entry order for slave 1 (Main, addr=1):
 ┌───┬──────────────────┬──────┬─────┬──────┐
 │ # │ Name             │ Addr │ FC  │ LN   │
 ├───┼──────────────────┼──────┼─────┼──────┤
 │ 1 │ Coil OFF         │    1 │ FC1 │  1   │  ← read
 │ 2 │ Coil ON          │    2 │ FC1 │  1   │  ← read
 │ 3 │ Coil TRIP        │    3 │ FC1 │  1   │  ← read
 │ 4 │ Coil FIRE        │    4 │ FC1 │  1   │  ← read
 │ 5 │ Coil AM          │    5 │ FC1 │  1   │  ← read
 │ 6 │ Coil DPS         │    6 │ FC1 │  1   │  ← read
 │ 7 │ Coil Fire_Pu     │    7 │ FC1 │  1   │  ← read
 │ 8 │ Coil Fire_damp   │    8 │ FC1 │  1   │  ← read
 │ 9 │ Valve Echo 1     │ 4066 │ FC3 │  1   │  ← read (FC changed from FC1)
 │10 │ Valve Echo 2     │ 4067 │ FC3 │  1   │  ← read
 │11 │ Fan Analog FB    │ 4067 │ FC4 │  1   │  ← read (FC changed from FC3)
 │12 │ Valve FB         │ 1561 │ FC3 │  1   │  ← read (FC changed from FC4)
 │13 │ Valve Echo copy  │ 1562 │ FC3 │  1   │  ← read (same FC, contiguous)
 │14 │ Enable Coil Read │  301 │ FC1 │  1   │  ← read (FC changed from FC3)
 │15 │ Discrete FB      │  301 │ FC2 │  1   │  ← read (FC changed from FC1)
 │16 │ Valve Write      │ 4066 │ FC6 │  1   │  ← WRITE
 │17 │ Fan Write        │ 4067 │ FC6 │  1   │  ← WRITE
 │18 │ Enable Write     │  301 │ FC5 │  1   │  ← WRITE
 └───┴──────────────────┴──────┴─────┴──────┘

GROUPING SCAN — Read registers only (rows 1–15):

  Reg 1 (FC1, addr 1):  → open pkt-A
  Reg 2 (FC1, addr 2):  A. FC1=FC1 ✓  B. 2=1+1 ✓  C. NRT=2≤60 ✓  → extend pkt-A
  Reg 3 (FC1, addr 3):  ✓ ✓ ✓ → extend pkt-A
  ... (regs 4-8 same) ...
  Reg 8 (FC1, addr 8):  ✓ ✓ ✓ → extend pkt-A  [pkt-A now: SA=1, NRT=8]
  
  Reg 9 (FC3, addr 4066):  A. FC3≠FC1 ✗ → close pkt-A, open pkt-B
  Reg 10 (FC3, addr 4067):  A. FC3=FC3 ✓  B. 4067=4066+1 ✓  C. NRT=2≤60 ✓  → extend pkt-B
                             [pkt-B now: SA=4066, NRT=2]
  
  Reg 11 (FC4, addr 4067):  A. FC4≠FC3 ✗ → close pkt-B, open pkt-C
                             [pkt-C: SA=4067, NRT=1]
  
  Reg 12 (FC3, addr 1561):  A. FC3≠FC4 ✗ → close pkt-C, open pkt-D
  Reg 13 (FC3, addr 1562):  A. FC3=FC3 ✓  B. 1562=1561+1 ✓  C. NRT=2≤60 ✓  → extend pkt-D
                             [pkt-D: SA=1561, NRT=2]
  
  Reg 14 (FC1, addr 301):   A. FC1≠FC3 ✗ → close pkt-D, open pkt-E
                             [pkt-E: SA=301, NRT=1]
  
  Reg 15 (FC2, addr 301):   A. FC2≠FC1 ✗ → close pkt-E, open pkt-F
                             [pkt-F: SA=301, NRT=1]  ← end of reads, close pkt-F

WRITE scan (rows 16–18) — one packet each:
  Reg 16 (FC6, addr 4066): pkt-G = {SA=4066, NRT=1, FC=6}
  Reg 17 (FC6, addr 4067): pkt-H = {SA=4067, NRT=1, FC=6}
  Reg 18 (FC5, addr  301): pkt-I = {SA=301,  NRT=1, FC=5}

Final slave-1 packets (global numbers assigned):
  ┌─────┬────┬──────┬─────┬──────┐
  │ Pkt │ FC │  SA  │ NRT │  SID │
  ├─────┼────┼──────┼─────┼──────┤
  │  1  │  1 │    1 │   8 │   1  │  ← reads pkt A
  │  2  │  3 │ 4066 │   2 │   1  │  ← reads pkt B
  │  3  │  4 │ 4067 │   1 │   1  │  ← reads pkt C
  │  4  │  3 │ 1561 │   2 │   1  │  ← reads pkt D
  │  5  │  1 │  301 │   1 │   1  │  ← reads pkt E
  │  6  │  2 │  301 │   1 │   1  │  ← reads pkt F
  │  7  │  6 │ 4066 │   1 │   1  │  ← write pkt G
  │  8  │  6 │ 4067 │   1 │   1  │  ← write pkt H
  │  9  │  5 │  301 │   1 │   1  │  ← write pkt I
  └─────┴────┴──────┴─────┴──────┘
```

**B3.SP is calculated NOW (after B4 is complete):**

```
packets_per_slave = [9, 1, 9, 1, 9, 1]
                     ↑         ↑
                  TFA15      TFA16
                  main       main
                  (9pkts)    (9pkts)

SP calculation:
  SP[0] = 1              (slave 1 starts at packet 1)
  SP[1] = 1+9 = 10       (slave 2 starts at packet 10)
  SP[2] = 10+1 = 11      (slave 3 starts at packet 11)
  SP[3] = 11+9 = 20      (slave 4 starts at packet 20)
  SP[4] = 20+1 = 21      (slave 5 starts at packet 21)
  SP[5] = 21+9 = 30      (slave 6 starts at packet 30)

  B3 = { SI: [1,2,3,4,5,6], SP: [1,10,11,20,21,30] }
```

---

### STAGE 3 — BUILD B5 PARAMETERS  (Depends on B4 — cannot run before B4)

```
Rule: Walk every packet IN ORDER (pkt 1 → pkt 2 → ... → pkt 30)
      For each packet, assign a param ID to each register it contains.
      Param IDs are sequential: 1, 2, 3, 4, ...

  ┌─────┬─────────────────────────────────────────────────────────────┐
  │ Pkt │ Registers inside (in address order)  → Param IDs assigned  │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  1  │ addr 1 (LN=1), addr 2 (LN=1), ..., addr 8 (LN=1)          │
  │     │ → params 1, 2, 3, 4, 5, 6, 7, 8   (all PN=1)              │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  2  │ addr 4066 (LN=1), addr 4067 (LN=1)                         │
  │     │ → params 9, 10   (both PN=2)                               │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  3  │ addr 4067 (LN=1)                                            │
  │     │ → param 11   (PN=3)   [Fan analog FB, MLT=0.1]             │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  4  │ addr 1561 (LN=1), addr 1562 (LN=1)                         │
  │     │ → params 12, 13   (both PN=4)   [param 12 MLT=0.1]        │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  5  │ addr 301 (LN=1)   → param 14   (PN=5)                     │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  6  │ addr 301 (LN=1)   → param 15   (PN=6)                     │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  7  │ addr 4066 (LN=1)  → param 16   (PN=7)   ← WRITE PARAM     │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  8  │ addr 4067 (LN=1)  → param 17   (PN=8)   ← WRITE PARAM     │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │  9  │ addr 301  (LN=1)  → param 18   (PN=9)   ← WRITE PARAM     │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │ 10  │ (slave 2, sensor)  → params 19, 20, 21  (PN=10)           │
  ├─────┼─────────────────────────────────────────────────────────────┤
  │ ... │  (TFA16 params 22-42, TFA17 params 43-63)                  │
  └─────┴─────────────────────────────────────────────────────────────┘

Each B5 row stores:
  ID  = param number (1-based, sequential)
  PN  = packet number (from B4)
  STA = register address
  LN  = 1 or 2 (data size)
  FMT = data format code
  MLT = scale multiplier
```

---

### STAGE 4 — BUILD B6 WRITE/VERIFY PAIRS  (Depends on B5 — needs param IDs)

```
Source: Link A connections confirmed in Step 4.

For each WRITE register that has a Link A partner:
  WP[i] = write register's param_id   (from B5)
  RP[i] = Link A partner's param_id   (from B5)

  ┌────────────────────────────────────────────────────────────┐
  │  Write Register    │ Link A Partner     │ WP    │ RP       │
  ├────────────────────┼────────────────────┼───────┼──────────┤
  │ Valve Write (FC6   │ Valve Echo (FC3    │  16   │   9      │
  │  @ addr 4066)      │  @ addr 4066)      │       │          │
  │ Fan Write (FC6     │ Fan Echo (FC3      │  17   │  10      │
  │  @ addr 4067)      │  @ addr 4067)      │       │          │
  │ Enable Write (FC5  │ Enable Coil (FC1   │  18   │  14      │
  │  @ addr 301)       │  @ addr 301)       │       │          │
  │ ... TFA16 ...      │                    │ 37,38 │ 30,31    │
  │ ... TFA17 ...      │                    │ 58,59 │ 51,52    │
  └────────────────────┴────────────────────┴───────┴──────────┘

  B6 = { WP: [16,17,18, 37,38,39, 58,59,60],
          RP: [ 9,10,14, 30,31,35, 51,52,56] }

  ★ WP[i] and RP[i] are ALWAYS index-paired.
    Never reorder WP or RP independently of each other.
```

---

### STAGE 5 — BUILD B1 COUNTS  (Always last for Modbus — needs B3, B4, B5)

```
  ┌─────────────────────────────────────────────────────────────────┐
  │  B1 field │ Formula                    │ TFA result             │
  ├───────────┼────────────────────────────┼────────────────────────┤
  │  NOS      │ len(B3.SI)                 │ 6 (6 slaves)           │
  │  NPT      │ count of B4 packets        │ 30 (30 packets)        │
  │  NOP      │ count of B5 param IDs      │ 63 (63 params)         │
  │  NOR      │ SUM of all B4.NRT values   │ 63 (sum of all NRTs)   │
  └───────────┴────────────────────────────┴────────────────────────┘

  Validation check (run before writing file):
    NOR == sum(NRT)?     63 == 63 ✓
    NPT == count(pkts)?  30 == 30 ✓
    NOP == count(B5)?    63 == 63 ✓

  B1 = { NOS:6, NOP:63, NPT:30, NOR:63 }

  ╔═══════════════════════════════╗
  ║  Modbus_Config.json COMPLETE  ║
  ╚═══════════════════════════════╝
```

---

### STAGE 6 — BUILD JKA  (Start of ParamMap — needs Step 5 cloud assignments)

```
Input: All registers where cloud_enabled = True, in cloud_order sequence.

Grouping logic:
  Registers with same Cloud Group → same JKA entry
  Different Cloud Groups → different JKA entries

  ┌──────────────────────────────────────────────────────────────────────┐
  │ Cloud assignments (in engineer's drag-order):                        │
  │                                                                      │
  │ order  Cloud Group          Device Label    Key                      │
  │ ─────  ─────────────────    ────────────    ─────                    │
  │   1    "TFA15_DIE1"         "OFF"           "St"                     │
  │   2    "TFA15_DIE1"         "ON"            "St"    ← same group!    │
  │   3    "TFA15_DIE1"         "AM"            "St"    ← same group!    │
  │   4    "TFA15_DIE1"         "Fire_Pu"       "St"    ← same group!    │
  │   5    "TFA15_DIE1"         "Fire_damp"     "St"    ← same group!    │
  │   6    "TFA15_DIE1_Trip"    "Trip"          "Tr"    ← new group      │
  │   7    "TFA15_DIE1_Fire"    "Fire"          "Ar"    ← new group      │
  │   8    "TFA15_AIE1"         "valve_Fb"      "per"   ← new group      │
  │   9    "TFA15_AIE1"         "EC_Fan_Fb"     "per"   ← same group!    │
  │  10    "TFA15_DOE1"         "EC_Fan_Enable" "St"    ← new group      │
  │  ...                                                                 │
  └──────────────────────────────────────────────────────────────────────┘

                              ▼  group and collect

  JKA array built:
  ┌─────┬───────────────────────┬──────────┬───────────────────────────┐
  │ [0] │ "TFA15_DIE1"          │ ["St"]   │ ["OFF","ON","AM","Fire_Pu"│
  │     │                       │          │  ,"Fire_damp"]            │
  │     │  M_data slots used:   │          │  1 key × 5 names = 5 slots│
  ├─────┼───────────────────────┼──────────┼───────────────────────────┤
  │ [1] │ "TFA15_DIE1_Trip"     │ ["Tr"]   │ ["Trip"]   → 1 slot       │
  ├─────┼───────────────────────┼──────────┼───────────────────────────┤
  │ [2] │ "TFA15_DIE1_Fire"     │ ["Ar"]   │ ["Fire"]   → 1 slot       │
  ├─────┼───────────────────────┼──────────┼───────────────────────────┤
  │ [3] │ "TFA15_DIE1_DPS"      │ ["Ar"]   │ ["DPS"]    → 1 slot       │
  ├─────┼───────────────────────┼──────────┼───────────────────────────┤
  │ [4] │ "TFA15_AIE1"          │ ["per"]  │ ["valve_Fb","EC_Fan_Fb"]  │
  │     │                       │          │  1 key × 2 names = 2 slots│
  ├─────┼───────────────────────┼──────────┼───────────────────────────┤
  │ [5] │ "TFA15_DOE1"          │ ["St"]   │ ["EC_Fan_Enable"] → 1slot │
  ├─────┴───────────────────────┴──────────┴───────────────────────────┤
  │  ... (continues for TFA16, TFA17 groups) ...                       │
  ├────────────────────────────────────────────────────────────────────┤
  │  TOTAL slots consumed = Σ(keys × names) = 51 → this MUST = NMD    │
  └────────────────────────────────────────────────────────────────────┘
```

---

### STAGE 7 — BUILD P2.MPI (LBI Slot Assignment — 3 Phases)

```
This determines WHICH B5 param lives at WHICH LBI slot number in Lua.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1: Write + Hardware Feedback PAIRS  (from Link B connections)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pattern for each device:  [write_param, its_Link_B_feedback_param, next_write, ...]

  For device TFA15 (in engineer's register entry order):
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Write: Valve Write  (param 16)  → LBI slot 1                       │
  │  Link B: Valve FB    (param 12)  → LBI slot 2  ← hardware feedback  │
  │  Write: Fan Write    (param 17)  → LBI slot 3                       │
  │  Link B: Fan FB      (param 11)  → LBI slot 4                       │
  │  Write: Enable Write (param 18)  → LBI slot 5                       │
  │  Link B: Discrete FB (param 15)  → LBI slot 6                       │
  └──────────────────────────────────────────────────────────────────────┘
  P2.MPI so far: [16, 12, 17, 11, 18, 15]

  For device TFA16 (same pattern, param numbers +21):
  → LBI slots 7–12 | P2.MPI += [37,33, 38,32, 39,36]

  For device TFA17 (param numbers +42):
  → LBI slots 13–18 | P2.MPI += [58,54, 59,53, 60,57]

  LBI slots 1–18 now assigned. This creates the Lua device tables:
  ┌────────────────────────────────────────────────────────────────────┐
  │  Valve[Write]   = {TFA15=1,  TFA16=7,  TFA17=13}  ← write slots  │
  │  Valve[Stat]    = {TFA15=2,  TFA16=8,  TFA17=14}  ← FB slots     │
  │  ECFan[Write]   = {TFA15=3,  TFA16=9,  TFA17=15}                 │
  │  ECFan[Stat]    = {TFA15=4,  TFA16=10, TFA17=16}                 │
  │  ECFan[EnWrite] = {TFA15=5,  TFA16=11, TFA17=17}                 │
  │  ECFan[EnStat]  = {TFA15=6,  TFA16=12, TFA17=18}                 │
  └────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2: Read-only registers (not already assigned in Phase 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Walk devices in order. Skip any register that already has an LBI slot.
  Append remaining read registers to P2.MPI.

  ┌──────────────────────────────────────────────────────────────────────┐
  │  TFA15 param 5  (AM coil, no write partner)  → LBI slot 19          │
  │  TFA15 param 20 (RAT sensor)                 → LBI slot 20          │
  │  TFA15 param 26                               → LBI slot 21          │
  │  TFA16 param 41 (RAT sensor)                 → LBI slot 22          │
  │  ... etc ...                                                         │
  │  TFA17 param 43 (OFF coil)                   → LBI slot 30          │
  └──────────────────────────────────────────────────────────────────────┘
  P2.MPI now has 30 entries. LBI slots 1–30 filled.

  SEN Lua table is generated from Phase 2:
  SEN[Stat] = {TFA15=20, TFA16=22, TFA17=24}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3: NVS-backed slots  → P2.RPCI  (not MPI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  NVS slots from Step 7, in the order engineer entered them:
  ┌──────────────────────────────────────────────────────────────────────┐
  │  NVS key "STP15"  → RPCI index 1 → LBI slot 31                     │
  │  NVS key "BMS15"  → RPCI index 2 → LBI slot 32                     │
  │  NVS key "STP16"  → RPCI index 3 → LBI slot 33                     │
  │  NVS key "BMS16"  → RPCI index 4 → LBI slot 34                     │
  │  NVS key "STP17"  → RPCI index 5 → LBI slot 35                     │
  │  NVS key "BMS17"  → RPCI index 6 → LBI slot 36                     │
  │  NVS key "VALR15" → RPCI index 7 → LBI slot 37                     │
  │  NVS key "VALR16" → RPCI index 8 → LBI slot 38                     │
  │  NVS key "VALR17" → RPCI index 9 → LBI slot 39                     │
  └──────────────────────────────────────────────────────────────────────┘
  P2.RPCI = [1,2,3,4,5,6,7,8,9]

  Lua LBI table generated from Phase 3:
  LBI = { [1]=31, [2]=32, [3]=33, [4]=34, [5]=35,
          [6]=36, [7]=37, [8]=38, [9]=39 }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL P2:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LBI  = [1,2,3,...,39]          (always sequential 1..NLB)
  MPI  = [16,12,17,11,18,15,     (Phase 1: 18 write+FB pairs)
          37,33,38,32,39,36,
          58,54,59,53,60,57,
          5,20,26,41,47,62,      (Phase 2: 12 read-only)
          2,23,44,1,22,43]
  RPCI = [1,2,3,4,5,6,7,8,9]   (Phase 3: 9 NVS slots)
```

---

### STAGE 8 — BUILD P3.MPI  (The JKA → M_data mapping)

```
★ CRITICAL RULE: P3.MPI order MUST match the JKA consumption order exactly.
  Any mismatch = wrong values published to cloud for every device.

HOW TO READ THIS DIAGRAM:
  Left side = JKA entries in order.
  Right side = the B5 param IDs that go into P3.MPI, one per M_data slot.
  The arrows show which register fills each slot.

  JKA entry                     │  P3.MPI slot   │  Param ID
  ──────────────────────────────┼────────────────┼──────────
  ["TFA15_DIE1",["St"],         │                │
    ["OFF","ON","AM",           │ MPI[0]         │  1   ← "OFF" coil
     "Fire_Pu","Fire_damp"]]    │ MPI[1]         │  2   ← "ON" coil
                                │ MPI[2]         │  5   ← "AM" coil (not 3!)
                                │ MPI[3]         │  7   ← "Fire_Pu"
                                │ MPI[4]         │  8   ← "Fire_damp"
  ──────────────────────────────┼────────────────┼──────────
  ["TFA15_DIE1_Trip",["Tr"],    │ MPI[5]         │  3   ← "Trip" coil
    ["Trip"]]                   │                │
  ──────────────────────────────┼────────────────┼──────────
  ["TFA15_DIE1_Fire",["Ar"],    │ MPI[6]         │  4   ← "Fire" coil
    ["Fire"]]                   │                │
  ──────────────────────────────┼────────────────┼──────────
  ["TFA15_DIE1_DPS",["Ar"],     │ MPI[7]         │  6   ← "DPS" coil
    ["DPS"]]                    │                │
  ──────────────────────────────┼────────────────┼──────────
  ["TFA15_AIE1",["per"],        │ MPI[8]         │ 12   ← valve_Fb
    ["valve_Fb","EC_Fan_Fb"]]   │ MPI[9]         │ 11   ← EC_Fan_Fb
  ──────────────────────────────┼────────────────┼──────────
  ["TFA15_DOE1",["St"],         │ MPI[10]        │ 15   ← EC_Fan_Enable
    ["EC_Fan_Enable"]]          │                │
  ──────────────────────────────┼────────────────┼──────────
  ... (TFA15 AIE3, TFA16, TFA17 continue) ...
  ──────────────────────────────┼────────────────┼──────────
  (end of Modbus params)        │ MPI[41]        │ 63   ← last Modbus param
  ──────────────────────────────┴────────────────┴──────────
  
  NOTE: P3.MPI[2]=5, not 3 or 4, because "AM" is in a different JKA entry
        than "Trip" (param 3) and "Fire" (param 4). The order follows JKA,
        NOT the param_id sequence from B5.

P3.LBI — NVS slots published to cloud:
  All NVS slots with "publish to cloud = yes", in LBI slot order:
  LBI = [31,32,33,34,35,36,37,38,39]   → these come AFTER MPI in the cloud output

P3.MDI — always sequential:
  [1,2,3,...,51]  (just 1..NMD, auto-generated)
```

---

### STAGE 9 — BUILD P1 COUNTS  (Always last for ParamMap)

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  P1 field │ Formula                         │ TFA result            │
  ├───────────┼─────────────────────────────────┼───────────────────────┤
  │  NLB      │ len(P2.MPI) + len(P2.RPCI)      │ 30 + 9 = 39          │
  │  NLBIN    │ same as NLB                      │ 39                    │
  │  NMD      │ len(P3.MPI) + len(P3.LBI)       │ 42 + 9 = 51          │
  └───────────┴─────────────────────────────────┴───────────────────────┘

  Cross-check (CRITICAL):
  Σ(JKA[i].keys × JKA[i].names) = 51  ?  Yes ✓  → safe to generate
                                   = 51  ?  No  ✗  → BLOCK generation, show error

  P1 = { NLB:39, NLBIN:39, NMD:51 }

  ╔═════════════════════════════════╗
  ║  ParamMap_Config.json COMPLETE  ║
  ╚═════════════════════════════════╝
```

---

## PART 4 — LUA FILES: HOW THEY ARE GENERATED

### MainScript.lua Generation Map

```
From Step 2 (devices) + Phase 1 LBI slots + engineer's cluster names (Step 3):

  ┌─────────────────────────────────────────────────────────────────────┐
  │  Device index constants (auto from device order):                   │
  │    (DeviceName) = (lua_index)  ← one constant per device           │
  │                                                                     │
  │  TFA example:  TFA15 = 1   TFA16 = 2   TFA17 = 3                   │
  │                                                                     │
  │  Cluster tables (names = what engineer typed in Step 3):            │
  │    (ClusterName)[(SlotName)] = {[Dev1]=LBI_slot, [Dev2]=LBI_slot}   │
  │                                                                     │
  │  TFA example (engineer used "Valve", "ECFan", "SEN" as names):      │
  │    Valve[Write]   = {[TFA15]=1, [TFA16]=7,  [TFA17]=13}  ← LBI    │
  │    Valve[Stat]    = {[TFA15]=2, [TFA16]=8,  [TFA17]=14}  ← LBI    │
  │    ECFan[Write]   = {[TFA15]=3, [TFA16]=9,  [TFA17]=15}  ← LBI    │
  │    ECFan[Stat]    = {[TFA15]=4, [TFA16]=10, [TFA17]=16}  ← LBI    │
  │    ECFan[EnWrite] = {[TFA15]=5, [TFA16]=11, [TFA17]=17}  ← LBI    │
  │    ECFan[EnStat]  = {[TFA15]=6, [TFA16]=12, [TFA17]=18}  ← LBI    │
  │    SEN[Stat]      = {[TFA15]=20,[TFA16]=22, [TFA17]=24}  ← LBI    │
  │                                                                     │
  │  AHU example (engineer used "Damper", "Fan"):                       │
  │    Damper[Cmd]    = {[AHU1]=1, [AHU2]=5}                           │
  │    Damper[FB]     = {[AHU1]=2, [AHU2]=6}                           │
  │    Fan[Speed]     = {[AHU1]=3, [AHU2]=7}                           │
  │    Fan[Status]    = {[AHU1]=4, [AHU2]=8}                           │
  └─────────────────────────────────────────────────────────────────────┘

From Step 7 (NVS) + Phase 3 LBI slots:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  LBI = {[1]=31,[2]=32,[3]=33,[4]=34,[5]=35,                        │
  │         [6]=36,[7]=37,[8]=38,[9]=39}                               │
  │                                                                     │
  │  NVS_VALR = {[TFA15]="VALR15",[TFA16]="VALR16",[TFA17]="VALR17"} │
  └─────────────────────────────────────────────────────────────────────┘

From Step 7 (NVS restore on boot):
  ┌─────────────────────────────────────────────────────────────────────┐
  │  do                                                                 │
  │    delay(5000)                                                      │
  │    NVS_Read("STP15", 31)   -- restore TFA15 setpoint               │
  │    NVS_Read("BMS15", 32)   -- restore TFA15 BMS mode               │
  │    ...                                                              │
  │    VAL_PS[TFA15] = NVS_GetVal("VALR15")   -- restore valve pos     │
  │    CntrlDev_NoFB2(Valve, TFA15, Write,                             │
  │      Scale_Value(VAL_PS[TFA15], 0,100, 0,1000))                    │
  │  end                                                                │
  └─────────────────────────────────────────────────────────────────────┘

From Step 6 (Action commands):
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Act_Com function:                                                  │
  │  Aid 1  + control type "valve_pos" + Link B present:               │
  │  → Insrt_ActCom2(Aid,Aval,1,Aval,                                  │
  │      Val_Set,Aval,CntrlDev4,Valve,TFA15,Write,Stat,                │
  │      Scale_Value(Aval,0,100,0,1000),Aval,FB_TYM)                   │
  │                                                                     │
  │  Aid 10 + control type "setpoint" + NVS key "STP15":               │
  │  → Insrt_ActCom2(Aid,Aval,10,Aval,                                 │
  │      ValWrt_Pt,Aval,"STP15",LBI[1])                                │
  │                                                                     │
  │  Aid 16 + control type "on_off_sequence":                          │
  │  → Insrt_ActCom2(Aid,Aval,16,1, TFA_Enable,TFA15,1)               │
  │    Insrt_ActCom2(Aid,Aval,16,0, TFA_Enable,TFA15,0)               │
  └─────────────────────────────────────────────────────────────────────┘
```

### Control Type → Lua Function Decision

```
For each action command, app decides the Lua function based on:

  Control Type                   Link B set?     Lua function used
  ─────────────────────          ───────────     ─────────────────────────────────────────
  Direct write                   No              CntrlDev_NoFB2(Cluster, Dev, Write, val)
  Write with hardware feedback   YES             CntrlDev4(Cluster, Dev, Write, Stat, ...)
  NVS-persisted setpoint         N/A (NVS)       ValWrt_Pt(Aval, "NVS_KEY", LBI[n])
  NVS-persisted mode             N/A (NVS)       ValWrt_bm(Aval, "NVS_KEY", LBI[n])
  Firmware sequence              N/A             User-specified Lua function name

  CntrlDev4       = write command + wait + read feedback + check if hardware moved
  CntrlDev_NoFB2  = write command only, no hardware confirmation

  Note: "Cluster" and "Dev" come from the register's cluster_name and the device's
  lua_index. These are NOT hardcoded — they reflect whatever the engineer named
  the clusters in Step 3.
```

---

## PART 5 — DEPENDENCY MAP (What Must Be Built Before What)

```
  ┌──────────┐    ┌──────────┐
  │   B2     │    │  B3-SI   │   ← No dependencies. Built from Step 1 & 2 directly.
  └──────────┘    └──────────┘
                       │
                       ▼
  ╔══════════════════════════════════════════════════════════╗
  ║   B4  — Packet Table                                    ║
  ║   Input: all registers in entry order                   ║
  ║   Rules: same FC + contiguous + NRT ≤ 60 → same packet  ║
  ║          reads first, writes last per slave              ║
  ╚══════════════════════════════════════════════════════════╝
       │                          │
       ▼                          ▼
  ┌──────────┐             ┌────────────────────┐
  │  B3-SP   │             │  B5 — Param Table  │
  │ (depends │             │  Input: B4 packet  │
  │  on B4   │             │  numbers           │
  │  counts) │             │  Output: param IDs │
  └──────────┘             └────────────────────┘
                                    │
                                    ▼
                           ┌────────────────────┐
                           │  B6 — Write/Verify │
                           │  Input: B5 param   │
                           │  IDs + Link A      │
                           └────────────────────┘
                                    │
                                    ▼
  ┌──────────────────────────────────────────────┐
  │  B1 — Counts                                │
  │  Input: B3 (NOS), B4 (NPT + NOR), B5 (NOP) │
  │  ALWAYS LAST for Modbus                     │
  └──────────────────────────────────────────────┘
          │
          │  (Modbus_Config.json done)
          │
          ▼
  ┌──────────────────────────────────────────────┐
  │  JKA — Cloud Hierarchy                       │
  │  Input: Step 5 cloud assignments             │
  │         in engineer's drag order             │
  └──────────────────────────────────────────────┘
       │                          │
       ▼                          ▼
  ┌──────────────────┐    ┌────────────────────────────┐
  │  P2 — LBI slots  │    │  P3 — M_data mapping       │
  │  Input: B5 IDs   │    │  Input: JKA order + B5 IDs │
  │  + Link B pairs  │    │  + NVS LBI slots from P2   │
  │  + NVS from Step7│    │                            │
  └──────────────────┘    └────────────────────────────┘
              │                         │
              └─────────┬───────────────┘
                        ▼
  ┌──────────────────────────────────────────────┐
  │  P1 — Counts                                │
  │  Input: P2 lengths + P3 lengths             │
  │  ALWAYS LAST for ParamMap                   │
  └──────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────┐
  │  JKC / NTC / MST                            │
  │  No dependencies — built from Step 1 data   │
  │  or hardcoded constants                     │
  └──────────────────────────────────────────────┘
```

---

## PART 6 — VALIDATION CHECKLIST (Runs Before "Generate Files")

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                    BLOCKING ERRORS                                   │
  │           (Generation is STOPPED if any of these fail)              │
  ├────┬─────────────────────────────────┬────────────────────────────-─┤
  │ V1 │ B1.NOR == sum(all B4.NRT)       │ "Register count mismatch.    │
  │    │                                 │  Firmware buffer corrupt."   │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V2 │ B1.NPT == count(B4 packets)     │ "Packet count mismatch."     │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V3 │ B1.NOP == count(B5 params)      │ "Param count mismatch."      │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V4 │ P1.NMD == Σ(JKA keys×names)    │ "Cloud count mismatch.       │
  │    │                                 │  Firmware refuses to boot."  │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V5 │ P1.NLB == len(MPI)+len(RPCI)   │ "LBI slot count mismatch."   │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V6 │ P1.NMD == len(P3.MPI)+len(LBI) │ "M_data slot mismatch."      │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V7 │ B6.WP params all have FC 5/6   │ "WP has a read param."       │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V8 │ B6.RP params all have FC 1–4   │ "RP has a write param."      │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ V9 │ All P3.MPI IDs exist in B5     │ "MPI references unknown param"│
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │V10 │ NVS keys ≤ 15 characters        │ "NVS key too long."          │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │V11 │ No duplicate NVS keys           │ "NVS key used twice."        │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │V12 │ B5.LN matches B5.FMT            │ "LN/FMT mismatch."           │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │V13 │ Each device has registers       │ "Device has no registers."   │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │V14 │ All B4.NRT ≤ 60                 │ "Packet too large (>60)."    │
  │    │ (safety net — should never fail │                              │
  │    │  if algorithm is correct)       │                              │
  └────┴─────────────────────────────────┴──────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │                    WARNINGS ONLY                                     │
  │           (Generation proceeds, user is informed)                   │
  ├────┬─────────────────────────────────┬──────────────────────────────┤
  │ W1 │ Write reg missing Link A        │ "Modbus_ParmWrite will fail  │
  │    │                                 │  silently on this register." │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ W2 │ Write reg missing Link B        │ "Using CntrlDev_NoFB2        │
  │    │                                 │  (no hardware check)."       │
  ├────┼─────────────────────────────────┼──────────────────────────────┤
  │ W3 │ Cloud-enabled reg not in P3.MPI │ "Register won't appear in    │
  │    │                                 │  cloud output."              │
  └────┴─────────────────────────────────┴──────────────────────────────┘
```

---

## PART 7 — THE TWO LINKAGE TYPES AT A GLANCE

```
                LINK A — Firmware Verify                LINK B — Hardware Feedback
                (B6 Write/Verify Pair)                  (P2 LBI Pair)
   ┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
   │  PURPOSE:                            │  │  PURPOSE:                            │
   │  Firmware reads back the echo to     │  │  Lua checks if the physical device   │
   │  confirm the Modbus write succeeded  │  │  actually moved to target position   │
   │  at the protocol level               │  │  (may have a time delay)             │
   ├──────────────────────────────────────┤  ├──────────────────────────────────────┤
   │  Same slave, SAME address            │  │  Same device, DIFFERENT address      │
   │  Write: FC6 @ 4066                   │  │  Write: FC6 @ 4066                   │
   │  Verify: FC3 @ 4066  ← same!        │  │  HW FB: FC3 @ 1561  ← different!    │
   ├──────────────────────────────────────┤  ├──────────────────────────────────────┤
   │  AUTO-DETECTED by app                │  │  ALWAYS MANUALLY ENTERED             │
   │  App matches: FC6 addr X             │  │  Engineer checks datasheet and       │
   │          ↔   FC3 addr X             │  │  selects the correct register        │
   ├──────────────────────────────────────┤  ├──────────────────────────────────────┤
   │  GOES INTO: B6.WP and B6.RP          │  │  GOES INTO: P2.MPI interleave pairs  │
   │                                      │  │  Determines Lua device table slots   │
   ├──────────────────────────────────────┤  ├──────────────────────────────────────┤
   │  IF MISSING:                         │  │  IF MISSING:                         │
   │  Modbus_ParmWrite() returns error 2  │  │  App generates CntrlDev_NoFB2        │
   │  Write silently fails on device      │  │  (write without physical check)      │
   └──────────────────────────────────────┘  └──────────────────────────────────────┘
```

---

## PART 8 — QUICK NUMBERS REFERENCE (TFA_15_16_17 Example Project)

> These numbers are specific to the TFA_15_16_17 test project.  
> For your project, all of these values will be different — the formulas are fixed,  
> the numbers are project-specific. Use this as a sanity-check template.

```
  ┌────────────────────────────────────────────────────────────────────┐
  │  MODBUS_CONFIG.JSON  (TFA_15_16_17 values — yours will differ)    │
  │  B1.NOS = 6     (slaves: 1,2,3,4,5,6)                            │
  │  B1.NPT = 30    (packets: 9+1 per device × 3 devices)            │
  │  B1.NOP = 63    (params: 21 per device × 3 devices)              │
  │  B1.NOR = 63    (sum of all NRT values)                           │
  │  B3.SI  = [1,2,3,4,5,6]                                          │
  │  B3.SP  = [1,10,11,20,21,30]                                      │
  │  B6.WP  = [16,17,18, 37,38,39, 58,59,60]  (write params)        │
  │  B6.RP  = [ 9,10,14, 30,31,35, 51,52,56]  (verify params)       │
  ├────────────────────────────────────────────────────────────────────┤
  │  PARAMAP_CONFIG.JSON  (TFA_15_16_17 values)                       │
  │  P1.NLB  = 39   (30 Modbus-backed + 9 NVS-backed LBI slots)      │
  │  P1.NMD  = 51   (42 Modbus cloud params + 9 NVS cloud params)    │
  │  P2.LBI  = [1..39]  ← always sequential 1..NLB                   │
  │  P2.RPCI = [1..9]                                                 │
  │  P3.MDI  = [1..51]  ← always sequential 1..NMD                   │
  │  P3.LBI  = [31..39]  (NVS slots that go to cloud)               │
  ├────────────────────────────────────────────────────────────────────┤
  │  LUA FILES  (TFA_15_16_17 values)                                 │
  │  Device indices: TFA15=1, TFA16=2, TFA17=3                        │
  │  Action IDs:     Aid 1-9 = device controls, Aid 10-18 = NVS      │
  │  NVS keys:       STP15/16/17, BMS15/16/17, VALR15/16/17 (9 keys) │
  │  Cluster names:  "Valve", "ECFan", "SEN"  (engineer-assigned)     │
  └────────────────────────────────────────────────────────────────────┘

  GENERAL FORMULAS (project-independent):
  ┌────────────────────────────────────────────────────────────────────┐
  │  B1.NOS = number of slaves (len of B3.SI)                         │
  │  B1.NPT = total packets (sum of all slave packet counts)          │
  │  B1.NOP = total params (len of B5)                                │
  │  B1.NOR = sum of all B4.NRT values — MUST equal NOP if all LN=1  │
  │  P1.NLB = len(P2.MPI) + len(P2.RPCI)                            │
  │  P1.NMD = len(P3.MPI) + len(P3.LBI) = Σ(JKA keys×names)        │
  │  P2.LBI = always [1, 2, 3, ..., NLB]                             │
  │  P3.MDI = always [1, 2, 3, ..., NMD]                             │
  └────────────────────────────────────────────────────────────────────┘
```

---

## PART 9 — COMMON MISTAKES AND WHAT GOES WRONG

```
  ┌────────────────────────────────────────────────────────────────────┐
  │  MISTAKE                  │ SYMPTOM                               │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  Building B5 before B4    │ All B5.PN = 0. Firmware reads         │
  │                           │ everything from offset 0. All         │
  │                           │ values are wrong.                     │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  Write packets BEFORE     │ Reg[] offsets shift. Read values      │
  │  read packets in B4       │ map to wrong B5 params. Silent        │
  │                           │ data corruption.                      │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  P3.MPI order doesn't     │ Cloud JSON publishes values under      │
  │  match JKA order          │ wrong device names and keys.          │
  │                           │ Undetectable without live device.     │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  P1.NMD ≠ Σ(JKA keys×    │ Firmware boot fails. Gateway stays    │
  │  names)                   │ silent. No MQTT data at all.          │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  B6 WP[i] and RP[i]       │ Firmware verifies wrong write.        │
  │  accidentally reordered   │ Modbus_ParmWrite returns false        │
  │                           │ success or wrong error codes.         │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  B4.NRT > 60              │ Firmware internal buffer overflow.    │
  │                           │ Last registers in packet return       │
  │                           │ garbage or zero values.               │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  NVS key > 15 chars       │ ESP32 Preferences silently truncates  │
  │                           │ the key. NVS_Read() finds nothing.    │
  │                           │ Value lost on every reboot.           │
  ├───────────────────────────┼───────────────────────────────────────┤
  │  P2.MPI Phase 1 order     │ Lua device tables get wrong LBI       │
  │  wrong (devices mixed up) │ numbers. Valve commands go to wrong   │
  │                           │ physical device.                      │
  └───────────────────────────┴───────────────────────────────────────┘
```

---

*Visual Guide v2.0 | Date: 2026-05-03 | Reference example: TFA_15_16_17 (app is general-purpose)*  
*Companion documents: BMIoT_Config_Logic_Guide.md | BMIoT_ConfigTool_Development_Plan.md*

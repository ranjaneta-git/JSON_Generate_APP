# BMIoT Gateway — Configuration & Logic Reference Guide

**Application Version:** 2.0  
**Platform:** ESP32 (FreeRTOS + Lua) | **Project Reference:** TFA_15_16_17  
**Files Covered:** `Modbus_Config.json` · `ParamMap_Config.json` · `MainScript.lua` · `FuncScript.lua`

---

## QUICK REFERENCE CARD

### Critical Count Formulas

| Formula | Rule | TFA_15_16_17 Value |
|---|---|---|
| `NOR = sum(all B4.NRT)` | Every packet's register count adds to Reg[] | 8+2+1+2+1+1+1+1+1+3 = 21 per TFA × 3 = **63** |
| `NPT = count(B4.SA entries)` | One SA per packet | **30** (10 per TFA unit) |
| `NOP = count(B5.ID entries)` | One ID per parameter | **63** |
| `NOS = count(B3.SI)` | One slave index per physical device | **6** (2 per TFA unit) |
| `NLB = count(P2.MPI) + count(P2.RPCI)` | Modbus-backed + NVS-backed LBI slots | 30 + 9 = **39** |
| `NLBIN = NLB` | Always equal to NLB | **39** |
| `NMD = Σ(JKA[i].keys × JKA[i].names)` | Cloud JSON hierarchy drives this | 42 + 9 = **51** |
| `NMD = count(P3.MPI) + count(P3.LBI)` | Cross-check for NMD | 42 + 9 = **51** |

### Seven Key Rules — At a Glance

1. **B4 ordering**: For each slave, all READ-FC packets (FC1/2/3/4) must appear BEFORE write-FC packets (FC5/6)
2. **B5 ordering**: Params must be grouped by ascending PN (packet number); within a PN group, STA is the register address offset
3. **B6 pairing**: `WP[i]` and `RP[i]` must be same-index — the firmware does index-matched lookups to find the verify-read param
4. **P2.MPI ordering**: Interleaved write/read pairs first (slots 1–18), then read-only sensors (slots 19–30)
5. **P3.MPI ordering**: Must match JKA's sequential M_data consumption order exactly — firmware loads P3 first, JKA iterates over M_data in the same order
6. **NMD validation**: `PConfig_FileCheck()` computes `Σ(JKA keys × names)` and compares to P1.NMD — **hard boot fail** if mismatch
7. **B5 ID is display-only**: The actual parameter number = **array position** (1-indexed), not the ID field value

---

## PART A — System Architecture

### A.1  What is the BMIoT Gateway?

The BMIoT Gateway is an ESP32-based IoT edge device running FreeRTOS. It:

- Polls Modbus RTU slaves over RS485 continuously
- Runs a Lua scripting engine (in a dedicated FreeRTOS task) that implements device-specific control logic
- Publishes JSON telemetry to an MQTT broker over WiFi or GSM
- Receives ACTION_CMD and Script.Cmd (RPC) MQTT messages from the cloud and routes them to the Lua script or directly to Modbus

### A.2  The Four Config Files and Their Roles

| File | Loaded By | Purpose | Boot Fail If Missing? |
|---|---|---|---|
| `Modbus_Config.json` | `MBConfig_Lib` | Defines all Modbus slaves, packets, and parameters | Yes — no Modbus at all |
| `ParamMap_Config.json` | `ParamMapConfig_Lib` | Maps Modbus params to Lua buffers; defines cloud JSON structure | Yes — NMD check fails |
| `MainScript.lua` | `LuaEngine_Lib` | Device tables, init, main control loop | No — Lua engine disabled |
| `FuncScript.lua` | `LuaEngine_Lib` | All helper functions used by MainScript | No — function calls fail |

> `Config_File.json` is a fifth file providing WiFi credentials, MQTT broker address, and device identity. It overrides NTC fields from ParamMap_Config.json at runtime.

### A.3  Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          ESP32 (FreeRTOS)                            │
│                                                                      │
│  ┌─────────────────┐   ┌──────────────────────┐   ┌──────────────┐  │
│  │  eModbusRTU_Lib  │   │   ParamMapConfig_Lib  │   │  Com_Lib     │  │
│  │ (Reg[], Pkt[])   │◄──│  (LuaBuffVar[],      │──►│  (MQTT pub/  │  │
│  │                  │   │   M_data[])           │   │   sub, JSON  │  │
│  └────────┬─────────┘   └──────────┬────────────┘   └──────┬───────┘  │
│           │                        │                        │           │
│  ┌────────▼─────────┐   ┌──────────▼────────────┐          │           │
│  │  MBConfig_Lib    │   │   LuaEngine_Lib        │   ┌──────▼───────┐  │
│  │  (BL3,BL4,BL5,  │   │  (Lua VM, LuaBuffVar,  │   │  MQTT Broker │  │
│  │   BL6, config)   │   │   Action_CmdID/VAL,    │   │  (Cloud)     │  │
│  └────────┬─────────┘   │   ARS_Stat)            │   └──────────────┘  │
│           │              └──────────┬────────────┘                      │
│  ┌────────▼──────────────────────────▼─────────────────┐               │
│  │  SPIFFS (Config files loaded at boot)                │               │
│  │  Modbus_Config.json  ParamMap_Config.json            │               │
│  │  MainScript.lua      FuncScript.lua                  │               │
│  └──────────────────────────────────────────────────────┘               │
│                                                                          │
│  NVS Flash (Preferences): STP15/16/17, BMS15/16/17, VALR15/16/17       │
└──────────────────────────────────────────────────────────────────────────┘
         │ RS485 Modbus RTU
         ▼
┌─────────────────────────────────┐
│  Slave 1 (TFA15 main) SID=1     │
│  Slave 2 (TFA15 secondary) SID=2│
│  Slave 3 (TFA16 main) SID=3     │
│  Slave 4 (TFA16 secondary) SID=4│
│  Slave 5 (TFA17 main) SID=5     │
│  Slave 6 (TFA17 secondary) SID=6│
└─────────────────────────────────┘
```

### A.4  Firmware Library Map

| Library | Key Data Structures | Key Functions |
|---|---|---|
| `eModbusRTU_Lib` | `Reg[]`, `Pkt[]` | `modbus_RegCalc()`, `modreg_Read()`, `handleData()`, `eModbusRTU_Loop()`, `modbus_SendReq()` |
| `MBConfig_Lib` | `BL1–BL6[]` | `MBConfig_FileRead()`, `MBConfig_BlockAlloc()`, `Modbus_ParmRead()`, `Modbus_ParmWrite()`, `Check_Request()` |
| `ParamMapConfig_Lib` | `LuaBuffVar[]`, `M_data[]`, `PC1–PC3`, `JKA`, `JKC`, `SLDT[]` | `PConfig_FileRead()`, `PConfig_FileCheck()`, `Map_LuaBuffVarSync()`, `Map_LuaBuffVarWriteWait()`, `Map_MdataBuffSync()`, `Map_LuaBuffValUpdate()` |
| `LuaEngine_Lib` | `Action_CmdID`, `Action_CmdVAL`, `ARS_Stat` | `LuaFunc_WriteWait()`, `LuaFunc_WriteNoWait()`, `LuaFunc_Read()`, `LuaFunc_ReadWait()`, `Input_CmdVariable()` |
| `RPC_Lib` | — | `CmdID_Handler()` |
| `Com_Lib` | `Json_String`, `JKA`, `M_data[]` | `MQTT_JSON_Payload_WJ()`, `MQTT_Publish()`, `SentARS_Payload()` |

---

## PART B — Modbus_Config.json

### B.1  Overview and B1 — Global Counts

B1 contains four integers that define the dimensions of every data structure the firmware allocates at boot. All other blocks must be consistent with these values.

```json
"B1": { "NOS": 6, "NOP": 63, "NPT": 30, "NOR": 63 }
```

| Field | Full Name | Meaning | Firmware Use |
|---|---|---|---|
| `NOS` | Number Of Slaves | How many Modbus slave devices | Allocates `BL3[NOS]`, `MRC[NOS]` |
| `NOP` | Number Of Parameters | Total count of all parameters in B5 | Allocates `BL5[NOP]` |
| `NPT` | Number Per Table (packets) | Total Modbus packet definitions in B4 | Allocates `BL4[NPT]`, `Pkt[NPT]` |
| `NOR` | Number Of Registers | Total size of the shared Reg[] array | Allocates `Reg[NOR]` |

**Firmware function:** `MBConfig_BlockAlloc()` validates B1 against hard limits before allocating:
- `NOS ≤ 50`, `NPT ≤ 150`, `NOP ≤ 300`, `NOR ≤ 1500`

**Critical rule:** `NOR MUST equal sum of all NRT values in B4`. If this is wrong, `modreg_Read()` computes wrong Reg[] offsets — wrong data silently read with no error.

---

### B.2  B2 — Serial Settings

```json
"B2": { "BR": 19200, "DF": "8E1" }
```

| Field | Meaning | TFA Value |
|---|---|---|
| `BR` | Baud rate for RS485 UART | 19200 baud |
| `DF` | Data format: `<databits><parity><stopbits>` | `8E1` = 8 data bits, Even parity, 1 stop bit |

Must match the physical device's serial configuration exactly. Mismatch → garbled data or no response.

---

### B.3  B3 — Slave-to-Packet Map

```json
"B3": {
  "SI": [1, 2, 3, 4, 5, 6],
  "SP": [1, 10, 11, 20, 21, 30]
}
```

| Field | Meaning |
|---|---|
| `SI` | Slave index array. `SI[i]` = the Modbus slave address (1–247) of the i-th slave |
| `SP` | Start packet for each slave. `SP[i]` = the B4 packet number where slave `SI[i]` begins |

**How firmware uses B3:**  
`BL3[i].s_StPkt` = `SP[i]` (the first packet belonging to that slave). `Check_Request()` uses this to find all packets of a slave when resetting stale data.

**TFA_15_16_17 mapping:**

| Slave Index (i) | SI[i] (Modbus addr) | SP[i] (first packet) | Packets owned | Unit |
|---|---|---|---|---|
| 0 | 1 | 1 | Pkts 1–9 | TFA15 main |
| 1 | 2 | 10 | Pkt 10 | TFA15 secondary |
| 2 | 3 | 11 | Pkts 11–19 | TFA16 main |
| 3 | 4 | 20 | Pkt 20 | TFA16 secondary |
| 4 | 5 | 21 | Pkts 21–29 | TFA17 main |
| 5 | 6 | 30 | Pkt 30 | TFA17 secondary |

**Why two slaves per TFA?** The TFA unit's main Modbus slave (1/3/5) exposes coils, holding registers, and input registers for control. A secondary slave (2/4/6) is a separate sensor module (temperature + humidity) at a different Modbus address. They belong to the same physical TFA unit but are separate Modbus devices.

---

### B.4  B4 — Packet Definitions

B4 defines every Modbus transaction (one per entry). Each field is a parallel array: index 0 describes packet 1, index 1 describes packet 2, etc.

```json
"B4": {
  "SA":  [1, 4066, 4067, 1561, 301, 301, 4066, 4067, 301, 1561,  ...×3],
  "NRT": [8,    2,    1,    2,   1,   1,    1,    1,   1,    3,  ...×3],
  "FC":  [1,    3,    4,    3,   1,   2,    6,    6,   5,    3,  ...×3],
  "SID": [1,    1,    1,    1,   1,   1,    1,    1,   1,    2,  3...6]
}
```

| Field | Meaning |
|---|---|
| `SA` | Start Address — the first Modbus register/coil address in this transaction |
| `NRT` | Number of Registers per Transaction — how many registers/coils this packet reads or writes |
| `FC` | Function Code — the Modbus operation type |
| `SID` | Slave ID — which slave this packet belongs to (must be a value from B3.SI) |

**Function Code Reference Table:**

| FC | Type | Direction | Used For |
|---|---|---|---|
| 1 | Read Coils | Read | Discrete output status (ON/OFF/AM/Trip/Fire) |
| 2 | Read Discrete Inputs | Read | Discrete input status (external sensors) |
| 3 | Read Holding Registers | Read | Writable registers — valve/fan echo readback, setpoints |
| 4 | Read Input Registers | Read | Read-only analog sensor registers (ECFan analog feedback) |
| 5 | Write Single Coil | Write | Set/clear a single coil (ECFan enable ON/OFF) |
| 6 | Write Single Register | Write | Write a 16-bit value to a holding register (valve position, fan speed) |

**Packet Ordering Rule — Critical:**  
For each slave, ALL read-FC packets (FC1/2/3/4) must come **before** any write-FC packets (FC5/6).  
Reason: `eModbusRTU_Loop()` scans the packet list and polls only read-FC packets continuously. Write packets are dispatched on-demand by `Modbus_ParmWrite()`. The Reg[] offset for every packet is calculated as the cumulative sum of NRT values for all preceding packets (`modbus_RegCalc()`). If write packets are interspersed with reads, the Reg[] layout breaks — values land in wrong slots silently.

**TFA_15_16_17 — Full B4 Table (1 TFA block, repeated × 3):**

| Pkt # (TFA15) | SA | NRT | FC | SID | Purpose |
|---|---|---|---|---|---|
| 1 | 1 | 8 | FC1 | 1 | Read 8 status coils (OFF/ON/AM/Fire/Trip/DPS...)|
| 2 | 4066 | 2 | FC3 | 1 | Read valve+fan write-echo holding regs |
| 3 | 4067 | 1 | FC4 | 1 | Read ECFan analog feedback (input reg) |
| 4 | 1561 | 2 | FC3 | 1 | Read valve position feedback |
| 5 | 301 | 1 | FC1 | 1 | Read ECFan enable coil status |
| 6 | 301 | 1 | FC2 | 1 | Read ECFan enable discrete input |
| 7 | 4066 | 1 | **FC6** | 1 | **WRITE** valve position |
| 8 | 4067 | 1 | **FC6** | 1 | **WRITE** ECFan speed |
| 9 | 301 | 1 | **FC5** | 1 | **WRITE** ECFan enable coil |
| 10 | 1561 | 3 | FC3 | 2 | Read 3 sensor regs (RH, RAT, SAT) from slave 2 |

Packets 11–20 are identical to 1–10 for TFA16 (SID 3+4), and 21–30 for TFA17 (SID 5+6).

---

### B.5  B5 — Parameter Definitions

B5 maps each individual register/coil to a "parameter" that the rest of the system uses by number. Each B5 entry = one parameter. **The array position (1-indexed) is the paramID, not the ID field value.**

```json
"B5": {
  "ID":  [1, 2, 3, ..., 63],       -- display label only, never used in runtime math
  "PN":  [1, 1, 1, 1, 1, 1, 1, 1,  2, 2,  3,  4, 4,  5,  6,  7,  8,  9, 10,10,10, ...],
  "STA": [1, 2, 3, 4, 5, 6, 7, 8, 4066,4067, 4067,1561,1562,301,301,4066,4067,301,1561,1562,1563, ...],
  "LN":  [1, 1, 1, ..., 1],        -- all 1 for UINT16 (TFA uses no 32-bit params)
  "FMT": [3, 3, 3, ..., 3],        -- all FMT=3 (UINT16bit)
  "MLT": [1,1,1,1,1,1,1,1, 1,1, 0.1,0.1,1, 1,1,1,1,1, 0.1,0.01,0.1, ...]
}
```

| Field | Meaning | Rule |
|---|---|---|
| `ID` | Display label | Stored in `BL5[i].s_Indx` but **never used in any runtime computation** |
| `PN` | Packet Number — which B4 packet this param reads from/writes to | Must be a valid packet number (1 ≤ PN ≤ NPT) |
| `STA` | Start Address — the register/coil address within that packet | Must fall within `[SA, SA + NRT - 1]` of the referenced packet |
| `LN` | Length in registers — 1 for 16-bit, 2 for 32-bit | Must match FMT: LN=1 for FMT 3/8; LN=2 for FMT 1/2/4/5/6/7 |
| `FMT` | Data format code | See FMT table below |
| `MLT` | Multiplier — applied after reading raw value | `return_value = round(raw_value, 2) * MLT` |

**FMT Code Reference Table:**

| FMT | Name | Size | Description |
|---|---|---|---|
| 1 | `FP32bit_BA` | 32-bit | IEEE 754 float, low word first (little-endian words) |
| 2 | `FP32bit_AB` | 32-bit | IEEE 754 float, high word first (big-endian words) |
| **3** | **`UINT16bit`** | **16-bit** | **Unsigned integer — all TFA params use this** |
| 4 | `INT32bit_BA` | 32-bit | Signed 32-bit, low word first |
| 5 | `INT32bit_AB` | 32-bit | Signed 32-bit, high word first |
| 6 | `UINT32bit_BA` | 32-bit | Unsigned 32-bit, low word first |
| 7 | `UINT32bit_AB` | 32-bit | Unsigned 32-bit, high word first |
| 8 | `INT16bit` | 16-bit | Signed 16-bit integer |

**MLT Scaling — Why It Matters:**  
MLT is applied **only on reads**, not on writes. Lua always writes raw unscaled values:

| MLT | Raw → Returned | Use Case in TFA |
|---|---|---|
| `1` | raw=1 → 1.0 | Coil status (0/1), raw integer values |
| `0.1` | raw=750 → 75.0 | Valve FB % (raw 0–1000 → 0.0–100.0%) |
| `0.1` | raw=245 → 24.5 | Temperature in °C (raw = tenths of degree) |
| `0.01` | raw=2450 → 24.50 | Higher-precision temperature (RAT sensor) |

**TFA_15_16_17 — Full B5 Parameter Table (TFA15 block, parameters 1–21):**

| ParamID | PN | STA | FC | SID | MLT | Physical Meaning |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | FC1 | 1 | 1 | TFA15 coil: OFF mode status |
| 2 | 1 | 2 | FC1 | 1 | 1 | TFA15 coil: ON mode status |
| 3 | 1 | 3 | FC1 | 1 | 1 | TFA15 coil: Trip alarm |
| 4 | 1 | 4 | FC1 | 1 | 1 | TFA15 coil: Fire alarm |
| 5 | 1 | 5 | FC1 | 1 | 1 | TFA15 coil: Auto Mode (AM) |
| 6 | 1 | 6 | FC1 | 1 | 1 | TFA15 coil: DPS alarm |
| 7 | 1 | 7 | FC1 | 1 | 1 | TFA15 coil: Fire protection active |
| 8 | 1 | 8 | FC1 | 1 | 1 | TFA15 coil: Fire damper status |
| 9 | 2 | 4066 | FC3 | 1 | 1 | TFA15 valve write-echo (holding reg, read back after FC6 write) |
| 10 | 2 | 4067 | FC3 | 1 | 1 | TFA15 fan write-echo (holding reg, read back after FC6 write) |
| 11 | 3 | 4067 | FC4 | 1 | 0.1 | TFA15 ECFan analog feedback (input reg, raw 0–1000 → 0–100%) |
| 12 | 4 | 1561 | FC3 | 1 | 0.1 | TFA15 valve position feedback (raw 0–1000 → 0–100%) |
| 13 | 4 | 1562 | FC3 | 1 | 1 | TFA15 holding reg at 1562 |
| 14 | 5 | 301 | FC1 | 1 | 1 | TFA15 ECFan enable coil status |
| 15 | 6 | 301 | FC2 | 1 | 1 | TFA15 ECFan discrete enable feedback |
| **16** | **7** | **4066** | **FC6** | **1** | **1** | **TFA15 valve WRITE ← B6.WP[0]** |
| **17** | **8** | **4067** | **FC6** | **1** | **1** | **TFA15 fan speed WRITE ← B6.WP[1]** |
| **18** | **9** | **301** | **FC5** | **1** | **1** | **TFA15 enable coil WRITE ← B6.WP[2]** |
| 19 | 10 | 1561 | FC3 | 2 | 0.1 | TFA15 Return Air Relative Humidity (slave 2) |
| 20 | 10 | 1562 | FC3 | 2 | 0.01 | TFA15 Return Air Temperature — RAT (slave 2, high precision) |
| 21 | 10 | 1563 | FC3 | 2 | 0.1 | TFA15 Supply Air Temperature — SAT (slave 2) |

Parameters 22–42 = TFA16 (same pattern, SID 3+4, PN 11–20).  
Parameters 43–63 = TFA17 (same pattern, SID 5+6, PN 21–30).

---

### B.6  B6 — Write/Read Parameter Pairs

B6 tells the firmware which parameters are writable and which read-back parameter to use for verify.

```json
"B6": {
  "WP": [16, 17, 18, 37, 38, 39, 58, 59, 60],
  "RP": [ 9, 10, 14, 30, 31, 35, 51, 52, 56]
}
```

| Field | Meaning |
|---|---|
| `WP` | Write Parameter list — paramIDs that can be written. These must all have write-FC (FC5/FC6) |
| `RP` | Read Parameter list — `RP[i]` is the read-back param to verify `WP[i]`. Same index = same pair |

**B6 pair meaning for TFA_15_16_17:**

| WP | RP | Write Action | Verify By Reading |
|---|---|---|---|
| 16 (FC6 @ 4066) | 9 (FC3 @ 4066) | Write valve position | Read back valve echo holding reg |
| 17 (FC6 @ 4067) | 10 (FC3 @ 4067) | Write fan speed | Read back fan echo holding reg |
| 18 (FC5 @ 301) | 14 (FC1 @ 301) | Write enable coil | Read back coil status |
| 37 (FC6 @ 4066) | 30 (FC3 @ 4066) | TFA16 valve write | TFA16 valve echo |
| 38 (FC6 @ 4067) | 31 (FC3 @ 4067) | TFA16 fan write | TFA16 fan echo |
| 39 (FC5 @ 301) | 35 (FC1 @ 301) | TFA16 enable | TFA16 coil status |
| 58 (FC6 @ 4066) | 51 (FC3 @ 4066) | TFA17 valve write | TFA17 valve echo |
| 59 (FC6 @ 4067) | 52 (FC3 @ 4067) | TFA17 fan write | TFA17 fan echo |
| 60 (FC5 @ 301) | 56 (FC1 @ 301) | TFA17 enable | TFA17 coil status |

**Firmware write flow (`Modbus_ParmWrite`):**
1. Linear search through `BL6[].WP` to find the paramID → if not found, return `READ_PARAM_NOT_FOUND(2)`
2. Stage write value in `Reg[regCalc(PN)]` of the write packet
3. Send write packet (FC5/FC6) via RS485
4. Send verify-read packet (packet of RP[i])
5. Compare `modreg_Read(RP[i])` against written value
6. Return `WRITE_SUCCESS(1)`, `VERIFY_FAIL(3)`, or `PACKET_FAIL(4)`

---

### B.7  The Reg[] Memory Layout

`Reg[]` is a single flat array of `NOR=63` floats shared between the Modbus polling loop and the Lua engine. Each packet "owns" a contiguous slice of it.

**`modbus_RegCalc(pckt)` formula:**
```
RegCalc(pckt) = NRT[0] + NRT[1] + ... + NRT[pckt-2]
              = sum of NRT values for all packets before packet pckt
```

**TFA_15_16_17 Reg[] Layout (NRT per packet: 8,2,1,2,1,1,1,1,1,3 × 3):**

```
Reg[0 .. 7]   ← Pkt 1  (FC1, SID=1, SA=1,    NRT=8) — TFA15 coil status (8 coils)
Reg[8 .. 9]   ← Pkt 2  (FC3, SID=1, SA=4066, NRT=2) — TFA15 valve+fan write-echo
Reg[10]       ← Pkt 3  (FC4, SID=1, SA=4067, NRT=1) — TFA15 ECFan analog FB
Reg[11..12]   ← Pkt 4  (FC3, SID=1, SA=1561, NRT=2) — TFA15 valve FB
Reg[13]       ← Pkt 5  (FC1, SID=1, SA=301,  NRT=1) — TFA15 enable coil status
Reg[14]       ← Pkt 6  (FC2, SID=1, SA=301,  NRT=1) — TFA15 enable discrete FB
Reg[15]       ← Pkt 7  (FC6, SID=1, SA=4066, NRT=1) — TFA15 valve WRITE staging
Reg[16]       ← Pkt 8  (FC6, SID=1, SA=4067, NRT=1) — TFA15 fan WRITE staging
Reg[17]       ← Pkt 9  (FC5, SID=1, SA=301,  NRT=1) — TFA15 enable WRITE staging
Reg[18..20]   ← Pkt 10 (FC3, SID=2, SA=1561, NRT=3) — TFA15 sensor: RH, RAT, SAT

Reg[21..41]   ← Pkts 11–20  (TFA16, same structure, offset +21)

Reg[42..62]   ← Pkts 21–30  (TFA17, same structure, offset +42)
```

> Write packets (FC5/FC6) also own a Reg[] slot. For FC6, `Reg[RegCalc(pkt)]` holds the value to send. `modbus_SendReq()` reads from that slot when building the FC6 frame.

---

### B.8  modreg_Read() — The Decode Formula

```cpp
// Firmware: eModbusRTU_Lib.cpp
float modreg_Read(uint16_t pckt, uint16_t addr, uint16_t len, uint8_t fmt, float mlt) {
    uint16_t regtr = addr - Pkt[pckt-1].str_addr + modbus_RegCalc(pckt);
    // regtr = absolute index into Reg[]
    float raw = decode_by_fmt(Reg[regtr], fmt, len);
    return round_2dec(raw) * mlt;
}
```

**Step-by-step for param 12 (TFA15 valve FB):**
- param 12 is at array position 11 (0-indexed) → PN=4, STA=1561, LN=1, FMT=3, MLT=0.1
- Packet 4 starts at Reg[11] (RegCalc = 8+2+1 = 11)
- `regtr = 1561 - 1561 + 11 = 11` → reads `Reg[11]`
- FMT=3 (UINT16) → raw = `Reg[11]` as unsigned integer
- Return = `round(Reg[11], 2) × 0.1`
- If raw=750 → 75.0 → valve is at 75.0%

**Rule:** STA must be ≥ packet's SA, and `(STA - SA) < NRT`. Otherwise the formula computes a Reg[] index that belongs to a different packet — wrong data, no error.

---

### B.9  NOR Calculation

```
NOR = Σ NRT[i] for all i in B4

For TFA_15_16_17:
Per TFA block (10 packets): 8+2+1+2+1+1+1+1+1+3 = 21
3 TFA blocks:  21 × 3 = 63 = NOR ✓
```

Every time you add a packet to B4 (e.g., adding a new sensor), you must:
1. Add its NRT to B4
2. Recalculate and update `B1.NOR`
3. Update `B1.NPT`
4. Update B5 to add parameters for the new packet
5. Update `B1.NOP`

---

### B.10  Modbus Firmware Functions — Summary

| Function | What It Does | Called By |
|---|---|---|
| `MBConfig_FileRead()` | Parses B1–B6 from JSON into BL1–BL6 structs | Boot sequence |
| `MBConfig_BlockAlloc()` | Validates B1 limits, allocates all arrays | Boot sequence |
| `eModbusRTU_Loop()` | Continuously polls all READ-FC packets in a FreeRTOS task | Background task |
| `handleData()` | On receive: stores data in `Reg[RegCalc(pkt)+i]`, increments `success_req` | Called from Modbus loop |
| `modbus_RegCalc(pckt)` | Returns the Reg[] starting offset for a packet | Called everywhere |
| `modreg_Read(pkt,addr,len,fmt,mlt)` | Decodes one value from Reg[] using the formula above | `Modbus_ParmRead()` |
| `Modbus_ParmRead(paramID)` | Direct index: returns `modreg_Read(BL5[paramID-1].*)` | `Map_LuaBuffVarSync()` |
| `Modbus_ParmWrite(writeID, value)` | Linear search B6.WP→write→read→verify | `Map_LuaBuffVarWriteWait()` |
| `Check_Request()` | If slave's `success_req` is stale, clears all its Reg[] data to avoid serving old values | Background timer |

---

## PART C — ParamMap_Config.json

### C.1  Overview and P1 — Global Counts

```json
"P1": { "NLB": 39, "NLBIN": 39, "NMD": 51 }
```

| Field | Meaning | TFA Value |
|---|---|---|
| `NLB` | Number of LBI slots total | 39 (30 Modbus-backed + 9 NVS-backed) |
| `NLBIN` | Number of LBI Input slots (always = NLB) | 39 |
| `NMD` | Number of M_data slots (cloud telemetry points) | 51 (42 Modbus + 9 LBI-backed) |

---

### C.2  P2 — LBI Slot Mapping

**LBI (Lua Buffer Input) slots** are the bridge between Lua and the Modbus hardware. Lua reads and writes hardware using LBI slot numbers. The firmware keeps `LuaBuffVar[NLB]` — one float per slot.

```json
"P2": {
  "LBI":  [1, 2, 3, ..., 39],
  "MPI":  [16,12,17,11,18,15, 37,33,38,32,39,36, 58,54,59,53,60,57, 5,20,26,41,47,62, 2,23,44, 1,22,43],
  "RPCI": [1, 2, 3, 4, 5, 6, 7, 8, 9]
}
```

**The PC2_MP / PC2_RPC Split:**

```
LBI slots 1 to len(P2.MPI) → PC2_MP (Modbus-backed)
   Each slot maps to a B5 parameter ID via P2.MPI
   Firmware: Buff_Write_Wait → Modbus_ParmWrite (hardware write)
             Buff_Read → reads from LuaBuffVar[] (auto-synced by Map_LuaBuffVarSync)
             Buff_Read_Wait → Modbus_ParmReadWait (on-demand hardware read)

LBI slots (len(P2.MPI)+1) to NLB → PC2_RPC (NVS/RAM-backed)
   Each slot maps to an RPCI index via P2.RPCI
   Firmware: Buff_Write_NoWait → only writes to LuaBuffVar[] in RAM
             No Modbus hardware involved
             CmdID_Handler (RPC) → Map_LuaBuffValUpdate → direct RAM write
```

**For TFA_15_16_17:**  
LBI slots 1–30 = Modbus-backed (P2.MPI has 30 entries)  
LBI slots 31–39 = NVS/RAM-backed (P2.RPCI has 9 entries)

**Firmware loading loop (`PConfig_FileRead`):**
```cpp
for (int i = 0; i < p_NLB; i++) {
    if (i < p_LBMPNum) {
        PC2_MP[i].p_LBI = P2.LBI[i];
        PC2_MP[i].p_MPI = P2.MPI[i];   // B5 paramID
    } else if (i - p_LBMPNum < p_LBRPCNum) {
        PC2_RPC[i - p_LBMPNum].p_LBI  = P2.LBI[i];
        PC2_RPC[i - p_LBMPNum].p_RPCI = P2.RPCI[i - p_LBMPNum];
    }
}
```

**Note on RPCI:** The `p_RPCI` value is stored in `PC2_RPC` but **never read at runtime**. `CmdID_Handler()` uses only the LBI slot number to route the write. RPCI serves as a config-tool cross-reference to B6.WP for documentation purposes only.

**TFA_15_16_17 — P2.MPI Full Mapping Table:**

| LBI Slot | P2.MPI → ParamID | FC | MLT | Lua Usage | Physical Meaning |
|---|---|---|---|---|---|
| 1 | 16 | FC6 | 1 | `Valve[Write][TFA15]` | TFA15 valve position WRITE |
| 2 | 12 | FC3 | 0.1 | `Valve[Stat][TFA15]` | TFA15 valve feedback (0–100%) |
| 3 | 17 | FC6 | 1 | `ECFan[Write][TFA15]` | TFA15 fan speed WRITE |
| 4 | 11 | FC4 | 0.1 | `ECFan[Stat][TFA15]` | TFA15 fan analog feedback |
| 5 | 18 | FC5 | 1 | `ECFan[EnWrite][TFA15]` | TFA15 enable coil WRITE |
| 6 | 15 | FC2 | 1 | `ECFan[EnStat][TFA15]` | TFA15 enable discrete FB |
| 7 | 37 | FC6 | 1 | `Valve[Write][TFA16]` | TFA16 valve position WRITE |
| 8 | 33 | FC3 | 0.1 | `Valve[Stat][TFA16]` | TFA16 valve feedback |
| 9 | 38 | FC6 | 1 | `ECFan[Write][TFA16]` | TFA16 fan speed WRITE |
| 10 | 32 | FC4 | 0.1 | `ECFan[Stat][TFA16]` | TFA16 fan analog feedback |
| 11 | 39 | FC5 | 1 | `ECFan[EnWrite][TFA16]` | TFA16 enable coil WRITE |
| 12 | 36 | FC2 | 1 | `ECFan[EnStat][TFA16]` | TFA16 enable discrete FB |
| 13 | 58 | FC6 | 1 | `Valve[Write][TFA17]` | TFA17 valve position WRITE |
| 14 | 54 | FC3 | 0.1 | `Valve[Stat][TFA17]` | TFA17 valve feedback |
| 15 | 59 | FC6 | 1 | `ECFan[Write][TFA17]` | TFA17 fan speed WRITE |
| 16 | 53 | FC4 | 0.1 | `ECFan[Stat][TFA17]` | TFA17 fan analog feedback |
| 17 | 60 | FC5 | 1 | `ECFan[EnWrite][TFA17]` | TFA17 enable coil WRITE |
| 18 | 57 | FC2 | 1 | `ECFan[EnStat][TFA17]` | TFA17 enable discrete FB |
| 19 | 5 | FC1 | 1 | status monitoring | TFA15 Auto Mode (AM) coil |
| 20 | 20 | FC3 | 0.01 | `SEN[Stat][TFA15]` | TFA15 Return Air Temp (RAT) |
| 21 | 26 | FC1 | 1 | status monitoring | TFA15 another coil status |
| 22 | 41 | FC3 | 0.01 | `SEN[Stat][TFA16]` | TFA16 Return Air Temp (RAT) |
| 23 | 47 | FC1 | 1 | status monitoring | TFA16 coil status |
| 24 | 62 | FC3 | 0.01 | `SEN[Stat][TFA17]` | TFA17 Return Air Temp (RAT) |
| 25 | 2 | FC1 | 1 | status monitoring | TFA15 ON coil status |
| 26 | 23 | FC1 | 1 | status monitoring | TFA16 ON coil status |
| 27 | 44 | FC1 | 1 | status monitoring | TFA17 ON coil status |
| 28 | 1 | FC1 | 1 | status monitoring | TFA15 OFF coil status |
| 29 | 22 | FC1 | 1 | status monitoring | TFA16 OFF coil status |
| 30 | 43 | FC1 | 1 | status monitoring | TFA17 OFF coil status |
| **31** | *(NVS)* | — | — | `LBI[1]` → TFA15 setpoint | NVS key: `STP15` |
| **32** | *(NVS)* | — | — | `LBI[2]` → TFA15 BMS mode | NVS key: `BMS15` |
| **33** | *(NVS)* | — | — | `LBI[3]` → TFA16 setpoint | NVS key: `STP16` |
| **34** | *(NVS)* | — | — | `LBI[4]` → TFA16 BMS mode | NVS key: `BMS16` |
| **35** | *(NVS)* | — | — | `LBI[5]` → TFA17 setpoint | NVS key: `STP17` |
| **36** | *(NVS)* | — | — | `LBI[6]` → TFA17 BMS mode | NVS key: `BMS17` |
| **37** | *(NVS)* | — | — | `LBI[7]` → TFA15 ON/OFF tracker | Buff_Write_NoWait only |
| **38** | *(NVS)* | — | — | `LBI[8]` → TFA16 ON/OFF tracker | Buff_Write_NoWait only |
| **39** | *(NVS)* | — | — | `LBI[9]` → TFA17 ON/OFF tracker | Buff_Write_NoWait only |

**Key Distinction: `Map_LuaBuffVarSync()` skips write-FC params**  
The background sync function reads all read-FC Modbus-backed slots and updates `LuaBuffVar[]`. It explicitly skips any slot whose B5 param has a write FC (5/6). This ensures that values Lua has staged for writing (e.g., valve target position) are not overwritten by background polling before the actual write transaction completes.

---

### C.3  P3 — M_data[] Mapping

P3 defines the 51 slots of `M_data[]` — the cloud telemetry array that gets serialized into the MQTT JSON payload.

```json
"P3": {
  "MDI":  [1, 2, 3, ..., 51],
  "MPI":  [1,2,5,7,8,3,4,6,12,11,15,19,20,21,22,23,26,28,29,24,25,27,33,32,36,40,41,42,43,44,47,49,50,45,46,48,54,53,57,61,62,63],
  "LBI":  [31,32,33,34,35,36,37,38,39]
}
```

**The PC3_MP / PC3_LB Split:**

```
M_data slots 0 to len(P3.MPI)-1 → PC3_MP (Modbus-backed, from Modbus_ParmRead)
M_data slots len(P3.MPI) to NMD-1 → PC3_LB (LBI-backed, from LuaBuffVar)
```

**Firmware loading loop:**
```cpp
for (int i = 0; i < p_NMD; i++) {
    if (i < p_MDMPNum) {
        PC3_MP[i].p_MDI = P3.MDI[i];
        PC3_MP[i].p_MPI = P3.MPI[i];    // B5 paramID → read via Modbus
    } else {
        PC3_LB[i - p_MDMPNum].p_MDI = P3.MDI[i];
        PC3_LB[i - p_MDMPNum].p_LBI = P3.LBI[i - p_MDMPNum]; // LuaBuffVar[LBI-1]
    }
}
```

**Map_MdataBuffSync()** fills `M_data[]` each cycle:
1. For M_data[0..41]: calls `Modbus_ParmRead(PC3_MP[i].p_MPI)` → decodes from Reg[] → stores
2. For M_data[42..50]: reads `LuaBuffVar[PC3_LB[i].p_LBI - 1]` directly

**Critical rule — P3.MPI order must match JKA sequential order:**  
`MQTT_JSON_Payload_WJ()` iterates JKA entries and consumes M_data[] sequentially from index 0. P3.MPI must be ordered so that M_data[k] holds the value that JKA's k-th entry expects.

**TFA_15_16_17 — P3.MPI to M_data[] mapping (TFA15 block):**

| M_data index | P3.MPI → ParamID | Physical Meaning | JKA Entry → Key |
|---|---|---|---|
| 0 | 1 | TFA15 OFF coil | `TFA15_DIE1` → `OFF.St` |
| 1 | 2 | TFA15 ON coil | `TFA15_DIE1` → `ON.St` |
| 2 | 5 | TFA15 AM coil | `TFA15_DIE1` → `AM.St` |
| 3 | 7 | TFA15 Fire_Pu coil | `TFA15_DIE1` → `Fire_Pu.St` |
| 4 | 8 | TFA15 Fire_damp coil | `TFA15_DIE1` → `Fire_damp.St` |
| 5 | 3 | TFA15 Trip coil | `TFA15_DIE1_Trip` → `Trip.Tr` |
| 6 | 4 | TFA15 Fire coil | `TFA15_DIE1_Fire` → `Fire.Ar` |
| 7 | 6 | TFA15 DPS coil | `TFA15_DIE1_DPS` → `DPS.Ar` |
| 8 | 12 | TFA15 valve FB (0–100%) | `TFA15_AIE1` → `valve_Fb.per` |
| 9 | 11 | TFA15 fan analog FB | `TFA15_AIE1` → `EC_Fan_Fb.per` |
| 10 | 15 | TFA15 enable discrete | `TFA15_DOE1` → `EC_Fan_Enable.St` |
| 11 | 19 | TFA15 RH (slave 2) | `TFA15_AIE2` → `RARH.per` |
| 12 | 20 | TFA15 RAT (0.01 precision) | `TFA15_AIE3` → `RAT.DegC` |
| 13 | 21 | TFA15 SAT | `TFA15_AIE3` → `SAT.DegC` |

M_data[14–27] = TFA16 (same pattern, params 22–42).  
M_data[28–41] = TFA17 (same pattern, params 43–63).  
M_data[42–50] = LuaBuffVar[30–38] = LBI slots 31–39 (setpoints, BMS modes, action trackers).

> Notice that P3.MPI reorders the coil params (1,2,5,7,8 then 3,4,6) to match JKA grouping — the physical device's coil order (OFF=1, ON=2, Trip=3, Fire=4, AM=5, DPS=6, Fire_Pu=7, Fire_damp=8) differs from the cloud JSON grouping. P3.MPI is the bridge that reorders them.

---

### C.4  JKY / JKA — Cloud JSON Hierarchy

JKA defines the structure of the MQTT JSON payload. Each entry in the JKA array is:

```
JKA[i] = [ "EqTypeName",  ["key1","key2",...],  ["name1","name2",...] ]
           ▲ equipment     ▲ property keys         ▲ device/signal names
             type label      (one per property)       (one sub-object each)
```

**M_data slots consumed = `len(keys) × len(names)`**

**Firmware (`MQTT_JSON_Payload_WJ`):**
```cpp
int md_ptr = 0;
JsonObject Head = doc.createNestedObject(JKC->p_JKH);  // "properties"

for (int i = 0; i < JKA_size; i++) {
    JsonObject EqType = Head.createNestedObject(JKA[i].p_JEqType);
    for (int j = 0; j < JKA[i].p_JEqNmNum; j++) {
        JsonObject EqObj = EqType.createNestedObject(JKA[i].p_JEqNm[j]);
        for (int k = 0; k < JKA[i].p_JKeysNum; k++) {
            EqObj[JKA[i].p_JKeys[k]] = M_data[md_ptr++];
        }
    }
}
```

**TFA_15_16_17 — Full JKA Table:**

| JKA[i] | EqType | Key(s) | Names | M_data slots | Count |
|---|---|---|---|---|---|
| 0 | `TFA15_DIE1` | `["St"]` | `["OFF","ON","AM","Fire_Pu","Fire_damp"]` | [0..4] | 5 |
| 1 | `TFA15_DIE1_Trip` | `["Tr"]` | `["Trip"]` | [5] | 1 |
| 2 | `TFA15_DIE1_Fire` | `["Ar"]` | `["Fire"]` | [6] | 1 |
| 3 | `TFA15_DIE1_DPS` | `["Ar"]` | `["DPS"]` | [7] | 1 |
| 4 | `TFA15_AIE1` | `["per"]` | `["valve_Fb","EC_Fan_Fb"]` | [8..9] | 2 |
| 5 | `TFA15_DOE1` | `["St"]` | `["EC_Fan_Enable"]` | [10] | 1 |
| 6 | `TFA15_AIE2` | `["per"]` | `["RARH"]` | [11] | 1 |
| 7 | `TFA15_AIE3` | `["DegC"]` | `["RAT","SAT"]` | [12..13] | 2 |
| 8–15 | `TFA16_*` | (same pattern) | (same pattern) | [14..27] | 14 |
| 16–23 | `TFA17_*` | (same pattern) | (same pattern) | [28..41] | 14 |
| 24 | `TFA_Vars` | `["Set"]` | `["Spt31","Bms32","Spt33","Bms34","Spt35","Bms36","En37","En38","En39"]` | [42..50] | 9 |
| **Total** | | | | | **51 = NMD ✓** |

**Resulting Cloud JSON structure:**
```json
{
  "machineId": "GWAY01",
  "deviceId": "GW01",
  "timestamp": "2026-05-03 14:00:00",
  "properties": {
    "TFA15_DIE1": {
      "OFF":       { "St": 0.0 },
      "ON":        { "St": 1.0 },
      "AM":        { "St": 0.0 },
      "Fire_Pu":   { "St": 0.0 },
      "Fire_damp": { "St": 0.0 }
    },
    "TFA15_AIE1": {
      "valve_Fb":  { "per": 75.0 },
      "EC_Fan_Fb": { "per": 80.0 }
    },
    "TFA15_AIE3": {
      "RAT": { "DegC": 24.50 },
      "SAT": { "DegC": 19.5  }
    },
    ...
    "TFA_Vars": {
      "Spt31": { "Set": 250.0 },
      "Bms32": { "Set": 1.0   },
      ...
    }
  }
}
```

**NMD Hard-Validation Rule (`PConfig_FileCheck()`):**
```
computed = Σ (JKA[i].keys_count × JKA[i].names_count)
if computed ≠ P1.NMD → firmware logs error and boot FAILS
```
This check runs at every boot. If you add a device name to JKA but forget to add a corresponding P3.MPI entry and update P1.NMD → boot will hard-fail with a config error.

---

### C.5  JKC — JSON Structural Keys

```json
"JKC": { "JKH": "properties", "EKS": "DKEY" }
```

| Field | Meaning | Impact |
|---|---|---|
| `JKH` | JSON Key Hierarchy — the name of the data wrapper object in the MQTT payload | If changed, cloud platform may not find the data section |
| `EKS` | External Key String — used by cloud to identify data points in schedule/action messages | Used in MQTT subscription parsing |

---

### C.6  NTC — Network & Cloud Identity

```json
"NTC": {
  "IP": "18.191.222.62", "PT": "1234", "CI": "Lucas",
  "SN": [1], "MI": ["GWAY01"], "MT": ["GWAY"], "DI": "GW01"
}
```

| Field | Meaning | Notes |
|---|---|---|
| `IP` | MQTT broker IP | Secondary — `Config_File.json` → `CF.Tcp` takes precedence at runtime |
| `PT` | MQTT broker port | Secondary — `Config_File.json` → `CF.Port` overrides |
| `CI` | MQTT client identifier string | Used in SLDT struct |
| `SN` | Slave numbers array — one per Modbus slave group | `len(SN)` must equal `B1.NOS` conceptually |
| `MI` | Machine ID array — one per slave group | Becomes `machineId` field in cloud JSON |
| `MT` | Machine type array | Device type label on cloud platform |
| `DI` | Device ID | Becomes `deviceId` field in cloud JSON. Also from `CF.DEV_id` |

The firmware loads NTC into `SLDT[]` (Slave Details array). At runtime, `CF.MCN_id` and `CF.DEV_id` from `Config_File.json` are passed to `MQTT_JSON_Payload_WJ()` as `MC_id` and `Dv_id`, overriding NTC.MI and NTC.DI.

---

### C.7  MST — Profile Settings

```json
"MST": { "PRF": 0 }
```

`PRF=0` = standard operational profile. This flag selects firmware behavior modes (edge scheduler activation, specific data handling paths) without recompiling. Currently `Model_E` vs `Model_A` device type (from Config_File) is the primary branch; PRF provides a secondary configuration layer.

---

### C.8  LuaBuffVar[] Layout

```
LuaBuffVar[0..29]   ← Slots 1–30: Modbus-backed (PC2_MP)
  [0]  = LBI  1 → paramID 16 (TFA15 valve write/read)
  [1]  = LBI  2 → paramID 12 (TFA15 valve FB)
  ...
  [17] = LBI 18 → paramID 57 (TFA17 enable FB)
  [18] = LBI 19 → paramID  5 (TFA15 AM coil)
  ...
  [29] = LBI 30 → paramID 43 (TFA17 OFF coil)

LuaBuffVar[30..38]  ← Slots 31–39: NVS/RAM-backed (PC2_RPC)
  [30] = LBI 31 → TFA15 setpoint (persisted in NVS "STP15")
  [31] = LBI 32 → TFA15 BMS mode (persisted in NVS "BMS15")
  [32] = LBI 33 → TFA16 setpoint
  [33] = LBI 34 → TFA16 BMS mode
  [34] = LBI 35 → TFA17 setpoint
  [35] = LBI 36 → TFA17 BMS mode
  [36] = LBI 37 → TFA15 action mode tracker (ON/OFF state for cloud)
  [37] = LBI 38 → TFA16 action mode tracker
  [38] = LBI 39 → TFA17 action mode tracker
```

---

### C.9  M_data[] Layout

```
M_data[0..13]   ← TFA15: 8 coils + fan/valve FB + enable + RH + RAT + SAT
M_data[14..27]  ← TFA16: same structure
M_data[28..41]  ← TFA17: same structure
M_data[42..50]  ← LuaBuffVar[30..38]: setpoints, BMS modes, ON/OFF trackers
                   (= P3.LBI slots 31–39 from LuaBuffVar directly)
```

---

### C.10  ParamMap Firmware Functions — Summary

| Function | What It Does |
|---|---|
| `PConfig_FileRead()` | Parses all P1–P3, JKY, JKC, NTC, MST into structs |
| `PConfig_FileCheck()` | Validates NMD = Σ(JKA keys×names); hard fails if mismatch |
| `Map_LuaBuffVarSync()` | Background sync: reads all read-FC Modbus params into LuaBuffVar[]; skips write-FC params |
| `Map_LuaBuffVarWriteWait()` | Called when Lua does `Buff_Write_Wait(LBI, val)`: gates on `LBI ≤ LBMPNum`, calls `Modbus_ParmWrite`, notifies Lua with result (1/3/4) |
| `Map_LuaBuffVarReadWait()` | Called when Lua does `Buff_Read_Wait(LBI)`: forces on-demand Modbus read, updates LuaBuffVar, notifies Lua |
| `Map_MdataBuffSync()` | Fills M_data[]: first from Modbus params, then from LuaBuffVar[LBI-1] |
| `Map_LuaBuffValUpdate()` | Direct RAM write to LuaBuffVar[LBI-1]; called by `CmdID_Handler` for RPC writes |
| `CmdID_Handler()` | Handles Script.Cmd RPC: validates `1 ≤ CmdID ≤ p_LBRPCNum`, calls `Map_LuaBuffValUpdate` |
| `MQTT_JSON_Payload_WJ()` | Builds the cloud JSON from JKA structure + M_data[] sequentially |

---

## PART D — MainScript.lua

### D.1  Purpose and Structure

MainScript.lua has three sections:
1. **Constants and device tables** (top): defines all device indexes, structure type constants, and the device cluster tables that map Lua names to LBI slot numbers
2. **Initialization block** (`do...end`): runs once at boot — NVS restore, initial valve positioning
3. **Main loop** (`while true`): executes every second — action commands, TFA state machines, setpoint sync, debug output

---

### D.2  Device Index Constants

```lua
TFA15 = 1   TFA16 = 2   TFA17 = 3
```

These are the keys used to index every device cluster table. They match the parameter groupings in Modbus_Config.json.

---

### D.3  Device Structure Type Constants

```lua
Write  = 1   Stat   = 2   Keys   = 3
Speed  = 4   FBStat = 5
EnWrite = 6   EnStat = 7
```

These index the second dimension of every device cluster table. Each constant selects a different LBI slot for a different operation type on the same device.

| Constant | Meaning | LBI type |
|---|---|---|
| `Write` | Control output write (FC5/FC6) | Modbus write param |
| `Stat` | Feedback read (FC3/FC4) | Modbus read param |
| `Keys` | String label for debug display | Not an LBI slot — string value |
| `Speed` | Speed-specific write | Modbus write param |
| `FBStat` | Speed-specific feedback | Modbus read param |
| `EnWrite` | Enable coil write (FC5) | Modbus write param |
| `EnStat` | Enable discrete feedback (FC2) | Modbus read param |

---

### D.4  Device Tables (Valve, ECFan, SEN)

Each device cluster is a Lua table indexed by [StructureType][DeviceIndex] → LBI slot number.

```lua
Valve[Write]   = { [TFA15]=1,  [TFA16]=7,  [TFA17]=13 }  -- P2.MPI→param 16,37,58 (FC6)
Valve[Stat]    = { [TFA15]=2,  [TFA16]=8,  [TFA17]=14 }  -- P2.MPI→param 12,33,54 (FC3)
Valve[Keys]    = { [TFA15]="TFA15-Valve", ... }

ECFan[Write]   = { [TFA15]=3,  [TFA16]=9,  [TFA17]=15 }  -- P2.MPI→param 17,38,59 (FC6)
ECFan[Stat]    = { [TFA15]=4,  [TFA16]=10, [TFA17]=16 }  -- P2.MPI→param 11,32,53 (FC4)
ECFan[EnWrite] = { [TFA15]=5,  [TFA16]=11, [TFA17]=17 }  -- P2.MPI→param 18,39,60 (FC5)
ECFan[EnStat]  = { [TFA15]=6,  [TFA16]=12, [TFA17]=18 }  -- P2.MPI→param 15,36,57 (FC2)

SEN[Stat]      = { [TFA15]=20, [TFA16]=22, [TFA17]=24 }  -- P2.MPI→param 20,41,62 (FC3, RAT)
```

**Rule:** The LBI slot number in these tables must match the corresponding `P2.LBI` slot that maps to the intended B5 parameter. Wrong LBI → writes/reads the wrong Modbus register silently.

---

### D.5  LBI Table — NVS-Backed Slots

```lua
LBI = { [1]=31, [2]=32, [3]=33, [4]=34, [5]=35, [6]=36, [7]=37, [8]=38, [9]=39 }
```

These LBI slots (31–39) are NOT backed by Modbus. They live only in `LuaBuffVar[]` and NVS flash.

| LBI Index | Slot | NVS Key | Meaning |
|---|---|---|---|
| `LBI[1]` | 31 | `STP15` | TFA15 setpoint (raw × 10, e.g., 250 = 25.0°C) |
| `LBI[2]` | 32 | `BMS15` | TFA15 BMS mode (0=Manual, 1=AutoCool, 2=AutoHeat) |
| `LBI[3]` | 33 | `STP16` | TFA16 setpoint |
| `LBI[4]` | 34 | `BMS16` | TFA16 BMS mode |
| `LBI[5]` | 35 | `STP17` | TFA17 setpoint |
| `LBI[6]` | 36 | `BMS17` | TFA17 BMS mode |
| `LBI[7]` | 37 | — | TFA15 ON/OFF action state tracker (cloud visibility) |
| `LBI[8]` | 38 | — | TFA16 ON/OFF tracker |
| `LBI[9]` | 39 | — | TFA17 ON/OFF tracker |

These slots are visible in the cloud because P3.LBI = [31..39], and P3's PC3_LB entries map M_data[42..50] directly from `LuaBuffVar[30..38]`.

---

### D.6  NVS Key Naming Convention

```lua
NVS_VALR = { [TFA15]="VALR15", [TFA16]="VALR16", [TFA17]="VALR17" }
```

| NVS Key | Value Stored | Purpose |
|---|---|---|
| `STP15/16/17` | Setpoint × 10 integer | Persists setpoint across reboot |
| `BMS15/16/17` | BMS mode 0/1/2 | Persists BMS mode across reboot |
| `VALR15/16/17` | Valve position % (0–100) | Persists last commanded valve position |

**Why persist valve position?** On reboot, the valve gets a close command by default (0%). Without restoring the last position, the room heats up uncontrolled between restart and the next cloud command. Restoring from NVS immediately positions the valve to its last known good state.

---

### D.7  State and Timer Variables

```lua
TFA_MD     = { [TFA15]=0, [TFA16]=0, [TFA17]=0 }  -- 0=idle, 1=ON seq, 2=OFF seq
VAL_PS     = { [TFA15]=0, [TFA16]=0, [TFA17]=0 }  -- last valve % (RAM, mirrors NVS)
ValPer_Var = { [TFA15]=0, [TFA16]=0, [TFA17]=0 }  -- valve % from auto-control logic
DT_Var     = { [TFA15]=0, [TFA16]=0, [TFA17]=0 }  -- last temp error (°C)
ST_PT      = { [TFA15]=0, [TFA16]=0, [TFA17]=0 }  -- working copy of setpoint
BMS_M      = { [TFA15]=0, [TFA16]=0, [TFA17]=0 }  -- working copy of BMS mode
ONC  = { 0, 0, 0 }   -- Once() state array (3 independent sequences)
DOEV = { 0, 0, 0 }   -- DoEvery() timestamp array (3 independent timers)
Cmd_Cnt = 0           -- current step in active command sequence (0=idle)
Seq_Set = 0           -- which TFA is currently running a sequence (0=none)
STATE_NEW = 1         -- CntrlDev4 state flag
FB_TYM = 5000         -- 5 second feedback timeout
```

---

### D.8  Initialization Block (Boot Sequence)

```lua
do
    delay(5000)                          -- wait 5s for slaves to be ready

    NVS_Read("STP15", LBI[1])           -- restore TFA15 setpoint → LuaBuffVar[30]
    NVS_Read("BMS15", LBI[2])           -- restore TFA15 BMS mode → LuaBuffVar[31]
    NVS_Read("STP16", LBI[3])           -- TFA16 setpoint
    NVS_Read("BMS16", LBI[4])
    NVS_Read("STP17", LBI[5])
    NVS_Read("BMS17", LBI[6])

    VAL_PS[TFA15] = NVS_GetVal("VALR15")
    VAL_PS[TFA16] = NVS_GetVal("VALR16")
    VAL_PS[TFA17] = NVS_GetVal("VALR17")

    -- Send each valve to its last known position using raw 0-1000 scale
    CntrlDev_NoFB2(Valve, TFA15, Write, Scale_Value(VAL_PS[TFA15], 0,100, 0,1000))
    CntrlDev_NoFB2(Valve, TFA16, Write, Scale_Value(VAL_PS[TFA16], 0,100, 0,1000))
    CntrlDev_NoFB2(Valve, TFA17, Write, Scale_Value(VAL_PS[TFA17], 0,100, 0,1000))
end
```

This block runs once. It uses `Buff_Write_Wait` (via `CntrlDev_NoFB2`) to do blocking Modbus writes, ensuring the valves actually receive the commands before the main loop starts.

---

### D.9  Main Loop Anatomy

```lua
while true do
    Act_Com()           -- 1. Process any pending cloud action command

    TFA_Logic(TFA15)    -- 2. Advance TFA15 ON/OFF sequence (if active)
    TFA_Logic(TFA16)    -- 3. Advance TFA16 ON/OFF sequence
    TFA_Logic(TFA17)    -- 4. Advance TFA17 ON/OFF sequence

    -- 5. Read setpoints and BMS modes from LuaBuffVar (NVS-backed slots)
    ST_PT[TFA15] = Buff_Read(LBI[1])   BMS_M[TFA15] = Buff_Read(LBI[2])
    ST_PT[TFA16] = Buff_Read(LBI[3])   BMS_M[TFA16] = Buff_Read(LBI[4])
    ST_PT[TFA17] = Buff_Read(LBI[5])   BMS_M[TFA17] = Buff_Read(LBI[6])

    if DoEvery(1, 2000) then           -- 6. Debug output every 2 seconds
        Disp_Dev(Valve, Stat, "TFA15_Valve")
        print("RAT TFA15: " .. Read_Val(SEN, TFA15, Stat))
        ...
    end

    if Script_Restart() then break end -- 7. Firmware-triggered script restart check
    Grb_collect()                      -- 8. Lua garbage collection
    delay(1000)                        -- 9. 1 second cycle time
end
```

**Loop ordering matters:**  
`Act_Com()` runs first so that any new cloud command sets `TFA_MD[tfa]` before `TFA_Logic()` checks it in the same cycle. This gives a one-cycle-maximum latency for command response.

---

## PART E — FuncScript.lua

### E.1  Function Index

| Function | Purpose |
|---|---|
| `Disp_Dev()` | Print cluster values to serial (debug) |
| `ARS_Resp()` | Compute Action Response Status code (0–6) |
| `CntrlDev4()` | Write + timed feedback check with state machine |
| `Read_Val()` | Simple buffer read shorthand |
| `Cmd_Seq3()` | Advance one step of a command sequence |
| `Cmd_Start()` | Begin a new command sequence |
| `Cmd_End()` | Terminate a completed sequence |
| `CntrlDev_NoFB2()` | Blocking write without feedback verification |
| `Act_Com()` | Parse and dispatch cloud action commands (Aid 1–18) |
| `Insrt_ActCom2()` | Conditionally execute an action if ID+value match |
| `ValWrt_Pt()` | Write setpoint to buffer + NVS |
| `ValWrt_bm()` | Write BMS mode to buffer + NVS (identical to ValWrt_Pt) |
| `NVS_Read()` | Read NVS key → write to LBI slot |
| `Once()` | Execute a block exactly once per condition |
| `DoEvery()` | Execute every N milliseconds |
| `Scale_Value()` | Linear interpolation: map x from [x1,x2] to [y1,y2] |
| `Limit()` | Clamp value to [l1, l2] |
| `Val_Set()` | Store valve %, write NVS, then call device write function |
| `ECFan_Enable_Direct()` | Direct FC5 write to enable coil for one TFA |
| `GetValvePercentage()` | Lookup table: temperature error → valve open % |
| `Valv_Logic()` | Temperature-based automatic valve control |
| `TFA_Valve_Control()` | High-level valve dispatch (checks AHU status first) |
| `TFA_Trig()` | Queue ON or OFF sequence for a TFA |
| `TFA_Enable()` | Immediately execute full TFA ON or OFF (no state machine) |
| `TFA_Logic()` | Per-loop advancement of ON/OFF sequence state machine |

---

### E.2  CntrlDev4 — Write With Timed Feedback Check

```lua
function CntrlDev4(cluster, clusterNum, clusterTP, clusterFB, val, exp_rslt, seq_tym)
```

| Parameter | Meaning |
|---|---|
| `cluster` | Device table (e.g., `Valve`, `ECFan`) |
| `clusterNum` | Device index (`TFA15`, `TFA16`, `TFA17`) |
| `clusterTP` | Trigger parameter type (`Write`, `EnWrite`) |
| `clusterFB` | Feedback parameter type (`Stat`, `EnStat`) |
| `val` | Raw value to write (0–1000 for valve/fan, 0/1 for coil) |
| `exp_rslt` | Expected feedback value after write |
| `seq_tym` | Timeout in ms to wait for feedback (`FB_TYM = 5000`) |

**State machine:**
```
STATE_NEW=1 → Write (Buff_Write_Wait), record millis(), STATE_NEW=0
While millis()-start < seq_tym → Buff_Read_Wait(clusterFB)
  If read ok AND value == exp_rslt → d_flg=1 (SUCCESS), STATE_NEW=1
  If read ok AND value ≠ exp_rslt → d_flg=2 (FAIL FB), STATE_NEW=1
  If timeout → d_flg=2 (FAIL TIMEOUT), STATE_NEW=1
Returns (d_flg, A_Flag)  -- 0=in-progress, 1=success, 2=fail
```

**vs CntrlDev_NoFB2:**

| | `CntrlDev4` | `CntrlDev_NoFB2` |
|---|---|---|
| Feedback check | Yes — timed, uses `Buff_Read_Wait` | No |
| Returns complete in one call? | No — must be called each loop while in-progress | Yes — blocking, returns immediately |
| Used for | Cloud action commands needing ARS feedback | ON/OFF sequences, boot init, auto-control |
| ARS result | Uses writeSt+fbSt | writeSt only (fbSt always 0) |

---

### E.3  Command Sequencing (Cmd_Seq3 / Cmd_Start / Cmd_End)

The three functions implement a step-by-step state machine for multi-step device operations. **Only one sequence can run at a time** (global `Cmd_Cnt` and `Seq_Set`).

```
Cmd_Start(tfa)   → sets Cmd_Cnt=1, Seq_Set=tfa (if Cmd_Cnt==0)
Cmd_Seq3(1,2,fn,...)  → if Cmd_Cnt==1: calls fn(); if fn returns ≠0: Cmd_Cnt=2
Cmd_Seq3(2,3,fn,...)  → if Cmd_Cnt==2: calls fn(); if fn returns ≠0: Cmd_Cnt=3
Cmd_Seq3(3,4,fn,...)  → if Cmd_Cnt==3: calls fn(); if fn returns ≠0: Cmd_Cnt=4
Cmd_End(4)       → if Cmd_Cnt==4: prints "End", resets Seq_Set=0, Cmd_Cnt=0
```

**ASCII Flow:**
```
Loop iteration N:
  TFA_Logic(TFA15): Cmd_Cnt=1 → Cmd_Seq3(1,2, CntrlDev_NoFB2, ECFan, TFA15, EnWrite, ON)
                    → CntrlDev_NoFB2 returns 1 (success) → Cmd_Cnt advances to 2

Loop iteration N+1:
  TFA_Logic(TFA15): Cmd_Cnt=2 → Cmd_Seq3(2,3, Val_Set, 100, CntrlDev_NoFB2, Valve, TFA15, Write, 100)
                    → returns 1 → Cmd_Cnt=3

Loop iteration N+2:
  TFA_Logic(TFA15): Cmd_Cnt=3 → Cmd_Seq3(3,4, CntrlDev_NoFB2, ECFan, TFA15, Write, 80)
                    → returns 1 → Cmd_Cnt=4
                    Cmd_Cnt==4 → TFA_MD[TFA15]=0, ARS_Stat(), Cmd_End(4) → resets

Each step takes at least 1 loop iteration (1 second) due to delay(1000) at end of loop.
```

**Rule:** `Seq_Set` locks out other TFAs from starting a sequence until the current one completes. `TFA_Logic(TFAxx)` returns immediately if `Seq_Set ≠ 0 AND Seq_Set ≠ tfa`.

---

### E.4  Act_Com() and Insrt_ActCom2() — Cloud Action Dispatch

`Act_Com()` is called every loop iteration and reads the pending action ID and value:

```lua
function Act_Com()
    local Aid = Read_ActCmdID()   -- returns Action_CmdID atomic (0 if none)
    local Aval = Read_ActCmdVal() -- returns Action_CmdVAL atomic
    if (Aid >= 1 and Aid <= 18) then
        Insrt_ActCom2(Aid, Aval, 1, Aval, Val_Set, ...)  -- Aid 1: TFA15 valve
        Insrt_ActCom2(Aid, Aval, 2, Aval, CntrlDev4, ...) -- Aid 2: TFA15 fan speed
        ...
    elseif (Aid ~= 0) then ARS_Stat(7)  -- invalid Aid
    end
end
```

**Action ID Map (TFA_15_16_17):**

| Aid | TFA | Action | Function Called | Modbus? | NVS? |
|---|---|---|---|---|---|
| 1 | TFA15 | Valve position (0–100%) | `Val_Set → CntrlDev4` | Yes (FC6) | Yes (VALR15) |
| 2 | TFA15 | Fan speed (0–100%) | `CntrlDev4` | Yes (FC6) | No |
| 3 | TFA15 | Fan enable (0/1) | `CntrlDev4` | Yes (FC5) | No |
| 4 | TFA16 | Valve position | `Val_Set → CntrlDev4` | Yes | Yes (VALR16) |
| 5 | TFA16 | Fan speed | `CntrlDev4` | Yes | No |
| 6 | TFA16 | Fan enable | `CntrlDev4` | Yes | No |
| 7 | TFA17 | Valve position | `Val_Set → CntrlDev4` | Yes | Yes (VALR17) |
| 8 | TFA17 | Fan speed | `CntrlDev4` | Yes | No |
| 9 | TFA17 | Fan enable | `CntrlDev4` | Yes | No |
| 10 | TFA15 | Setpoint (raw×10) | `ValWrt_Pt` | No | Yes (STP15) |
| 11 | TFA16 | Setpoint | `ValWrt_Pt` | No | Yes (STP16) |
| 12 | TFA17 | Setpoint | `ValWrt_Pt` | No | Yes (STP17) |
| 13 | TFA15 | BMS mode (0/1/2) | `ValWrt_bm` | No | Yes (BMS15) |
| 14 | TFA16 | BMS mode | `ValWrt_bm` | No | Yes (BMS16) |
| 15 | TFA17 | BMS mode | `ValWrt_bm` | No | Yes (BMS17) |
| 16 | TFA15 | Enable sequence (1=ON/0=OFF) | `TFA_Enable` | Yes (all 3 writes) | Yes (VALR15) |
| 17 | TFA16 | Enable sequence | `TFA_Enable` | Yes | Yes (VALR16) |
| 18 | TFA17 | Enable sequence | `TFA_Enable` | Yes | Yes (VALR17) |

`Insrt_ActCom2()` executes the function only when `Aid == AI_rslt AND Aval == AVAL_rslt`. If the function returns `rs ≠ 0`, it calls `ActCMD_Reset()` + `ARS_Stat(ARS_Resp(rs, fs))`. **If ActCMD_Reset is never called, the same action fires on every loop iteration.** Insrt_ActCom2 guarantees it resets after the first non-zero return.

---

### E.5  ValWrt_Pt and ValWrt_bm — NVS-Backed Writes

Both functions are identical in implementation:

```lua
function ValWrt_Pt(stp, nstr, lbi)      function ValWrt_bm(BMS_M, nstr, lbi)
    Buff_Write_NoWait(lbi, stp)              Buff_Write_NoWait(lbi, BMS_M)
    NVS_WriteInt(nstr, stp)                  NVS_WriteInt(nstr, BMS_M)
    return 1, 1                              return 1, 1
end                                      end
```

- **`Buff_Write_NoWait`** writes directly to `LuaBuffVar[lbi-1]` without blocking — no Modbus transaction
- **`NVS_WriteInt`** persists the value to ESP32 flash so it survives reboot
- Always return `1, 1` → `ARS_Resp(1,1) = 5` (Write OK, FB OK) — since there's no hardware to fail
- The separate naming (`Pt` = setPoint, `bm` = BMS mode) is for code readability only

---

### E.6  ARS Response System

**`ARS_Resp(writeSt, fbSt)` — Return Code Table:**

| writeSt | fbSt | ARS code | Meaning |
|---|---|---|---|
| 0 | 0 | **0** | In-progress (write still pending) |
| 1 | 0 | **1** | Write sent, feedback not yet verified |
| 2 | 0 | **2** | Write failed, no feedback attempted |
| 2 | 1 | **3** | Write failed, but feedback reported success |
| 2 | 2 | **4** | Write failed AND feedback failed |
| 1 | 1 | **5** | Write OK AND feedback confirmed ✓ (ideal outcome) |
| 1 | 2 | **6** | Write OK but feedback mismatch (hardware moved, sensor disagreed) |
| — | — | **7** | Invalid Action ID (Aid out of range 1–18) |

`ARS_Stat(code)` sends the code to the firmware's `LE.ARS_Stat` atomic. `main.cpp` reads this and calls `COM.SentARS_Payload()` to publish the ARS result to MQTT topic `CF.MQTTACT_PUB`.

**Modbus write result codes (from firmware → Lua):**

| Code | Constant | Firmware Status | Cause |
|---|---|---|---|
| 1 | `PKT_SUCC` | `WRITE_SUCCESS` | Write sent, readback matches |
| 2 | — | `READ_PARAM_NOT_FOUND` | paramID not in B6.WP (config error) |
| 3 | `PKT_VRFAIL` | `VERIFY_FAIL` | Write sent, readback ≠ written value |
| 4 | `PKT_FAIL` | `PACKET_FAIL` | No response or CRC error from slave |

---

### E.7  Valve Logic Chain

**`GetValvePercentage(DT)` — Temperature Error → Valve Open %:**

| DT (°C) | Valve % |
|---|---|
| ≥ 1.5 | 100% |
| 1.0 ≤ DT < 1.5 | 90% |
| 0.75 ≤ DT < 1.0 | 80% |
| 0.5 ≤ DT < 0.75 | 60% |
| 0.25 ≤ DT < 0.5 | 50% |
| −0.25 ≤ DT < 0.25 | 20% (minimum non-zero to prevent hunting) |
| DT < −0.25 | 0% |

`DT = RAT − setpoint_in_°C` — positive means room is warmer than setpoint (need more cooling).

**`Valv_Logic(tfa, stp, Tmpsen, BMS_M)` — Algorithm:**
1. `stp_f = stp / 10.0` → converts raw × 10 integer to real °C (e.g., 250 → 25.0)
2. `DT = Tmpsen - stp_f` → temperature error
3. `ValPer1 = GetValvePercentage(DT)` → target valve %
4. **Hysteresis on rising temp:** if `DT > 0 AND DT > DT_Var[tfa]` (temp rising), ramp `ValPer_Var` at +2%/cycle instead of jumping directly — prevents rapid oscillation
5. **On falling temp:** apply `ValPer1` directly (fast response to cool down)
6. `Limit(ValPer_Var, 0, 100)` → clamp
7. `CntrlDev_NoFB2(Valve, tfa, Write, Scale_Value(ValPer_Var, 0,100, 0,1000))` → write raw 0–1000

**`TFA_Valve_Control(tfa, stp, Tmpsen, BMS_M)` — Dispatch:**
- If `ECFan[EnStat][tfa] == OFF`: force valve to 0%, reset `ValPer_Var` (TFA is off — no cooling needed)
- If `BMS_M == 1 or 2` (auto modes): call `Valv_Logic()` → temperature-based control
- If `BMS_M == 0` (manual): skip valve logic entirely → cloud commands valve directly via Aid 1/4/7

---

### E.8  TFA ON/OFF State Machine — Three Levels

There are three ways to start a TFA enable/disable. They differ in how they execute:

| Function | How | Blocking? | State machine? | NVS? | Typical trigger |
|---|---|---|---|---|---|
| `TFA_Trig(tfa, mode)` | Queues mode in `TFA_MD[tfa]`, calls `Cmd_Start(tfa)` | No | Yes — `TFA_Logic` advances it | No | `Aid 16/17/18` (now commented out) |
| `TFA_Enable(tfa, mode)` | Executes all 3 steps immediately via `CntrlDev_NoFB2` | Yes — each step blocks | No | Yes (via Val_Set) | `Aid 16/17/18` (current) |
| `TFA_Logic(tfa)` | Advances `Cmd_Seq3` state machine step-by-step each loop | No | Yes | Yes (via Val_Set) | Called from main loop when `TFA_MD[tfa] ≠ 0` |

**TFA_Enable ON sequence** (immediate):
1. EC Fan Enable = ON (FC5, addr 301)
2. Valve = 100% via `Val_Set(100, CntrlDev_NoFB2, Valve, tfa, Write, 1000)` + saves VALR to NVS
3. Fan speed = 800 raw (80%) via FC6

**TFA_Enable OFF sequence** (immediate):
1. Valve = 0% + NVS VALR save
2. Fan speed = 0 (FC6)
3. EC Fan Enable = OFF (FC5)

**Both sequences also write to `LBI[6+tfa]` (`Buff_Write_NoWait`) to update the cloud tracker variable.**

---

### E.9  Utility Functions

**`Scale_Value(x, x1, x2, y1, y2)` — Linear Interpolation:**
```
y = ((x - x1) / (x2 - x1)) × (y2 - y1) + y1
```
Standard use: `Scale_Value(percent, 0, 100, 0, 1000)` → converts 0–100% to raw 0–1000.  
Example: `Scale_Value(75, 0, 100, 0, 1000)` = 750 raw → FC6 write → device positions valve at 75%.

**`Limit(x, l1, l2)` — Clamp:**  
Returns l1 if x < l1, l2 if x > l2, else x. Used to prevent valve from going below 0% or above 100%.

**`Once(seq, seg, cond)` — Single-shot execution:**  
- `seg=0` resets the sequence
- Returns `true` only the first time `cond` is true for a given `seg` value
- `ONC[seq]` tracks which segment last fired
- Used to trigger one-time actions inside continuous loops

**`DoEvery(seq, sq_dly)` — Timed execution:**  
- `DOEV[seq]` holds the last trigger timestamp in ms
- Returns `true` when `millis() - DOEV[seq] >= sq_dly`
- On true, resets the timestamp
- Debug output uses `DoEvery(1, 2000)` for 2-second intervals

**`Val_Set(valps, func, ...)` — Valve position persist wrapper:**  
Stores `valps` (0–100%) in `VAL_PS`, writes NVS key `"VALR"`, then calls `func(...)` with the remaining args. Used inside command sequences to save valve position alongside the Modbus write.

---

### E.10  Debug Utilities

**`Read_Val(cluster, clusterNum, clusterFB)`:**  
Shorthand for `Buff_Read(cluster[clusterFB][clusterNum])`. Returns the current value from `LuaBuffVar[]` (background-synced, not an on-demand read).

**`Disp_Dev(cluster, cluster_blk, Stname)`:**  
Sorts the device keys alphabetically, reads each LBI value from `LuaBuffVar[]`, prints as a comma-separated list. Used for serial monitor debugging.

---

## PART F — Complete Data Flow Diagrams

### F.1  Read Flow — Modbus Slave → Cloud MQTT

```
Physical Device (Modbus Slave)
│
│  RS485 Modbus RTU response (raw bytes)
▼
eModbusRTU_Loop() — polls READ-FC packets continuously (FreeRTOS task)
│
│  handleData(token, data[])
│  Stores: Reg[modbus_RegCalc(token) + i] = data[i]
│  Increments: BL3[slave].success_req
▼
Reg[] — flat array of NOR=63 floats (shared memory, atomic access)
│
│  Map_LuaBuffVarSync() — runs in background
│  For each PC2_MP slot (LBI 1–30):
│    LuaBuffVar[LBI-1] = Modbus_ParmRead(MPI)
│                      = modreg_Read(PN, STA, LN, FMT, MLT)
│                      = round(Reg[RegCalc(PN) + STA - pkt.SA], 2) × MLT
│  (SKIPS write-FC params to protect staged write values)
▼
LuaBuffVar[0..29] — background-synced, always fresh from last Modbus read
│
│  Lua calls Buff_Read(LBI) → LuaFunc_Read() → returns LuaBuffVar[LBI-1]
│  OR
│  Map_MdataBuffSync() — copies all 51 slots to M_data[]
│    M_data[0..41] ← Modbus_ParmRead(PC3_MP[i].p_MPI)
│    M_data[42..50] ← LuaBuffVar[PC3_LB[i].p_LBI - 1]
▼
M_data[0..50] — telemetry snapshot
│
│  MQTT_JSON_Payload_WJ(M_data, JKC, JKA, ...)
│  Iterates JKA → builds nested JSON → consumes M_data[] sequentially
▼
MQTT Broker (Cloud) — JSON payload published to CF.MQTT_Topic
```

---

### F.2  Write Flow — Cloud → Modbus → Verify → ARS Response

```
Cloud Platform
│
│  MQTT message to MQTTSUB_TOPIC
│  Payload: { "ACTION_CMD": "Aid", "Value": "Aval" }
▼
main.cpp: MQTT subscription callback
│  Input_CmdVariable(Aid, Aval) — sets Action_CmdID, Action_CmdVAL atomics
▼
Lua loop: Act_Com()
│  Read_ActCmdID() → Aid=1, Read_ActCmdVal() → Aval=75
│
│  Insrt_ActCom2(Aid=1, Aval=75, 1, 75, Val_Set, 75, CntrlDev4, Valve, TFA15, Write, Stat, 750, 75, 5000)
│    → Aid==1 AND Aval==75 → match!
│    → Val_Set(75, CntrlDev4, ...) → saves VAL_PS=75, writes NVS "VALR"=75
│    → CntrlDev4(Valve, TFA15, Write, Stat, 750, 75, 5000)
▼
CntrlDev4 (STATE_NEW=1):
│  Buff_Write_Wait(LBI=1, value=750)  → LuaFunc_WriteWait()
│    → LuaBuffVar[0] = 750
│    → LuaNotifyWriteWait = 1
│    → task blocks (xTaskNotifyWait)
▼
ParamMapConfig_Lib: Map_LuaBuffVarWriteWait()
│  LBI=1 ≤ LBMPNum=30 → Modbus-backed path
│  Calls Modbus_ParmWrite(paramID=16, writeData=750)
│    → Linear search B6.WP: WP[0]=16 ✓ → RP[0]=9
│    → Stage: Reg[RegCalc(pkt7)] = 750
│    → Send FC6 write packet (pkt 7, addr 4066, slave 1)
│    → Send FC3 read packet (pkt 2, addr 4066, slave 1)
│    → result = modreg_Read(pkt2, 4066, 1, 3, 1)
│    → if result == 750 → WRITE_SUCCESS(1) = PKT_SUCC
│    → if result ≠ 750 → VERIFY_FAIL(3) = PKT_VRFAIL
│    → if no response → PACKET_FAIL(4) = PKT_FAIL
│  xTaskNotify(Lua task, result)
▼
CntrlDev4 continues (STATE_NEW=0, within FB_TYM=5000ms):
│  Buff_Read_Wait(LBI=2) → reads valve FB (param 12, FC3, addr 1561)
│  if feedback == exp_rslt=75 → d_flg=1
│  if feedback ≠ exp_rslt → d_flg=2
│  if timeout → d_flg=2
▼
Insrt_ActCom2:
│  rs=1 (success) → ActCMD_Reset() → Action_CmdID=0
│  ARS_Resp(writeSt=1, fbSt=1) = 5
│  ARS_Stat(5) → LE.ARS_Stat = 5
▼
main.cpp reads LE.ARS_Stat:
│  SentARS_Payload(CF.MQTTACT_PUB, ..., LE.ARS_Stat=5, ...)
▼
Cloud Platform receives ARS_STAT payload: action_result=5 (Success)
```

---

### F.3  RPC / Script.Cmd Flow — Direct RAM Write (No Modbus)

```
Cloud Platform
│
│  MQTT message: Script.Cmd type with CmdID and CmdVal
│  Example: Set TFA15 setpoint → CmdID=1, CmdVal=250
▼
main.cpp: MQTT callback → RPC_Lib::CmdID_Handler(CmdID=1, CmdVal=250)
│  Validates: 1 ≤ CmdID ≤ p_LBRPCNum=9
│  Looks up: PC2_RPC[0].p_LBI = LBI slot 31
│  Calls: Map_LuaBuffValUpdate(LE, LBI=31, value=250)
│    → LuaBuffVar[30] = 250 (direct RAM write, NO Modbus, NO NVS)
▼
Lua reads Buff_Read(LBI[1]=31) → returns 250 from LuaBuffVar[30]
BUT: NVS is NOT updated — value lost on reboot

For persistent RPC commands, the Lua Act_Com path (Aid 10/11/12) uses
ValWrt_Pt() which writes BOTH to LuaBuffVar AND NVS.
```

> **Key difference between RPC (Script.Cmd) and ACTION_CMD:**  
> RPC = instant, no hardware transaction, not persistent, CmdID maps to RPCI  
> ACTION_CMD = goes through Lua Act_Com, may do Modbus writes, Lua decides NVS persistence  

---

### F.4  NVS Persist and Restore Flow

```
SETPOINT WRITE (via Action CMD, Aid 10):
  Cloud sends Aid=10, Aval=250
  → ValWrt_Pt(250, "STP15", 31)
    → Buff_Write_NoWait(31, 250)  [LuaBuffVar[30] = 250]
    → NVS_WriteInt("STP15", 250)  [flash: STP15=250]
  → Also updates M_data[42] via Map_MdataBuffSync → cloud sees new setpoint

REBOOT:
  delay(5000)
  NVS_Read("STP15", 31)
    → NVS_GetVal("STP15") = 250
    → Buff_Write_NoWait(31, 250)  [LuaBuffVar[30] = 250 restored]

VALVE POSITION WRITE (via Action CMD, Aid 1):
  Cloud sends Aid=1, Aval=75
  → Val_Set(75, CntrlDev4, ...)
    → VAL_PS = 75
    → NVS_WriteInt("VALR", 75)  [Note: uses generic "VALR" key in Val_Set]
  [Separately, NVS_VALR per-TFA keys "VALR15/16/17" are used at init time]

VALVE RESTORE (at boot):
  VAL_PS[TFA15] = NVS_GetVal("VALR15")
  CntrlDev_NoFB2(Valve, TFA15, Write, Scale_Value(VAL_PS[TFA15], 0,100, 0,1000))
```

---

## PART G — Rules & Constraints Quick Reference

| # | Rule | What Enforces It | What Breaks If Violated |
|---|---|---|---|
| 1 | `NOR = sum(all B4.NRT)` | `MBConfig_BlockAlloc` allocates Reg[NOR] | modreg_Read reads wrong Reg[] slots — silent wrong values |
| 2 | `NOP = count(B5.ID)` | `MBConfig_BlockAlloc` allocates BL5[NOP] | Array out of bounds or uninitialized params |
| 3 | `NPT = count(B4.SA)` | `MBConfig_BlockAlloc` allocates BL4[NPT], Pkt[NPT] | Missing or extra packets not processed |
| 4 | B4: READ-FC packets before WRITE-FC per slave | eModbusRTU_Loop skips write packets in polling | Write packets' Reg[] offsets miscalculated; staged write values corrupted |
| 5 | B5.PN must reference a valid B4 packet number | `MBConfig_FileRead` — silent if wrong | modreg_Read uses wrong packet offset → wrong Reg[] address |
| 6 | B5.STA must be within `[B4.SA, B4.SA + B4.NRT - 1]` | Not validated — silent | modreg_Read lands outside packet's Reg[] window |
| 7 | B5 array position = paramID (not B5.ID value) | Firmware indexes `BL5[paramID-1]` directly | If B5 is reordered, all param references must also be updated |
| 8 | B6.WP[i] and B6.RP[i] are same-index pairs | `Modbus_ParmWrite` uses index-matched lookup | Wrong verify-read param → always VERIFY_FAIL or reads wrong data |
| 9 | `NLB = count(P2.MPI) + count(P2.RPCI)` | `PConfig_FileRead` loop limit | LBI slots beyond NLB not allocated; Lua crashes on out-of-bounds |
| 10 | `NMD = Σ(JKA[i].keys × JKA[i].names)` | `PConfig_FileCheck` hard fails boot | Firmware refuses to start; device goes offline |
| 11 | P3.MPI order must match JKA M_data consumption order | Not validated — silent | Cloud receives mismatched values (e.g., temperature where ON/OFF expected) |
| 12 | `count(P3.MPI) + count(P3.LBI) = NMD` | Implied by PConfig_FileCheck | M_data slots missing or extra → JSON truncated or wrong data |
| 13 | LBI slots 1..len(MPI) are Modbus-backed; rest are NVS-backed | `PConfig_FileRead` loading loop boundary | Calling Buff_Write_Wait on NVS slot does nothing to hardware; no error |
| 14 | P2.MPI: Modbus-write params must be in B6.WP | `Modbus_ParmWrite` returns 2 if not found | Write silently fails with `READ_PARAM_NOT_FOUND(2)` |
| 15 | `len(NTC.SN) = len(NTC.MI) = len(NTC.MT)` | Loaded into SLDT[]; mismatch may cause crash | Cloud identity fields in JSON payload are wrong |
| 16 | B5.LN must match B5.FMT (LN=1 for 16-bit, LN=2 for 32-bit) | Not validated — silent | modreg_Read decodes 2 registers instead of 1 (or vice versa) — wrong value |

---

## PART H — Failure Conditions & Error Codes

### H.1  Boot Hard-Fail Conditions

| Condition | Firmware Check | Effect |
|---|---|---|
| `MBConfig_FileRead()` fails (file missing or JSON parse error) | `MB_CNF.MB_ERC != ERC_NONE` | Modbus setup skipped — no communication with any slave |
| `NMD ≠ Σ(JKA keys×names)` | `PConfig_FileCheck()` | ParamMap rejected — no cloud data published |
| `NOR > 1500` or `NPT > 150` or `NOP > 300` | `MBConfig_BlockAlloc()` | Memory allocation skipped — no Modbus |
| SPIFFS not mounted or file not found | `SPIFFS_begin()` | Config not loaded — fallback to defaults |

### H.2  Write Result Codes

| Code | Lua Constant | Meaning | Typical Cause |
|---|---|---|---|
| 1 | `PKT_SUCC` | Write confirmed | Write sent and readback matched |
| 2 | — | Param not writable | paramID not listed in B6.WP |
| 3 | `PKT_VRFAIL` | Readback mismatch | Slave accepted command but device didn't respond (mechanical issue) |
| 4 | `PKT_FAIL` | Packet failure | Slave offline, wrong baud rate, CRC error |

### H.3  ARS Response Codes

| Code | writeSt / fbSt | Meaning | Cause |
|---|---|---|---|
| 0 | 0/0 | In-progress | Action still executing |
| 1 | 1/0 | Write sent | Modbus write OK, FB not checked |
| 2 | 2/0 | Write failed | `PKT_VRFAIL` or `PKT_FAIL` from Modbus |
| 3 | 2/1 | Write failed + FB OK | Unusual — FB reported OK despite write fail |
| 4 | 2/2 | Write + FB both failed | Complete failure |
| 5 | 1/1 | **Full success** ✓ | Write OK + FB confirmed match |
| 6 | 1/2 | Write OK + FB mismatch | Hardware inconsistency (jammed valve, sensor fault) |
| 7 | —/— | Invalid Aid | Action ID not in range 1–18 |

### H.4  Common Mistakes → Symptom → Fix

| Mistake | Symptom | Fix |
|---|---|---|
| `B1.NOR ≠ sum(B4.NRT)` | All Modbus data wrong — values from wrong parameters | Recalculate NOR: add all NRT values |
| Write packet before read packet in B4 | Write staging Reg[] slot corrupted; reads wrong data | Reorder B4: all FC1/2/3/4 before FC5/6 per slave |
| `B5.STA` outside packet's address range | modreg_Read returns wrong register value | Check: `B4.SA ≤ B5.STA < B4.SA + B4.NRT` for every param |
| B6.WP listed param without matching B4 FC6/FC5 | `Modbus_ParmWrite` sends FC6/FC5 for a read-only register — slave error | Only add params with write FC to B6.WP |
| P3.MPI order doesn't match JKA order | Cloud shows mismatched data (e.g., temperature in valve FB position) | Reorder P3.MPI to match sequential JKA consumption |
| `P1.NMD ≠ Σ(JKA keys×names)` | Boot fails — device goes offline | Recompute NMD; add/remove JKA entries or P3 slots to match |
| Wrong LBI slot in Lua device table | Writes/reads wrong Modbus parameter | Cross-check: Lua LBI → P2.MPI → B5 param → B4 FC/SA |
| NVS key mismatch (e.g., "STP15" written but "STP1" read) | After reboot, setpoint always defaults to 0 | Verify exact key strings in ValWrt_Pt and NVS_Read match |
| `ActCMD_Reset()` never called | Same action fires every loop iteration | Ensure `Insrt_ActCom2` function returns `rs ≠ 0` eventually |
| `CntrlDev4` feedback never returns non-zero | State stuck, next loop iteration can't proceed | Check B5 param has correct FC type; ensure slave responds to read-back packet |
| FMT=3 (UINT16) with LN=2 | Two registers decoded as one 32-bit number — wrong value | Set LN=1 for any 16-bit FMT (3 or 8) |

---

## PART I — Step-by-Step: Creating Configs for a New Project

Use this guide when setting up a new installation from scratch. Follow in order.

**Step 1 — Identify all physical devices**  
List every Modbus slave, its address, the register/coil addresses it exposes, and whether you need to read or write each register.

**Step 2 — Fill B2 (serial settings)**  
Set `BR` to the baud rate all slaves use (they must all match) and `DF` to the parity format (usually "8E1" or "8N1"). Use the device's Modbus manual.

**Step 3 — Fill B3 (slave map)**  
Assign each slave an entry in `B3.SI` (its Modbus address). Write the starting packet number for each slave in `B3.SP`. If a device needs multiple packets, those packets must be contiguous in B4.

**Step 4 — Fill B4 (packet definitions)**  
For each slave, add packets in this order:
- All READ-FC packets first (FC1, FC2, FC3, FC4) — one row per address range
- All WRITE-FC packets last (FC5, FC6) — one row per writable register
Set `SA` (start address), `NRT` (how many registers/coils), `FC`, and `SID` (slave address) for each.  
**Record the NRT values — you will sum them for B1.NOR.**

**Step 5 — Calculate B1.NPT and B1.NOR**  
`NPT = total number of B4 packets (rows)`.  
`NOR = sum of all B4.NRT values`. Write these into B1.

**Step 6 — Fill B5 (parameter definitions)**  
For each individual register or coil you need, add one entry:
- `PN` = packet number from B4 that contains this register
- `STA` = the register address (must be within `[B4.SA, B4.SA + NRT - 1]`)
- `LN` = 1 for 16-bit registers, 2 for 32-bit
- `FMT` = pick from the FMT table (3=UINT16, 8=INT16, 1/2=FP32, etc.)
- `MLT` = scaling factor applied on read (0.1 for ÷10, 0.01 for ÷100, 1 for raw)
- `ID` = sequential number (label only — can be anything)

**Set B1.NOP = total count of B5 entries.**

**Step 7 — Fill B6 (write/read pairs)**  
For each writable parameter (FC5/FC6 type from B5), add its param number to `B6.WP`.  
For each WP, identify the corresponding read-back param (the FC3/FC1 register that echoes the written value) and add it to `B6.RP` at the **same index**.

**Step 8 — Validate B1**  
Double-check:
- `B1.NOS = count(B3.SI)`
- `B1.NPT = count(B4 rows)`
- `B1.NOP = count(B5 rows)`
- `B1.NOR = sum of all B4.NRT`

**Step 9 — Plan the LBI layout (P2)**  
Decide which Modbus params Lua needs to read/write:
- Assign paired write+read slots first (e.g., LBI 1 = valve WRITE param, LBI 2 = valve FB READ param)
- Add read-only sensor slots after that
- Add NVS-backed slots last (setpoints, modes, trackers)

Write `P2.MPI` = list of B5 param IDs (one per Modbus-backed LBI slot).  
Write `P2.RPCI` = sequential [1,2,3,...] for each NVS-backed slot.  
Write `P2.LBI` = sequential [1,2,...,NLB].

**Set P1.NLB = P1.NLBIN = len(P2.MPI) + len(P2.RPCI).**

**Step 10 — Plan the cloud output (JKA)**  
Design the JSON hierarchy you want the cloud to receive:
- Group devices by equipment type (EqType)
- For each EqType, list device names and the property key(s) each reports
- Count: `slots_for_this_entry = len(keys) × len(names)`
Sum all slot counts. This total = `NMD`.

**Step 11 — Fill P3 (M_data mapping)**  
Order `P3.MPI` entries to match JKA's sequential M_data consumption:
- For each JKA entry (in order), for each device name, for each key: the next P3.MPI slot must point to the B5 param that holds that value
- After all Modbus-backed entries, list `P3.LBI` = LBI slots to use for NVS-backed M_data slots

**Set P1.NMD = len(P3.MPI) + len(P3.LBI). Verify this equals the JKA sum from Step 10.**

**Step 12 — Write MainScript.lua device tables**  
For each device and operation type, create a cluster table with the corresponding LBI slot numbers from Step 9.  
Add NVS key strings matching the keys used in FuncScript.lua write/restore calls.

**Step 13 — Write FuncScript.lua Act_Com() dispatch**  
For each cloud action:
- Assign an Aid number (1–N)
- Choose the function to call (CntrlDev4 for Modbus writes, ValWrt_Pt for setpoints, ValWrt_bm for modes, TFA_Enable for full sequences)
- Pass the correct LBI slot, raw value (scale if needed with Scale_Value), and expected feedback

**Step 14 — Fill NTC and JKC**  
Set `JKC.JKH = "properties"` and `JKC.EKS = "DKEY"` (usually unchanged).  
Set `NTC.MI` = machine ID(s), `NTC.DI` = device ID, `NTC.SN` = slave counts. These will appear in the cloud JSON header.

**Step 15 — Final validation checklist before flashing**

- [ ] `B1.NOR` = exact sum of all B4.NRT — **recalculate manually**
- [ ] Every B4 FC5/FC6 packet comes after FC1/2/3/4 for its slave
- [ ] Every B5.STA is within its packet's address range
- [ ] Every B6.WP[i] has the matching read-back param at B6.RP[i]
- [ ] `P1.NMD` = `Σ(JKA keys × names)` = `len(P3.MPI) + len(P3.LBI)` — all three equal
- [ ] P3.MPI order matches JKA consumption order exactly
- [ ] Lua LBI slot numbers in device tables match P2.LBI → P2.MPI → B5 chain
- [ ] NVS key strings in Lua init and Act_Com match the keys in NVS_Read/ValWrt_Pt calls

---

*Document generated: 2026-05-03 | Reference project: TFA_15_16_17 (2nd Floor, PN_10)*

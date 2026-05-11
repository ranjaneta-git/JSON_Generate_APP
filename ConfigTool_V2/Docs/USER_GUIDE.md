# BMIoT ConfigTool v2.0 — User Guide

**Application Version:** 2.0  
**Who this is for:** Anyone configuring a BMIoT gateway — even if you have never used this tool before.  
**What it does:** Walks you through every step needed so the gateway knows how to talk to your Modbus devices, run control logic, and send data to the cloud.

---

## How the Tool Works — Big Picture

The tool generates two configuration files that are flashed onto the gateway:

| File | Purpose |
|---|---|
| `Modbus_Config.json` | Tells the gateway **which registers to read/write** on your devices (the Modbus communication side) |
| `ParamMap_Config.json` | Tells the Lua control script and cloud telemetry **how to use** those register values |

You fill in **9 steps** in order. Each step feeds the next. If you skip a step or fill it incorrectly the generated config will not work on the hardware.

---

## Step 1 — Project Settings

Set the **serial port parameters** for the Modbus RS-485 bus.

| Field | What to enter |
|---|---|
| Baud Rate | Must match all devices on the bus (e.g., 19200) |
| Data Format | Typically `8E1` or `8N1` — check your device manual |

**Rule:** Every slave on the same RS-485 bus must use the same baud rate and data format.

---

## Step 2 — Devices and Slaves

**Device** = a logical piece of equipment (e.g., one heat pump, one TFA unit).  
**Slave** = a Modbus node ID inside that equipment.

Most equipment exposes one slave. Some equipment (like a TFA unit with a separate sensor board) uses two slaves — you add both slaves under the same device so the tool knows they belong together.

**When to add multiple slaves under one device:**  
When one piece of physical equipment has two different Modbus addresses — e.g., the main control board at ID 1 and the sensor board at ID 2 both belong to TFA15.

**When to create a new device:**  
When it is a separate physical machine (e.g., TFA16 is different equipment from TFA15 even if both are TFA units).

---

## Step 3 — Registers

Each row in this table is one data point the gateway will poll or write on the RS-485 bus.

| Column | What to enter |
|---|---|
| Name | A human-readable label — used only in this tool and in Lua scripts |
| Address | The Modbus register address from the device datasheet |
| FC (Function Code) | How to read/write this register (see table below) |
| FMT (Format) | The data type of the register value (see table below) |
| Multiplier (MLT) | A scaling factor applied after reading (1.0 = no scaling, 0.1 = divide by 10) |

### Function Codes

| FC | Name | When to use |
|---|---|---|
| FC1 | Read Coils | Read a ON/OFF digital output (e.g., run status, relay state) |
| FC2 | Read Discrete Inputs | Read a ON/OFF digital input (e.g., a DI feedback signal) |
| FC3 | Read Holding Registers | Read a numeric value that is writable (most common — speed, temperature, etc.) |
| FC4 | Read Input Registers | Read a numeric value that is read-only from a sensor |
| FC5 | Write Single Coil | Send an ON/OFF command to a coil (e.g., enable/disable a digital output) |
| FC6 | Write Single Register | Send a numeric command (e.g., setpoint, speed reference) |

> **Tip:** If a register appears in a device datasheet as "Holding Register" → use FC3 for reading, FC6 for writing.  
> If it says "Coil" → use FC1 for reading, FC5 for writing.

### Data Formats (FMT)

| FMT | What it means | When to use |
|---|---|---|
| FMT3 | Unsigned 16-bit integer | Most common — digital statuses, percentages, RPM |
| FMT8 | Signed 16-bit integer | Temperatures that can be negative |
| FMT1 | Float32 (BA word order) | 32-bit floating point, low word first |
| FMT2 | Float32 (AB word order) | 32-bit floating point, high word first |

### About the Multiplier

The gateway stores all values as raw integers. If the device sends temperature as tenths of a degree (e.g., 235 means 23.5°C), set MLT = 0.1. The Lua script and cloud telemetry will then see 23.5.

---

## Step 4 — Link B (Write Feedback)

This step only applies if you have any **write registers** (FC5 or FC6).

**What is Link B?**  
When the gateway sends a write command (e.g., "Start the fan"), you can tell it which read register to check afterwards to confirm the hardware actually responded. This is called the **feedback register**.

Example:
- Write register: `FanEnable_Cmd` at FC6, address 4067 — sends the speed command
- Link B feedback: `EC_Fan_Fb` at FC4, address 4067 — reads back the actual reported speed

The gateway Lua script will know these two are a matched pair. If the feedback register never changes after a write, the Lua script can raise an alarm.

**When to set Link B:**
- Always set it when you have a physical output (valve, fan, relay) and a corresponding status/feedback input from the same device.

**When you can leave it as "None":**
- When there is no corresponding feedback signal in the device (e.g., a one-shot trigger with no readback).

> **Important:** The feedback register must already exist in Step 3 under the same device (can be on a different slave within the same device).

---

## Step 5 — LBI Slots (Lua Access)

**What is an LBI slot?**  
The Lua control script running on the gateway accesses register values through a numbered list called `LBI[]`. Think of it as a phone book — the Lua script dials a slot number to get the value of a register.

**The key rule:** A register can only be used in a Lua script **if it has an LBI slot assigned**. Registers without an LBI slot are still polled and sent to the cloud, but the Lua script cannot see them.

### Which registers get LBI slots automatically?

These are **always** given LBI slots — you cannot remove them:
1. Every **write register** (FC5/FC6) — because Lua needs to send commands
2. Every **Link B feedback register** — because Lua needs to check if the command worked

### Which registers do you need to check manually?

Any **read-only register** that your Lua control script needs at runtime. Ask yourself:

> *"Does my Lua script read this value to make a decision — like checking a temperature, a status bit, or a sensor reading?"*

- **Yes → check the box** (give it an LBI slot)
- **No, it's only for cloud reporting → leave it unchecked**

### Two types of registers to understand

| Type | Description | Needs LBI slot? |
|---|---|---|
| **Physical address register** | Directly maps to a Modbus register on the hardware. Has an FC, address, and MLT. The gateway polls this address on the RS-485 bus. | Only if Lua uses it |
| **Write + Link B pair** | A write register (command) paired with its feedback register. Both get LBI slots automatically. Lua uses these for command-and-confirm patterns. | Always automatic |

**Example:**
- `Valve_Fb` (FC3, address 1561, MLT=0.1) — read-only Modbus register. Appears in cloud telemetry. Check it only if Lua needs to read the valve position to decide something.
- `ValveCmd` (FC6, address 4066) + its Link B `Valve_Fb` — both get automatic LBI slots because Lua must issue the command and check the feedback.

---

## Step 6 — Cloud Groups (MQTT Telemetry)

This step defines what gets sent to the cloud via MQTT and how it is structured.

**What is a Cloud Group?**  
A cloud group is a named collection of register readings that gets published together as one MQTT message. The gateway Lua script collects the values and publishes them under the group's cluster name.

### Fields

| Field | What to enter |
|---|---|
| Cluster Name | A label for this group (e.g., `TFA15_DIE1`, `HP_Status`). This becomes the MQTT topic or key. |
| Keys | The measurement type labels — comma-separated (e.g., `St` for status, `DegC` for temperature, `per` for percentage) |
| Equipment Names | Comma-separated names of the individual readings in this group (e.g., `OFF, ON, Trip, Fire`) |
| Source Type | `Modbus` if values come from hardware registers; `NVS` if values come from cloud-pushed setpoints |

### How Keys and Equipment Names work together

The cloud receives a matrix of `[Equipment × Key]` pairs. For each combination you assign one register.

**Example:**
- Cluster: `TFA15_AIE1`
- Keys: `per`
- Equipment: `valve_Fb, EC_Fan_Fb`
- Result: Two readings sent per publish cycle → `valve_Fb.per` and `EC_Fan_Fb.per`

If you had two keys (`per, Hz`) and two equipment names (`Valve, Fan`), you would have four slots to fill (Valve.per, Valve.Hz, Fan.per, Fan.Hz).

### Order matters

All **Modbus groups must come before NVS groups** in the list. Use the ↑↓ buttons to reorder. The firmware processes groups in order when building the MQTT payload.

### When to use NVS groups

Only when the group contains setpoint values that are stored in flash (NVS). See Step 7 for the full explanation.

---

## Step 7 — NVS Setpoints

### What is NVS?

NVS stands for **Non-Volatile Storage** — it is a small section of flash memory on the gateway's ESP32 chip. Values written there survive power cuts and reboots.

### What is an NVS slot?

An NVS slot is a named variable stored in that flash memory. The cloud can push a new value (e.g., a new temperature setpoint), the gateway saves it to NVS, and even if power is lost the setpoint is remembered.

### When do you need NVS slots?

Add an NVS slot for every setpoint or configuration value that:
1. Is **sent from the cloud** (operator or BMS system pushes it down)
2. Must be **remembered after a reboot** (not just held in RAM)
3. Is **not a Modbus register** — it does not come from a sensor or device, it is a number that lives on the gateway itself

**Common examples:**
- Target supply air temperature setpoint (`Spt`)
- Enable/disable flags for features (`En`)
- BMS override values (`Bms`)

**When NOT to use NVS:**
- Do not use NVS for values that are read from hardware (those are Modbus registers, not NVS).
- Do not use NVS if the setpoint only needs to last until the next reboot (use a Lua variable instead).

### NVS Key Name

The key name is the identifier used in Lua scripts to read/write this slot. Keep it short (max 15 characters), no spaces. Convention: append the slot number to the name (e.g., `Spt31`, `Bms32`, `En37`).

### NVS and the LBI / P2 connection

NVS slots also get LBI slots — automatically placed at the end of the LBI list (after all Modbus write pairs and read registers). The `P2.RPCI` array in the generated ParamMap lists the LBI slot numbers that correspond to NVS slots. The Lua script reads NVS values via these LBI indices just like it reads Modbus registers.

---

## Step 8 — Network / MQTT

| Field | What to enter |
|---|---|
| Broker IP | The IP address or hostname of your MQTT broker server |
| Broker Port | TCP port — typically `1883` (unencrypted) or `8883` (TLS) |
| Client ID | A unique identifier for this gateway on the broker |
| Device ID (DI) | Short name for this gateway used in MQTT topic paths |
| Slave Numbers (SN) | The MQTT slave topic numbers this gateway subscribes to (usually `[1]`) |
| Machine IDs (MI) | Labels for the machines served by this gateway (e.g., `GWAY01`) |
| Machine Types (MT) | Type labels matching the machine IDs (e.g., `GWAY`) |

---

## How It All Connects — The Full Chain

```
Step 3: Registers
    ↓ defines all Modbus addresses and function codes
Step 4: Link B
    ↓ pairs each write command with its hardware feedback register
Step 5: LBI Slots
    ↓ marks which registers the Lua script can access by index
Step 6: Cloud Groups
    ↓ groups registers for MQTT telemetry publishing
Step 7: NVS
    ↓ adds cloud-settable setpoints that survive reboots
```

The generated files encode this chain:

```
Modbus_Config.json
  B4 → B5 → B6
  ↑         ↑
  Packets   Write+Read pairs (Link A = auto, same address)

ParamMap_Config.json
  P2.MPI  → write/feedback pairs (Link B) + Lua-accessible reads + NVS
  P3.MPI  → cloud group register IDs (JKA)
  P2.RPCI → LBI slot numbers of NVS setpoints
```

---

## Understanding the Generated File Sections

You don't normally edit these directly, but knowing what they mean helps you debug.

### Modbus_Config.json

| Section | What it contains |
|---|---|
| B1 | Summary counts — NOS (slaves), NOP (parameters), NPT (packets), NOR (registers) |
| B2 | Baud rate and data format |
| B3 | Slave IDs (SI) and the parameter offset where each slave's registers start (SP) |
| B4 | Packet table — each row is one RS-485 poll/write transaction (address, register count, FC, slave ID) |
| B5 | Parameter table — every individual register gets a unique ID with address, packet number, length, format, and multiplier |
| B6 | Write pairs — for each write register (WP), the read register to verify it (RP) using the same address and complementary FC |

#### B6 in plain terms

B6 answers: *"After I write to register X, which register do I read back to check it worked?"*

- `WP` = list of write register param IDs (FC5 or FC6 registers)
- `RP` = list of corresponding read-back register param IDs (same address, FC1 for FC5 writes, FC3 for FC6 writes)
- The firmware uses this for its polling confirmation loop — it is generated **automatically** from your Link B assignments. You do not fill this in manually.

### ParamMap_Config.json

| Section | What it contains |
|---|---|
| P1 | Summary — NLB (total LBI slots), NLBIN (read LBI slots), NMD (total cloud data items) |
| P2 | The LBI slot table — maps Lua array indices to parameter IDs |
| P3 | The cloud telemetry table — maps MQTT payload positions to parameter IDs |
| JKY.JKA | Cloud group definitions (name, keys, equipment names) |
| NTC | MQTT network config (IP, port, client ID, etc.) |
| MST | Miscellaneous settings (profile number) |

#### P2 in plain terms

P2 is the **Lua phone book** — it tells the Lua script which register value lives at which LBI index.

- `LBI` = the slot numbers (1, 2, 3 … always sequential)
- `MPI` = the parameter ID (from B5) at each LBI slot
- `RPCI` = which LBI slot numbers hold NVS setpoint values

The LBI slot list is built in this order:
1. **Write + Link B pairs** — first (slots 1 to 2×N where N = number of write registers). Each pair takes two consecutive slots: slot 2k-1 = write register, slot 2k = its Link B feedback.
2. **Additional read registers** you checked in Step 5 (`needs_lbi_slot`) — next, in the order they appear in your register list.
3. **NVS setpoints** — last. RPCI lists these slot numbers.

> **Why does the write register always come before its Link B feedback in the pair?**  
> Because the Lua script uses the pattern: `LBI[odd_slot]` = command value to write, `LBI[odd_slot+1]` = status to read back. This pairing is fixed by convention.

#### P3 in plain terms

P3 is the **cloud telemetry order** — it tells the firmware which register values to put into the MQTT payload and in what order.

- `MDI` = position in the MQTT payload (1, 2, 3 … always sequential)
- `MPI` = the parameter ID (from B5) at each position
- `LBI` = which LBI slot numbers correspond to NVS setpoints in the cloud payload

The order follows your **cloud group list from Step 6** exactly — group 1's registers first, then group 2's, and so on. Within each group, the order is: for each equipment name, for each key — which matches how the JKA consumer in the firmware unpacks the payload.

---

## Quick Decision Guide

| Situation | What to do |
|---|---|
| Register I only want to read for cloud telemetry, not for Lua | Add it in Step 3, skip LBI in Step 5, add it to a cloud group in Step 6 |
| Register Lua needs to check at runtime (e.g., a status or sensor) | Add in Step 3, **check LBI** in Step 5 |
| Register Lua writes to hardware (e.g., start command) | Add with FC5/FC6 in Step 3 — LBI is automatic |
| Feedback signal after a write command | Add with FC1/FC2/FC3/FC4 in Step 3, assign it in Link B Step 4 — LBI is automatic |
| Setpoint the cloud can change, gateway remembers it after reboot | Add an NVS slot in Step 7 — LBI is automatic |
| Setpoint the cloud can change, only until next reboot | Use an NVS slot anyway — it's simpler and safer |
| Two Modbus addresses in one piece of equipment | Add two slaves under the same device in Step 2 |
| Two physically separate machines | Add two separate devices in Step 2 |

---

## Common Mistakes to Avoid

1. **Wrong address** — Always use the address from the device datasheet. Some manuals list addresses starting from 1, some from 0. Check which convention the device uses and be consistent.

2. **Wrong FC for a write** — FC6 is for holding registers (numeric values). FC5 is for coils (ON/OFF). Using FC6 on a coil address will fail silently on some devices.

3. **Link B pointing to a wrong slave** — The Link B feedback register must be under the same device as the write register (can be a different slave within the device, not a different device).

4. **Forgetting to check LBI for a sensor Lua needs** — If the Lua script tries to read a register that has no LBI slot, it will get zero or stale data. Always tick the LBI box for every register your control logic reads.

5. **NVS groups listed before Modbus groups** — The tool enforces that all Modbus cloud groups must come before NVS cloud groups. Use the ↑↓ buttons to fix the order before generating.

6. **Cloud group key/equipment count mismatch** — The number of registers you assign must exactly equal (number of keys) × (number of equipment names). If you have 2 keys and 3 equipment names, you need 6 register slots.

7. **Duplicate Modbus slave IDs** — Each slave must have a unique ID on the RS-485 bus. Duplicate IDs cause collisions and unpredictable readings.

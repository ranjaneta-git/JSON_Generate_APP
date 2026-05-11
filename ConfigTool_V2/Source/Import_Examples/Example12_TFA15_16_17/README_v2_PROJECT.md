# TFA15 / TFA16 / TFA17 — BMIoT ConfigTool v2 Example Project

## File
`TFA15_16_17.bmiot_project` — open this in **BMIoT_ConfigTool_v2**

## What It Generates

Clicking **Generate JSON Files** on Step 10 produces all **4 output files**:

| File | Description |
|------|-------------|
| `Modbus_Config.json` | Modbus polling config — 6 slaves, 54 params, 24 packets |
| `ParamMap_Config.json` | Cloud/LBI mapping — 18 LBI slots, 45 cloud params |
| `MainScript.lua` | Lua main script with all 6 cluster tables and init block |
| `FuncScript.lua` | Standard functions library + generated Act_Com() (9 Actions) |

## Hardware Configuration

| Slave ID | Device | Description |
|----------|--------|-------------|
| 1 | TFA15 FCU | Digital/discrete/holding registers + coil writes |
| 2 | TFA15 Sensors | Return air humidity, return air temp, supply air temp |
| 3 | TFA16 FCU | Same register layout as SID 1 |
| 4 | TFA16 Sensors | Same as SID 2 |
| 5 | TFA17 FCU | Same register layout as SID 1 |
| 6 | TFA17 Sensors | Same as SID 2 |

- **Baud rate**: 19200, **Format**: 8E1

## Lua Action Commands (MQTT)

| Aid | Action | Description |
|-----|--------|-------------|
| 1 | TFA15 Valve | Set valve position 0–100% (scaled to 0–1000 register value) |
| 2 | TFA15 FAN | Set fan speed 0–100% |
| 3 | TFA15 ENAB | Enable (Aval=1) / Disable (Aval=0) |
| 4 | TFA16 Valve | Same as Aid 1 for TFA16 |
| 5 | TFA16 FAN | Same as Aid 2 for TFA16 |
| 6 | TFA16 ENAB | Same as Aid 3 for TFA16 |
| 7 | TFA17 Valve | Same as Aid 1 for TFA17 |
| 8 | TFA17 FAN | Same as Aid 2 for TFA17 |
| 9 | TFA17 ENAB | Same as Aid 3 for TFA17 |

## Lua Clusters

| Cluster | Device Aliases | Purpose |
|---------|---------------|---------|
| `Valve1` | `TFA15_Act` (Write=LBI2, Stat=LBI6), `TFA15_FAN` (Write=LBI3, Stat=LBI5) | TFA15 valve + fan control |
| `PPM1`   | `TFA15_ENAB` (Write=LBI1, Stat=LBI4) | TFA15 enable/disable |
| `Valve2` | `TFA16_Act` (Write=LBI8, Stat=LBI12), `TFA16_FAN` (Write=LBI9, Stat=LBI11) | TFA16 valve + fan control |
| `PPM2`   | `TFA16_ENAB` (Write=LBI7, Stat=LBI10) | TFA16 enable/disable |
| `Valve3` | `TFA17_Act` (Write=LBI14, Stat=LBI18), `TFA17_FAN` (Write=LBI15, Stat=LBI17) | TFA17 valve + fan control |
| `PPM3`   | `TFA17_ENAB` (Write=LBI13, Stat=LBI16) | TFA17 enable/disable |

## Steps to Use

1. Open **BMIoT_ConfigTool_v2.exe**
2. **File → Open Project** → select `TFA15_16_17.bmiot_project`
3. Review the pre-filled data on each step (Project Info → Network → Devices → etc.)
4. On **Step 9 (Lua Scripts)**: the Lua config is already populated
5. On **Step 10 (Generate)**: click **Generate JSON Files**
6. All 4 files appear in the preview tabs; use **Save Files** to write them to disk

## NVS / Valve Position
- On startup, the last saved valve position is restored from NVS key `VALR`
- Only TFA15's Valve1 position is restored (TFA16/17 start at 0)
- Valve positions are saved automatically when Aid 1, 4, or 7 is executed

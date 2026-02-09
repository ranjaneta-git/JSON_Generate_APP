# Example6 - Complete Configuration Set
**Chiller Control System with 21 Parameters**

## Overview
This example demonstrates a chiller control system with:
- **21 parameters** across **3 slaves** (IDs: 1, 2, 3)
- **9 communication packets** at **9600 baud**
- **6 write parameters** (IDs: 7-12) with **6 feedback parameters** (IDs: 1-6)
- **13 cloud-mapped parameters** organized by equipment groups
- **19 Lua buffer parameters** for local processing

## Equipment Configuration
- **CH1_DIE1**: Digital Input - Cr1 (Current sensor)
- **CH1_DIE2**: Digital Input - PP, SP (Pump status indicators)
- **CH1_DIE3**: Digital Input - SAC1, SAC2, SAC3 (Safety controls)
- **CH1_AIE1**: Analog Input - Tank_T (Tank temperature, 0.1 multiplier)
- **CH1_DIE4**: Digital Input - AM1, AM2 (Alarm monitors)
- **CH1_AIE2**: Analog Input - Spt, DltPt (Setpoint and delta)
- **CH1_DIE5**: Digital Input - CH1_Mode (Operating mode)
- **CH1_DIE6**: Digital Input - CH1_Cmd (Command status)

## Files in this Example

### 1. Modbus_Config.json
Contains the Modbus communication structure (B1-B6 blocks).

### 2. ParamMap_Config.json
Contains the parameter mapping for Lua buffer, cloud, and JSON structure (P1-P3, JKY, NTC, MST blocks).

### 3. Register_Config.json
Contains the complete register table with all 21 parameters including:
- Basic Modbus fields (slave_id, fc, address, length, fmt, multiplier)
- Access control (access, parameter_type, write_param_id, feedback_param_id)
- Cloud mapping (cloud, json_group, json_unit, json_key)
- Equipment hierarchy (equipment_group, device_name, equipment_type)
- Array membership (array_membership, p2_mpi_index, p3_mpi_index)
- Packet information (packet_num, packet_sa, packet_nrt)

## How to Use This Example

### Method 1: Import Modbus + ParamMap → Generate Register_Config
1. Open the application
2. File → Import Modbus/ParamMap
3. Select `Modbus_Config.json` and `ParamMap_Config.json`
4. Application generates all registers with metadata
5. Export → Register_Config.json

### Method 2: Import Register_Config → Generate Modbus + ParamMap
1. Open the application
2. File → Import Register Config
3. Select `Register_Config.json`
4. Application populates all 21 registers
5. Generate Configuration → Creates Modbus_Config.json and ParamMap_Config.json

## Key Features Demonstrated

### Mixed Function Codes
- **FC 1**: Read Coils (parameters 1-6, 13-20)
- **FC 3**: Read Holding Registers (parameter 21 at address 1561)
- **FC 5**: Write Single Coil (parameters 7-12)

### Write-Feedback Pairing
- Parameter 7 (write) ↔ Parameter 1 (feedback)
- Parameter 8 (write) ↔ Parameter 2 (feedback)
- Parameter 9 (write) ↔ Parameter 3 (feedback)
- Parameter 10 (write) ↔ Parameter 4 (feedback)
- Parameter 11 (write) ↔ Parameter 5 (feedback)
- Parameter 12 (write) ↔ Parameter 6 (feedback)

### Cloud Integration
- **MQTT Broker**: 18.191.222.62:1234
- **Client ID**: Lucas
- **Gateway ID**: GW01
- **13 cloud parameters** mapped to JKA equipment structure

### Special Characteristics
- **High address register**: Parameter 21 at address 1561 (non-contiguous addressing)
- **Decimal precision**: Parameter 21 uses 0.1 multiplier for temperature reading
- **Multi-slave communication**: 3 slaves with different addressing schemes
- **Packet optimization**: 8-register burst read (packet 8) for efficiency

## Validation Checkpoints

When importing or generating, verify:
- ✅ Total parameters: 21 (B1.NOP)
- ✅ Slave count: 3 (B1.NOS)
- ✅ Packet count: 9 (B1.NPT)
- ✅ Register count: 23 (B1.NOR - includes gaps)
- ✅ Write params: 6 (len(B6.WP))
- ✅ Feedback params: 6 (len(B6.RP))
- ✅ Cloud params: 13 (P1.NMD = len(P3.MDI))
- ✅ Lua buffer: 19 (P1.NLB = len(P2.LBI))
- ✅ JKA entries: 8 equipment groups

## Round-Trip Integrity

This example has been verified for 100% round-trip integrity:
```
Register_Config.json → Modbus + ParamMap → Register_Config.json
                    (exact match)

Modbus + ParamMap → Register_Config.json → Modbus + ParamMap
                    (exact match)
```

All B1-B6 and P1-P3 blocks are perfectly reconstructed in both directions.

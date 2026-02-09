==========================================
 VERIFIED IMPORT EXAMPLES
==========================================

These are production-verified JSON configurations that have been tested with 100% round-trip integrity.

EXAMPLE 1: Small Configuration (21 Parameters)
-----------------------------------------------
Location: Import_Examples\Example1_21params\
Files:
  - Modbus_Config.json
  - ParamMap_Config.json

Configuration Summary:
  - Parameters: 21
  - Slaves: 3 (IDs: 1, 2, 3)
  - Packets: 9
  - Baud Rate: 9600
  - Write Parameters: 6 (IDs: 7-12)
  - Feedback Parameters: 6 (IDs: 1-6)
  - Cloud Parameters: 9 (IDs: 13-21)
  - Pattern: Write-Verification pairing (6 pairs)

Equipment:
  - Digital Inputs: CH1_DIE1, CH1_DIE2, CH1_DIE3
  - Analog Inputs: CH1_AIE1, CH1_AIE2, CH1_AIE3, CH1_AIE4
  - Digital Outputs: CH1_DOE1, CH1_DOE2


EXAMPLE 2: Large Configuration (163 Parameters)
------------------------------------------------
Location: Import_Examples\Example2_163params\
Files:
  - Modbus_Config.json
  - ParamMap_Config.json

Configuration Summary:
  - Parameters: 163
  - Slaves: 13 (IDs: 1-13)
  - Packets: 82
  - Baud Rate: 38400
  - Write Parameters: 33
  - Feedback Parameters: 33
  - Cloud Parameters: 97
  - Pattern: Write-Verification pairing (33 pairs)

Equipment:
  - VFD Pumps: Cd_Pu1, Cd_Pu2, Cd_Pu3, PP_Pu1, PP_Pu2, PP_Pu3
  - Cooling Tower Fans: CT_Fn1, CT_Fn2
  - Chiller System: CH1 with multiple sensors
  - Sensors: Temperature, Pressure, Humidity, Flow, Alarms


EXAMPLE 6: Chiller Control System (21 Parameters)
--------------------------------------------------
Location: Import_Examples\Example6_21params\
Files:
  - Modbus_Config.json
  - ParamMap_Config.json

Configuration Summary:
  - Parameters: 21
  - Slaves: 3 (IDs: 1, 2, 3)
  - Packets: 9
  - Baud Rate: 9600
  - Write Parameters: 6 (IDs: 7-12)
  - Feedback Parameters: 6 (IDs: 1-6)
  - Cloud Parameters: 13 (MDI count)
  - Lua Buffer: 19 parameters
  - Pattern: Write-Verification pairing with chiller control

Equipment:
  - Digital Inputs: CH1_DIE1 (Cr1), CH1_DIE2 (PP/SP), CH1_DIE3 (SAC1/SAC2/SAC3)
  - Digital Inputs: CH1_DIE4 (AM1/AM2), CH1_DIE5 (CH1_Mode), CH1_DIE6 (CH1_Cmd)
  - Analog Inputs: CH1_AIE1 (Tank_T), CH1_AIE2 (Spt/DltPt)
  - Multi-value array parameters with equipment grouping
  - Cloud JSON structure with properties hierarchy (JKH/EKS)

Special Features:
  - Function Codes: FC 1 (coils), FC 3 (holding registers), FC 5 (write single coil)
  - Mixed register types: 8 coils, 1 holding register, 8 coils again
  - High address register: 1561 (parameter ID 21 with 0.1 multiplier)
  - MQTT connection: 18.191.222.62:1234 (Lucas client)


HOW TO IMPORT:
--------------
1. Open the application
2. Go to File → Import Modbus/ParamMap
3. Select the Modbus_Config.json file from the example folder
4. Select the ParamMap_Config.json file from the same folder
5. The application will populate all registers and generate the Register_Config.json
6. Verify the generated output matches the expected counts


VERIFICATION STATUS:
--------------------
✅ Both examples passed 100% round-trip validation
✅ All B1-B6 blocks correctly populated
✅ All P1-P3 blocks correctly populated
✅ Bidirectional flow verified (JSON ↔ Registers)
✅ Write-Verification pairing preserved
✅ Cloud parameter mapping validated
✅ Slave distribution maintained


VALIDATION TESTS:
-----------------
Test Date: February 6, 2026
Test Scripts:
  - V6.5_Version\test_roundtrip.py (Example 1)
  - V6.5_Version\test_large_config.py (Example 2)

All integrity checks passed:
  ✅ Parameter count match
  ✅ Slave count match
  ✅ B6.WP reconstruction
  ✅ B6.RP reconstruction
  ✅ P3.MPI cloud parameters
  ✅ Access mode distribution
  ✅ Packet distribution

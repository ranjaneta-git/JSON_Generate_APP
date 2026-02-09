#!/usr/bin/env python3
"""
Test script to verify output.json generation uses user-configured values
"""
import sys
import json

print('✓ Testing output.json generation with user-configured values...\n')

try:
    # Import the generate_output_json function
    import importlib.util
    spec = importlib.util.spec_from_file_location("app", "modbus_tkinter_app_v6.6_complete.py")
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    generate_output_json = app.generate_output_json
    
    print('  ✅ Module imported successfully\n')
except Exception as e:
    print(f'  ❌ Import failed: {e}')
    sys.exit(1)

# Create mock param_config
param_config = {
    'NTC': {
        'IP': '18.191.222.62',
        'PT': '1234',
        'CI': 'Lucas',
        'DI': 'OLD_DEVICE_01',  # This should NOT be used if device_id is provided
        'MI': ['SLAVE1', 'SLAVE2'],  # Array - should NOT be used for machineId
        'MT': ['GWAY', 'GWAY']
    }
}

# Create mock registers with cloud parameters
class MockRegister:
    def __init__(self, cloud, json_group, json_key, json_unit):
        self.cloud = cloud
        self.json_group = json_group
        self.json_key = json_key
        self.json_unit = json_unit

registers = [
    MockRegister(True, "AHU_RL_Mb1", "VFD", "Ar"),
    MockRegister(True, "AHU_RL_DIE1", "VFDTrip", "Tr"),
    MockRegister(True, "AHU_RL_Mb2", "VFD_Rhr", "Hour"),
    MockRegister(False, "CH1_Misc", "Temp", "DegC"),  # Not cloud-enabled, should be excluded
]

# Test 1: Generate with user-configured values
print('Test 1: Generate with user-configured machineId and deviceId')
print('=' * 70)
machine_id = "EnergyHive_Test"
device_id = "TSA_Serv1001"

output = generate_output_json(param_config, registers, machine_id, device_id)

print(f'\n✓ Generated output.json:')
print(json.dumps(output, indent=2))

# Verify structure
print('\n✓ Verification:')
checks = []

# Check machineId
if output.get('machineId') == machine_id:
    print(f'  ✅ machineId = "{machine_id}" (user-configured, NOT from NTC.MI)')
    checks.append(True)
else:
    print(f'  ❌ machineId mismatch: expected "{machine_id}", got "{output.get("machineId")}"')
    checks.append(False)

# Check deviceId
if output.get('deviceId') == device_id:
    print(f'  ✅ deviceId = "{device_id}" (user-configured, NOT NTC.DI)')
    checks.append(True)
else:
    print(f'  ❌ deviceId mismatch: expected "{device_id}", got "{output.get("deviceId")}"')
    checks.append(False)

# Check timestamp format (ISO 8601)
timestamp = output.get('timestamp', '')
if 'T' in timestamp and 'Z' in timestamp:
    print(f'  ✅ timestamp = "{timestamp}" (ISO 8601 format)')
    checks.append(True)
else:
    print(f'  ❌ timestamp format incorrect: "{timestamp}"')
    checks.append(False)

# Check responseStatus
if output.get('responseStatus') == 0:
    print(f'  ✅ responseStatus = 0 (success)')
    checks.append(True)
else:
    print(f'  ❌ responseStatus incorrect: {output.get("responseStatus")}')
    checks.append(False)

# Check responseString
if output.get('responseString', {}).get('MB') == 'OK':
    print(f'  ✅ responseString.MB = "OK"')
    checks.append(True)
else:
    print(f'  ❌ responseString.MB incorrect')
    checks.append(False)

# Check properties structure
properties = output.get('properties', {})
if properties.get('msgType') == 'NML_STAT':
    print(f'  ✅ properties.msgType = "NML_STAT"')
    checks.append(True)
else:
    print(f'  ❌ properties.msgType incorrect')
    checks.append(False)

if properties.get('autoShed') == 0:
    print(f'  ✅ properties.autoShed = 0')
    checks.append(True)
else:
    print(f'  ❌ properties.autoShed incorrect')
    checks.append(False)

# Check nested structure (only cloud-enabled params)
if 'AHU_RL_Mb1' in properties:
    print(f'  ✅ properties.AHU_RL_Mb1 exists')
    if 'VFD' in properties['AHU_RL_Mb1']:
        print(f'  ✅ properties.AHU_RL_Mb1.VFD exists')
        if 'Ar' in properties['AHU_RL_Mb1']['VFD']:
            print(f'  ✅ properties.AHU_RL_Mb1.VFD.Ar = {properties["AHU_RL_Mb1"]["VFD"]["Ar"]}')
            checks.append(True)
        else:
            print(f'  ❌ properties.AHU_RL_Mb1.VFD.Ar missing')
            checks.append(False)
    else:
        print(f'  ❌ properties.AHU_RL_Mb1.VFD missing')
        checks.append(False)
else:
    print(f'  ❌ properties.AHU_RL_Mb1 missing')
    checks.append(False)

# Check non-cloud param is excluded
if 'CH1_Misc' not in properties:
    print(f'  ✅ Non-cloud parameter excluded correctly')
    checks.append(True)
else:
    print(f'  ❌ Non-cloud parameter should not be in properties')
    checks.append(False)

# Test 2: Generate with defaults (no user values)
print('\n\nTest 2: Generate without user-configured values (use defaults)')
print('=' * 70)
output2 = generate_output_json(param_config, registers)

print(f'\n✓ Generated with defaults:')
print(f'  machineId: {output2.get("machineId")}')
print(f'  deviceId: {output2.get("deviceId")}')

if output2.get('machineId') == "EnergyHive_Test":
    print(f'  ✅ Default machineId used')
    checks.append(True)
else:
    print(f'  ❌ Default machineId incorrect')
    checks.append(False)

# Final result
print('\n' + '=' * 70)
if all(checks):
    print('🎉 ALL TESTS PASSED!')
    print('✅ machineId and deviceId are user-configurable')
    print('✅ Output JSON format matches expected structure')
    print('✅ Only cloud-enabled parameters included')
else:
    print(f'❌ Some tests failed: {checks.count(False)}/{len(checks)} failures')
    sys.exit(1)

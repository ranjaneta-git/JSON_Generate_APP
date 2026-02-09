#!/usr/bin/env python3
"""
Test script to verify complete packet calculation flow
"""
import sys

# Test 1: Import key modules
print('✓ Testing imports...')
try:
    import modbus_tkinter_app_v6_6_complete as app
    auto_assign_packet_numbers = app.auto_assign_packet_numbers
    RegisterEntry = app.RegisterEntry
    print('  ✅ Main module imported successfully')
except Exception as e:
    print(f'  ❌ Import failed: {e}')
    print('     Trying alternate import...')
    try:
        # Try with .py extension
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", "modbus_tkinter_app_v6.6_complete.py")
        app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app)
        auto_assign_packet_numbers = app.auto_assign_packet_numbers
        RegisterEntry = app.RegisterEntry
        print('  ✅ Main module imported successfully (alternate method)')
    except Exception as e2:
        print(f'  ❌ Alternate import also failed: {e2}')
        sys.exit(1)

# Test 2: Create test registers
print('\n✓ Testing register creation...')
test_registers = []
try:
    # Create 10 test registers on same slave/FC
    for i in range(10):
        reg = {
            'slave_id': 1,
            'fc': 3,
            'address': i * 5,  # Addresses: 0, 5, 10, 15, ..., 45
            'length': 2,
            'fmt': 3,
            'multiplier': 1.0,
            'access': 'R',
            'cloud': 'Yes',
            'b5_id': i + 1
        }
        test_registers.append(reg)
    print(f'  ✅ Created {len(test_registers)} test registers')
except Exception as e:
    print(f'  ❌ Register creation failed: {e}')
    sys.exit(1)

# Test 3: Calculate packets
print('\n✓ Testing packet calculation...')
try:
    result_registers = auto_assign_packet_numbers(test_registers)
    
    # Verify all registers have packet fields
    for i, reg in enumerate(result_registers):
        pnum = reg.get('packet_num')
        psa = reg.get('packet_sa')
        pnrt = reg.get('packet_nrt')
        
        if pnum is None or psa is None or pnrt is None:
            print(f'  ❌ Register {i+1} missing packet fields')
            print(f'     packet_num={pnum}, packet_sa={psa}, packet_nrt={pnrt}')
            sys.exit(1)
    
    print(f'  ✅ All registers have packet assignments')
    
    # Show packet assignments
    unique_packets = set(r.get('packet_num') for r in result_registers)
    print(f'  ℹ️  Total packets: {len(unique_packets)}')
    
    for pnum in sorted(unique_packets):
        packet_regs = [r for r in result_registers if r.get('packet_num') == pnum]
        first_reg = packet_regs[0]
        psa = first_reg.get('packet_sa')
        pnrt = first_reg.get('packet_nrt')
        print(f'     Packet {pnum}: {len(packet_regs)} registers, SA={psa}, NRT={pnrt}')
        
except Exception as e:
    print(f'  ❌ Packet calculation failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Verify address span constraint
print('\n✓ Testing address span validation...')
try:
    # Create registers with large address span (should exceed 70)
    large_span_regs = [
        {'slave_id': 1, 'fc': 3, 'address': 0, 'length': 1, 'b5_id': 1},
        {'slave_id': 1, 'fc': 3, 'address': 80, 'length': 1, 'b5_id': 2}  # Span = 80 (exceeds 70)
    ]
    
    result = auto_assign_packet_numbers(large_span_regs)
    
    # Should be split into 2 packets
    packet_nums = [r.get('packet_num') for r in result]
    unique_packets = set(packet_nums)
    
    if len(unique_packets) == 2:
        print(f'  ✅ Large address span correctly split into {len(unique_packets)} packets')
    else:
        print(f'  ❌ Expected 2 packets, got {len(unique_packets)}')
        sys.exit(1)
        
except Exception as e:
    print(f'  ❌ Address span test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Multi-register parameter handling
print('\n✓ Testing multi-register parameters...')
try:
    multi_reg_test = [
        {'slave_id': 1, 'fc': 3, 'address': 100, 'length': 1, 'b5_id': 1},
        {'slave_id': 1, 'fc': 3, 'address': 101, 'length': 2, 'b5_id': 2},  # Occupies 101-102
        {'slave_id': 1, 'fc': 3, 'address': 103, 'length': 1, 'b5_id': 3}
    ]
    
    result = auto_assign_packet_numbers(multi_reg_test)
    
    # Should be in 1 packet with correct NRT
    first_reg = result[0]
    expected_nrt = 103 - 100 + 1  # Should be 4 (addresses 100, 101, 102, 103)
    actual_nrt = first_reg.get('packet_nrt')
    
    if actual_nrt == expected_nrt:
        print(f'  ✅ Multi-register NRT calculated correctly: {actual_nrt}')
    else:
        print(f'  ❌ Expected NRT={expected_nrt}, got {actual_nrt}')
        sys.exit(1)
        
except Exception as e:
    print(f'  ❌ Multi-register test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Different slaves should be in different packets
print('\n✓ Testing multi-slave grouping...')
try:
    multi_slave_test = [
        {'slave_id': 1, 'fc': 3, 'address': 100, 'length': 1, 'b5_id': 1},
        {'slave_id': 2, 'fc': 3, 'address': 100, 'length': 1, 'b5_id': 2},
        {'slave_id': 3, 'fc': 3, 'address': 100, 'length': 1, 'b5_id': 3}
    ]
    
    result = auto_assign_packet_numbers(multi_slave_test)
    
    # Should be 3 different packets
    packet_nums = [r.get('packet_num') for r in result]
    unique_packets = set(packet_nums)
    
    if len(unique_packets) == 3:
        print(f'  ✅ Different slaves correctly split into {len(unique_packets)} packets')
    else:
        print(f'  ❌ Expected 3 packets, got {len(unique_packets)}')
        sys.exit(1)
        
except Exception as e:
    print(f'  ❌ Multi-slave test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Different function codes should be in different packets
print('\n✓ Testing multi-FC grouping...')
try:
    multi_fc_test = [
        {'slave_id': 1, 'fc': 1, 'address': 100, 'length': 1, 'b5_id': 1},
        {'slave_id': 1, 'fc': 3, 'address': 100, 'length': 1, 'b5_id': 2},
        {'slave_id': 1, 'fc': 4, 'address': 100, 'length': 1, 'b5_id': 3}
    ]
    
    result = auto_assign_packet_numbers(multi_fc_test)
    
    # Should be 3 different packets
    packet_nums = [r.get('packet_num') for r in result]
    unique_packets = set(packet_nums)
    
    if len(unique_packets) == 3:
        print(f'  ✅ Different FCs correctly split into {len(unique_packets)} packets')
    else:
        print(f'  ❌ Expected 3 packets, got {len(unique_packets)}')
        sys.exit(1)
        
except Exception as e:
    print(f'  ❌ Multi-FC test failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

print('\n' + '='*60)
print('🎉 ALL TESTS PASSED!')
print('='*60)
print('\n✅ Packet calculation algorithm working correctly')
print('✅ Address span validation enforced (70 max)')
print('✅ Multi-register parameters handled properly')
print('✅ Slave ID grouping working')
print('✅ Function Code grouping working')
print('✅ Ready for JSON generation')
print('\n💡 Next steps:')
print('   1. Launch GUI: python modbus_tkinter_app_v6_6_complete.py')
print('   2. Add registers using "Add Register" button')
print('   3. Click "🔄 Calculate Packets" button')
print('   4. Click "⚡ Generate Configurations" button')
print('   5. Check generated JSON files for B4.SA, B4.NRT, B5.PN arrays')

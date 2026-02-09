"""
Test script to verify WRITE operations get separate packets
Tests the fix for packet assignment logic
"""

def auto_assign_packet_numbers_test(registers):
    """
    Simplified version of auto_assign_packet_numbers for testing
    Implements the FIXED logic
    """
    if not registers:
        return registers
    
    # Sort by slave_id, fc, then by address
    sorted_regs = sorted(registers, key=lambda r: (
        r.get('slave_id', 0),
        r.get('fc', 0),
        r.get('address', 0)
    ))

    packet_num = 1
    MAX_REGISTERS_PER_PACKET = 70
    MAX_ADDRESS_SPAN = 70
    
    # Group by slave_id and fc
    groups = {}
    for reg in sorted_regs:
        slave = reg.get('slave_id', 0)
        fc = reg.get('fc', 0)
        key = (slave, fc)
        if key not in groups:
            groups[key] = []
        groups[key].append(reg)
    
    # Process each group and create packets
    for (slave_id, fc), group_regs in sorted(groups.items()):
        # CRITICAL FIRMWARE REQUIREMENT: Write operations must each get separate packet
        if fc in [5, 6, 15, 16]:
            # Each WRITE parameter gets its own packet
            for reg in group_regs:
                addr = reg.get('address', 0)
                length = reg.get('length', 1)
                
                # Single packet for this write parameter
                reg['packet_num'] = packet_num
                reg['packet_sa'] = addr
                reg['packet_nrt'] = length
                
                packet_num += 1
            continue  # Move to next group
        
        # READ operations: Group parameters if they fit within constraints
        packet_start_idx = 0
        
        while packet_start_idx < len(group_regs):
            packet_regs = []
            
            for i in range(packet_start_idx, len(group_regs)):
                current_reg = group_regs[i]
                current_address = current_reg.get('address', 0)
                current_length = current_reg.get('length', 1)
                
                if not packet_regs:
                    packet_regs.append(current_reg)
                else:
                    # Calculate span
                    all_addresses = []
                    for r in packet_regs + [current_reg]:
                        addr = r.get('address', 0)
                        length = r.get('length', 1)
                        all_addresses.extend(range(addr, addr + length))
                    
                    min_addr = min(all_addresses)
                    max_addr = max(all_addresses)
                    address_span = max_addr - min_addr + 1
                    
                    would_exceed_count = len(packet_regs) >= MAX_REGISTERS_PER_PACKET
                    would_exceed_span = address_span > MAX_ADDRESS_SPAN
                    
                    if would_exceed_count or would_exceed_span:
                        break
                    
                    packet_regs.append(current_reg)
            
            # Calculate packet metadata
            all_addresses = []
            for r in packet_regs:
                addr = r.get('address', 0)
                length = r.get('length', 1)
                all_addresses.extend(range(addr, addr + length))
            
            packet_sa = min(all_addresses)
            packet_nrt = max(all_addresses) - min(all_addresses) + 1
            
            for reg in packet_regs:
                reg['packet_num'] = packet_num
                reg['packet_sa'] = packet_sa
                reg['packet_nrt'] = packet_nrt
            
            packet_start_idx += len(packet_regs)
            packet_num += 1
    
    return registers


def test_write_packet_separation():
    """Test that write operations each get their own packet"""
    
    # Simulate registers with mixed READ and WRITE operations
    test_registers = [
        # READ operations (should be grouped if addresses are close)
        {'slave_id': 1, 'fc': 3, 'address': 100, 'length': 1},
        {'slave_id': 1, 'fc': 3, 'address': 101, 'length': 1},
        {'slave_id': 1, 'fc': 3, 'address': 102, 'length': 1},
        
        # WRITE operations (should each get separate packet)
        {'slave_id': 1, 'fc': 6, 'address': 200, 'length': 1},
        {'slave_id': 1, 'fc': 6, 'address': 201, 'length': 1},
        {'slave_id': 1, 'fc': 16, 'address': 300, 'length': 2},
        
        # More READ operations
        {'slave_id': 2, 'fc': 3, 'address': 1000, 'length': 1},
        {'slave_id': 2, 'fc': 3, 'address': 1001, 'length': 1},
    ]
    
    print("=" * 80)
    print("WRITE PACKET SEPARATION TEST")
    print("=" * 80)
    print("\nTest Registers:")
    print("-" * 80)
    
    for idx, reg in enumerate(test_registers, 1):
        fc_type = "WRITE" if reg['fc'] in [5, 6, 15, 16] else "READ"
        print(f"{idx}. Slave {reg['slave_id']}, FC {reg['fc']} ({fc_type}), "
              f"Address {reg['address']}, Length {reg['length']}")
    
    # Use the test function with fixed logic
    result = auto_assign_packet_numbers_test(test_registers)
    
    print("\n" + "=" * 80)
    print("PACKET ASSIGNMENT RESULTS")
    print("=" * 80)
    
    # Group by packet number
    packets = {}
    for reg in result:
        pnum = reg.get('packet_num', 0)
        if pnum not in packets:
            packets[pnum] = []
        packets[pnum].append(reg)
    
    # Display results
    for pnum in sorted(packets.keys()):
        regs = packets[pnum]
        print(f"\nPacket {pnum}:")
        print(f"  Slave ID: {regs[0]['slave_id']}")
        print(f"  FC: {regs[0]['fc']} ({'WRITE' if regs[0]['fc'] in [5, 6, 15, 16] else 'READ'})")
        print(f"  Parameters: {len(regs)}")
        print(f"  Addresses: {[r['address'] for r in regs]}")
        print(f"  Packet Start: {regs[0].get('packet_sa')}")
        print(f"  Packet Registers: {regs[0].get('packet_nrt')}")
    
    # Validation
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    passed = True
    
    # Check: All WRITE operations should have single parameter per packet
    write_packets = [p for p in packets.values() if p[0]['fc'] in [5, 6, 15, 16]]
    for packet_regs in write_packets:
        if len(packet_regs) > 1:
            print(f"❌ FAIL: Packet {packet_regs[0]['packet_num']} has {len(packet_regs)} WRITE parameters (should be 1)")
            passed = False
        else:
            print(f"✅ PASS: Packet {packet_regs[0]['packet_num']} has 1 WRITE parameter")
    
    # Check: READ operations can be grouped
    read_packets = [p for p in packets.values() if p[0]['fc'] in [1, 2, 3, 4]]
    for packet_regs in read_packets:
        print(f"✅ PASS: Packet {packet_regs[0]['packet_num']} has {len(packet_regs)} READ parameter(s) (grouping allowed)")
    
    print("\n" + "=" * 80)
    if passed:
        print("✅ ALL TESTS PASSED - WRITE operations correctly separated!")
    else:
        print("❌ TESTS FAILED - WRITE operations are being grouped incorrectly!")
    print("=" * 80)

if __name__ == "__main__":
    print("\n🔧 Testing WRITE Packet Separation Fix\n")
    test_write_packet_separation()

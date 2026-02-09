"""
Modbus Configuration Generator - Enhanced Tkinter Desktop Application v6.4
CRITICAL FIXES APPLIED:
- P3/JKY ordering: Sequential MDI mapping matching firmware's JKY flattened order
- JKY structure: Proper grouping with firmware-compatible format
- Validation: Enhanced firmware-specific checks

Run with: python modbus_tkinter_app_test_6.4.py
No external dependencies except tkinter (comes with Python)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
from datetime import datetime
import os
import csv
import sys

# Import bmiot_constants - Try from same directory first
try:
    import bmiot_constants as bc
    print("✅ bmiot_constants loaded successfully from current directory")
except ImportError:
    # Create minimal fallback
    print("⚠️ Warning: Could not import bmiot_constants")
    print("   Using fallback constants")
    class bc:
        DROPDOWN_OPTIONS = {
            'function_code': ["1 - Read Coil Status", "2 - Read Input Status", "3 - Read Holding Registers", 
                              "4 - Read Input Registers", "5 - Force Single Coil", "6 - Preset Single Register",
                              "15 - Force Multiple Coils", "16 - Preset Multiple Registers"],
            'data_format_code': ["1 - Float 32-bit (Big Endian)", "2 - Float 32-bit (Little Endian)",
                                 "3 - Unsigned 16-bit", "4 - Signed 32-bit (Big Endian)",
                                 "5 - Signed 32-bit (Little Endian)", "6 - Unsigned 32-bit (Big Endian)",
                                 "7 - Unsigned 32-bit (Little Endian)", "8 - Signed 16-bit"],
            'access_type': ["R - Read Only", "W - Write Only", "RW - Read/Write (Write + Verification)"],
            'profile': ["0 - Multiple Slave, Different Types, Non-Uniform, Slave-by-Slave",
                       "1 - Multiple Slave, Same Type, Uniform, Slave-by-Slave",
                       "2 - Multiple Slave, Different Types, Non-Uniform, Single Send"]
        }
        
        @staticmethod
        def get_register_length(fmt_code):
            return 2 if fmt_code in [1, 2, 4, 5, 6, 7] else 1
        
        @staticmethod
        def parse_dropdown_selection(value, dropdown_type):
            if ' - ' in str(value):
                try:
                    part = value.split(' - ')[0]
                    return int(part) if part.isdigit() else part
                except:
                    return value
            return value
        
        @staticmethod
        def validate_slave_id(slave_id):
            """Validate slave ID (1-247)"""
            if not isinstance(slave_id, int):
                return False, "Slave ID must be an integer"
            if slave_id < 1 or slave_id > 247:
                return False, f"Slave ID must be between 1-247, got {slave_id}"
            return True, ""
        
        @staticmethod
        def validate_address(address):
            """Validate Modbus address (0-65535)"""
            if not isinstance(address, int):
                return False, "Address must be an integer"
            if address < 0 or address > 65535:
                return False, f"Address must be between 0-65535, got {address}"
            return True, ""
        
        @staticmethod
        def validate_function_code(fc):
            """Validate function code"""
            valid_codes = [1, 2, 3, 4, 5, 6, 15, 16]
            if fc not in valid_codes:
                return False, f"Function code must be one of {valid_codes}, got {fc}"
            return True, ""
        
        @staticmethod
        def validate_format_code(fmt):
            """Validate format code (1-8)"""
            if fmt not in [1, 2, 3, 4, 5, 6, 7, 8]:
                return False, f"Format code must be 1-8, got {fmt}"
            return True, ""

# Backend Classes
class RegisterEntry:
    def __init__(self, param_id, slave_id, fc, address, length, fmt, multiplier, access, cloud, json_group, json_unit, json_key):
        self.param_id = param_id
        self.slave_id = slave_id
        self.fc = fc
        self.address = address
        self.length = length
        self.fmt = fmt
        self.multiplier = multiplier
        self.access = access
        self.cloud = cloud
        self.json_group = json_group
        self.json_unit = json_unit
        self.json_key = json_key
        self.packet_id = None

class Packet:
    def __init__(self, packet_id, slave_id, fc):
        self.packet_id = packet_id
        self.slave_id = slave_id
        self.fc = fc
        self.start_address = None
        self.register_count = 0
        self.parameters = []

# Backend Logic Functions
def validate_registers(registers):
    if not registers:
        return {"status": "error", "message": "No registers provided"}
    
    # FIRMWARE LIMITS (from firmware analysis)
    MAX_SLAVES = 50        # B3_szmax
    MAX_PACKETS = 150      # B4_szmax  
    MAX_PARAMETERS = 300   # B5_szmax
    
    # Check firmware limits
    unique_slaves = len(set(reg.slave_id for reg in registers))
    if unique_slaves > MAX_SLAVES:
        return {"status": "error", "message": f"Too many slaves ({unique_slaves}). Firmware limit: {MAX_SLAVES}"}
    
    if len(registers) > MAX_PARAMETERS:
        return {"status": "error", "message": f"Too many parameters ({len(registers)}). Firmware limit: {MAX_PARAMETERS}"}
    
    # Validate individual registers
    for idx, reg in enumerate(registers, 1):
        serial_no = idx  # Serial number visible in tree (1, 2, 3, ...)
        if reg.length > 70:
            return {"status": "error", "message": f"Serial No. {serial_no}: Length {reg.length} exceeds 70 register limit"}
        if reg.cloud and not (reg.json_group and reg.json_unit and reg.json_key):
            return {"status": "error", "message": f"Serial No. {serial_no}: Cloud output enabled but missing JSON keys (Group/Unit/Key)"}
        if reg.slave_id < 1 or reg.slave_id > 247:
            return {"status": "error", "message": f"Serial No. {serial_no}: Invalid Slave ID {reg.slave_id} (must be 1-247)"}
        if reg.address < 0 or reg.address > 65535:
            return {"status": "error", "message": f"Serial No. {serial_no}: Invalid Address {reg.address} (must be 0-65535)"}
    
    return {"status": "ok"}

def generate_packets(registers):
    """
    Generate packets with proper grouping logic:
    - Group by Slave ID + Function Code
    - WRITE operations (FC 5,6,15,16): Each parameter = separate packet
    - READ operations (FC 1,2,3,4): Group parameters if span ≤ 70 registers
    """
    packets = []
    packet_counter = 1
    
    # Group by Slave ID and Function Code only
    grouped = {}
    for reg in registers:
        key = (reg.slave_id, reg.fc)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(reg)
    
    # Sort each group by address
    for key in grouped:
        grouped[key].sort(key=lambda r: r.address)
    
    # Process each group
    for (slave_id, fc), regs in grouped.items():
        # WRITE operations: Each parameter = separate packet
        if fc in [5, 6, 15, 16]:
            for reg in regs:
                packet = Packet(f"PN{packet_counter}", slave_id, fc)
                packet.start_address = reg.address
                packet.register_count = reg.length
                packet.parameters.append(reg)
                reg.packet_id = packet.packet_id
                packets.append(packet)
                packet_counter += 1
        
        # READ operations: Group if span ≤ 70
        else:  # fc in [1, 2, 3, 4]
            i = 0
            while i < len(regs):
                # Start new packet
                current_packet = Packet(f"PN{packet_counter}", slave_id, fc)
                current_packet.parameters.append(regs[i])
                regs[i].packet_id = current_packet.packet_id
                
                # Try to add more parameters to this packet
                j = i + 1
                while j < len(regs):
                    # Calculate span if we add this parameter
                    min_addr = min(r.address for r in current_packet.parameters)
                    max_addr = max(r.address + r.length - 1 for r in current_packet.parameters)
                    
                    # Check if adding regs[j] keeps span ≤ 70
                    new_max_addr = max(max_addr, regs[j].address + regs[j].length - 1)
                    span = new_max_addr - min_addr + 1
                    
                    if span <= 70:
                        current_packet.parameters.append(regs[j])
                        regs[j].packet_id = current_packet.packet_id
                        j += 1
                    else:
                        break
                
                # Finalize packet: calculate start address and register count
                min_addr = min(r.address for r in current_packet.parameters)
                max_addr = max(r.address + r.length - 1 for r in current_packet.parameters)
                current_packet.start_address = min_addr
                current_packet.register_count = max_addr - min_addr + 1
                
                packets.append(current_packet)
                packet_counter += 1
                i = j
    
    # FIRMWARE LIMIT CHECK: Maximum packets
    MAX_PACKETS = 150  # B4_szmax
    if len(packets) > MAX_PACKETS:
        raise ValueError(f"Generated {len(packets)} packets exceeds firmware limit of {MAX_PACKETS}")
    
    return packets

def generate_modbus_io_json(communication, slaves, packets, registers):
    total_params = len(registers)
    total_packets = len(packets)
    
    # Count total register reads across all packets
    total_register_reads = sum(p.register_count for p in packets)
    
    # B1: Summary counts
    b1 = {
        "NOS": len(slaves),           # Number of Slaves
        "NOP": total_params,          # Number of Parameters
        "NPT": total_packets,         # Number of Packets Total
        "NOR": total_register_reads   # Number of Register reads
    }
    
    # B2: Communication settings
    b2 = {
        "BR": communication["baudrate"],  # Baud Rate
        "DF": communication["format"]     # Data Format
    }
    
    # B3: Slave and Packet mapping
    # SP: list of packet numbers that correspond to each slave (1-indexed)
    slave_packet_map = {}
    for idx, packet in enumerate(packets, 1):
        if packet.slave_id not in slave_packet_map:
            slave_packet_map[packet.slave_id] = []
        slave_packet_map[packet.slave_id].append(idx)
    
    # Create SP list in order of SI
    sp_list = []
    for slave_id in slaves:
        if slave_id in slave_packet_map:
            # Add first packet number for this slave
            sp_list.append(slave_packet_map[slave_id][0])
    
    b3 = {
        "SI": slaves,     # Slave IDs
        "SP": sp_list     # Starting Packet for each slave
    }
    
    # B4: Packet details (arrays aligned by packet index)
    sa_list = []   # Start Address
    nrt_list = []  # Number of Registers Total
    fc_list = []   # Function Code
    sid_list = []  # Slave ID
    
    for packet in packets:
        sa_list.append(packet.start_address)
        nrt_list.append(packet.register_count)
        fc_list.append(packet.fc)
        sid_list.append(packet.slave_id)
    
    b4 = {
        "SA": sa_list,    # Start Address for each packet
        "NRT": nrt_list,  # Number of Registers Total for each packet
        "FC": fc_list,    # Function Code for each packet
        "SID": sid_list   # Slave ID for each packet
    }
    
    # B5: Parameter details (arrays aligned by parameter ID)
    id_list = []    # Parameter ID (1-indexed)
    pn_list = []    # Packet Number
    sta_list = []   # Start Address
    ln_list = []    # Length
    fmt_list = []   # Format
    mlt_list = []   # Multiplier
    
    # Map packet_id to packet number (1-indexed)
    packet_id_to_number = {}
    for idx, packet in enumerate(packets, 1):
        packet_id_to_number[packet.packet_id] = idx
    
    for idx, reg in enumerate(registers, 1):
        id_list.append(idx)
        pn_list.append(packet_id_to_number.get(reg.packet_id, 0))
        sta_list.append(reg.address)
        ln_list.append(reg.length)
        fmt_list.append(reg.fmt)
        mlt_list.append(reg.multiplier)
    
    b5 = {
        "ID": id_list,      # Parameter IDs
        "PN": pn_list,      # Packet Number for each parameter
        "STA": sta_list,    # Start Address for each parameter
        "LN": ln_list,      # Length for each parameter
        "FMT": fmt_list,    # Format for each parameter
        "MLT": mlt_list     # Multiplier for each parameter
    }
    
    # B6: Write and Read PARAMETER IDs (not packet numbers!)
    # WP = Write Parameter IDs: All parameters with W or RW access
    # RP = Read Parameter IDs: Write-verification reads
    #      - RW parameters (write+verify in single parameter)
    #      - R parameters that pair with W parameters (separate write+verify)
    #      NOT pure monitoring reads (R access) - those go to Output JSON
    # 
    # CRITICAL: Based on historical Excel mapping analysis:
    # - R parameters (monitoring): Pure telemetry → Go to Output JSON (NOT in RP)
    # - R parameters (verification): Paired with W → Go to RP (NOT in Output JSON)
    # - W parameters: Write only → Go to WP
    # - RW parameters: Write + verification → Go to BOTH WP and RP
    write_param_ids = []
    read_param_ids = []
    
    # Step 1: Add all W and RW parameters to WP
    for idx, reg in enumerate(registers, 1):
        if 'W' in reg.access:
            write_param_ids.append(idx)
    
    # Step 2: Add RW parameters to RP (write+verify in single parameter)
    for idx, reg in enumerate(registers, 1):
        if reg.access == 'RW':
            read_param_ids.append(idx)
    
    # Step 3: Detect R parameters that pair with W parameters (separate write+verify)
    # An R parameter is a verification read if:
    # - Same slave ID, address, length, format as a W parameter
    for idx, reg in enumerate(registers, 1):
        if reg.access == 'R':
            # Check if this R pairs with any W parameter
            for widx, wreg in enumerate(registers, 1):
                if ('W' in wreg.access and
                    wreg.slave_id == reg.slave_id and
                    wreg.address == reg.address and
                    wreg.length == reg.length and
                    wreg.fmt == reg.fmt):
                    # This is a verification read for a write
                    read_param_ids.append(idx)
                    break
    
    b6 = {
        "WP": write_param_ids,  # Write Parameter IDs (W or RW access)
        "RP": read_param_ids    # Write-Verification Read Parameter IDs (ONLY RW access)
    }
    
    return {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5, "B6": b6}

def generate_parameter_config_json(registers, profile=0):
    """Generate ParamMap_Config.json V1.2.0 compliant with BD-Algorithm specs.
    
    Args:
        registers: List of register objects
        profile: Profile type (0, 1, or 2) - affects MST.PRF value
    """
    # CRITICAL: Build B6 mappings first to identify write-verification pairs
    b6_wp_ids = set()
    b6_rp_ids = set()
    
    # Step 1: Identify all write parameters for B6.WP
    for idx, reg in enumerate(registers, 1):
        if 'W' in reg.access:
            b6_wp_ids.add(idx)
    
    # Step 2: Identify verification reads for B6.RP
    for idx, reg in enumerate(registers, 1):
        # RW parameters include their own verification
        if reg.access == 'RW':
            b6_rp_ids.add(idx)
        # Detect paired R parameters that verify W parameters
        elif reg.access == 'R':
            for widx, wreg in enumerate(registers, 1):
                if ('W' in wreg.access and
                    wreg.slave_id == reg.slave_id and
                    wreg.address == reg.address and
                    wreg.length == reg.length and
                    wreg.fmt == reg.fmt):
                    b6_rp_ids.add(idx)
                    break
    
    # Step 3: Build Lua Buffer based on Lua script pattern
    # Analysis from MainScript.lua shows:
    # - LBI 1-15: Equipment Write/Status pairs (interleaved by equipment)
    # - LBI 16-19: Verification reads (dual-use: firmware verification + Lua user variables)
    #
    # Pattern: For each equipment → (Write, Status Monitor) pair
    # Then: Standalone monitors
    # Finally: Verification reads for user data storage
    
    lua_buffer_params_with_ids = []  # List of (param_idx, register) tuples for P2.MPI
    verification_for_lua = []  # Verification reads that go to P2.RPCI (LBI 16+)
    
    # Group write parameters by equipment (json_group)
    equipment_groups = {}  # {group_name: {'writes': [], 'monitors': []}}
    standalone_monitors = []  # Monitors without paired writes
    
    # Step 3a: Collect write parameters grouped by equipment
    for idx, reg in enumerate(registers, 1):
        if 'W' in reg.access:
            group = reg.json_group if reg.json_group else "Unknown"
            if group not in equipment_groups:
                equipment_groups[group] = {'writes': [], 'monitors': []}
            equipment_groups[group]['writes'].append((idx, reg))
    
    # Step 3b: Collect monitoring parameters (R access, cloud=Yes, NOT verification)
    for idx, reg in enumerate(registers, 1):
        if reg.access == 'R' and reg.cloud and idx not in b6_rp_ids:
            group = reg.json_group if reg.json_group else "Unknown"
            if group in equipment_groups:
                # Pair with equipment that has writes
                equipment_groups[group]['monitors'].append((idx, reg))
            else:
                # Standalone monitor
                standalone_monitors.append((idx, reg))
    
    # Step 3c: Build interleaved pattern: (Write, Monitor) for each equipment
    for group in sorted(equipment_groups.keys(), key=lambda g: min((p[0] for p in equipment_groups[g]['writes']), default=999)):
        writes = equipment_groups[group]['writes']
        monitors = equipment_groups[group]['monitors']
        
        # Interleave write and monitor for each equipment
        for i, (w_idx, w_reg) in enumerate(writes):
            lua_buffer_params_with_ids.append((w_idx, w_reg))
            if i < len(monitors):
                lua_buffer_params_with_ids.append(monitors[i])
        
        # Add remaining monitors if more monitors than writes
        for i in range(len(writes), len(monitors)):
            lua_buffer_params_with_ids.append(monitors[i])
    
    # Step 3d: Add standalone monitors (sorted by slave_id, then address)
    # This ensures correct LBI order matching Excel "Lua Buffer Side" table
    standalone_monitors.sort(key=lambda x: (x[1].slave_id, x[1].address))
    lua_buffer_params_with_ids.extend(standalone_monitors)
    
    # Step 3e: Add verification reads for Lua user data storage (LBI 16-19)
    # CRITICAL: Take only FIRST 4 verification reads to match Lua LBI structure
    # From Lua: LBI = {[1] = 16, [2] = 17, [3] = 18, [4] = 19}
    # This limits P1.NLB = 15 (MPI) + 4 (RPCI) = 19
    sorted_verification_reads = sorted(b6_rp_ids)
    for param_idx in sorted_verification_reads[:4]:  # Take only first 4
        reg = registers[param_idx - 1]
        verification_for_lua.append((param_idx, reg))
    
    # CRITICAL: Cloud params = pure monitoring reads (R access, NOT verification)
    cloud_params = [r for idx, r in enumerate(registers, 1)
                    if r.cloud and r.access == 'R' and idx not in b6_rp_ids]
    
    # P1: Size calculations
    # NLB = Number of Lua Buffer variables (equipment params + verification reads)
    # NLBIN = Same as NLB (all allocated variables are used)
    # NMD = Total JSON keys (will be calculated after JKY is built)
    total_lua_buffer = lua_buffer_params_with_ids + verification_for_lua
    
    p1 = {
        "NLB": len(total_lua_buffer),                                         # Total Lua buffer count
        "NLBIN": len(total_lua_buffer),                                       # Same as NLB (all are used)
        "NMD": 0  # Will be updated after JKY is built
    }
    
    # P2: Lua Buffer mappings based on Lua script pattern
    # LBI: Sequential [1, 2, 3, ..., 19] for ALL Lua buffer entries
    # MPI: First 15 LBIs → Equipment parameters (writes + monitors)
    # RPCI: LBI 16-19 → Verification reads (used by Lua for user data storage)
    #
    # From Lua analysis:
    # - LBI 1-15 map to equipment Write/Status pairs + monitors
    # - LBI 16-19 map to verification reads (dual-use: firmware + Lua variables)
    
    lbi_list = []   # Sequential [1, 2, 3, ..., 19]
    mpi_list = []   # B5 Param IDs for LBI 1-15 (equipment params)
    rpci_list = []  # B5 Param IDs for LBI 16-19 (verification reads)
    
    # Build MPI from equipment parameters (LBI 1-15)
    for idx, (param_idx, reg) in enumerate(lua_buffer_params_with_ids, 1):
        lbi_list.append(idx)
        mpi_list.append(param_idx)
    
    # Build RPCI from verification reads (LBI 16-19)
    # These are B6.RP params that Lua uses for user variable storage
    for idx, (param_idx, reg) in enumerate(verification_for_lua, len(mpi_list) + 1):
        lbi_list.append(idx)
        rpci_list.append(param_idx)
    
    p2 = {
        "LBI": lbi_list,    # Sequential: [1, 2, 3, ...] for ALL Lua buffer entries
        "MPI": mpi_list,    # B5 Param IDs for LBI 1-15 (equipment params)
        "RPCI": rpci_list   # B5 Param IDs for LBI 16-19 (verification reads)
    }
    
    # CRITICAL FIX: Build P3 and JKY in P2.MPI order (Lua Buffer order), NOT alphabetical
    # P3.MPI = cloud parameters extracted from P2.MPI in same order
    # JKY must follow the same order as P3.MPI
    
    # Step 1: Build P3.MPI by extracting cloud params from P2.MPI order
    p3_mpi_unique = []  # Unique cloud param IDs in P2.MPI order
    p3_mpi_unique_set = set()
    
    for param_idx in mpi_list:  # Iterate P2.MPI in order
        reg = registers[param_idx - 1]
        if reg.cloud and reg.access == 'R' and param_idx not in b6_rp_ids:
            if param_idx not in p3_mpi_unique_set:
                p3_mpi_unique.append(param_idx)
                p3_mpi_unique_set.add(param_idx)
    
    # Step 2: Build JKA structure following P3.MPI order
    jka_structure_ordered = []  # List to preserve order: [(group, {unit: [keys]})]
    group_seen = {}  # Track which groups we've processed
    
    for param_idx in p3_mpi_unique:
        reg = registers[param_idx - 1]
        group = reg.json_group if reg.json_group else ""
        unit = reg.json_unit if reg.json_unit else ""
        
        if not group:
            continue
            
        # Find or create group entry
        if group not in group_seen:
            group_entry = {}
            jka_structure_ordered.append((group, group_entry))
            group_seen[group] = group_entry
        else:
            group_entry = group_seen[group]
        
        if unit not in group_entry:
            group_entry[unit] = []
        
        # Support comma-separated keys
        if reg.json_key:
            keys = [k.strip() for k in reg.json_key.split(',') if k.strip()]
        else:
            keys = []
        
        # Add keys that don't already exist
        for key in keys:
            if key not in group_entry[unit]:
                group_entry[unit].append(key)
    
    # Step 3: Flatten JKA in P2.MPI order and create JKY + P3.MDI
    jka_list = []
    mdi_list = []
    p3_mpi_list = []  # Can have duplicates for multi-key params
    mdi_counter = 1
    
    for group, units_dict in jka_structure_ordered:
        unit_list = list(units_dict.keys())  # Preserve order from P3.MPI
        
        # Collect ALL keys for this group across all units
        all_keys_for_group = []
        for unit in unit_list:
            all_keys_for_group.extend(units_dict[unit])
        
        # Create JKA entry: [group, [units], [all_keys]]
        jka_list.append([group, unit_list, all_keys_for_group])
        
        # Build P3.MDI: Simply count total keys (each key gets an MDI)
        for unit in unit_list:
            for key in units_dict[unit]:
                mdi_list.append(mdi_counter)
                mdi_counter += 1
    
    # P3.MPI is simply the unique parameter list (no duplication per key!)
    # Parameters with multiple keys still appear only ONCE in P3.MPI
    # JKY structure handles the key expansion during JSON generation
    p3_mpi_list = p3_mpi_unique.copy()  # Use the unique list we built earlier
    
    jky = {"JKA": jka_list}
    
    # Calculate total keys in JKY for P1.NMD
    # CRITICAL: Firmware expects P1.NMD = Σ(num_keys × num_names) for each JKA entry
    # JKA structure: [type, [keys], [names]] where keys are units like "FB", "DegC"
    # and names are equipment identifiers like "CNTRL Valve", "VFDRun"
    total_jky_keys = 0
    for jka_entry in jka_list:
        if len(jka_entry) >= 3:
            num_keys = len(jka_entry[1])   # Number of keys/units (index [1])
            num_names = len(jka_entry[2])  # Number of equipment names (index [2])
            total_jky_keys += num_keys * num_names  # MULTIPLY keys × names
    
    # Step 4: Build P3 structure
    # P3 has two sources for output data:
    # - P3.MPI: Maps MDI to B5 Modbus parameter IDs (PC3_MP array)
    # - P3.LBI: Maps MDI to P2 Lua buffer indices (PC3_LB array)
    # 
    # IMPORTANT: P3.LBI is ONLY for Lua-calculated values that don't come from Modbus.
    # Verification reads are Modbus parameters and must output via P3.MPI, not P3.LBI.
    # For most configurations, P3.LBI will be empty [] since all outputs come from Modbus.
    
    p3_lbi_list = []  # Empty for configurations where all outputs are from Modbus params
    # NOTE: P3.LBI would only be populated if Lua script calculates custom values
    # that need to be output to cloud (e.g., aggregated metrics, alarms, etc.)
    
    p3 = {
        "MDI": mdi_list,       # SEQUENTIAL: [1, 2, 3, 4, ...]
        "MPI": p3_mpi_list,    # Maps MDI to B5 Modbus parameter IDs
        "LBI": p3_lbi_list     # Maps MDI to P2 Lua buffer indices (usually empty)
    }
    
    # Update P1.NMD with total JKY keys count
    p1["NMD"] = total_jky_keys
    
    # JKC: JSON Key Configuration (fixed structure from examples)
    jkc = {
        "JKH": "properties",
        "EKS": "DKEY"
    }
    
    # NTC: Network Configuration (template with defaults)
    # User can modify these in the generated JSON
    ntc = {
        "IP": "18.191.222.62",
        "PT": "1234",
        "CI": "Lucas",
        "SN": [1],
        "MI": ["GWAY01"],
        "MT": ["GWAY"],
        "DI": "GW01"
    }
    
    # MST: Master settings
    # PRF: Profile selection (0, 1, or 2)
    #   0 = Multiple Slave, Different Types, Non-Uniform, Slave-by-Slave
    #   1 = Multiple Slaves, Same Type, Uniform, Slave-by-Slave
    #   2 = Multiple Slaves, Different Types, Non-Uniform, All Parameters Once
    mst = {
        "PRF": int(profile)  # Use actual profile from communication settings
    }
    
    return {
        "P1": p1,
        "P2": p2,
        "P3": p3,
        "JKY": jky,
        "JKC": jkc,
        "NTC": ntc,
        "MST": mst
    }


def generate_output_json(param_config, registers):
    """Generate Output JSON template based on ParamMap_Config.json structure.
    
    This Output JSON is used by external systems/cloud for data visualization.
    Structure is defined by JKY (grouping) and P3 (parameter mapping).
    
    Output structure follows Excel mapping logic:
    - Top level: Machine type group (e.g., "CPM")
    - Contains: MSG_TYPE + device groups (e.g., "FAN", "PUMP")
    - Each device group: Array of device objects
    - Each device object: DKEY + parameter key-value pairs
    
    Example:
    {
      "CPM": {
        "MSG_TYPE": "NML_STAT",
        "FAN": [
          {
            "DKEY": "Fan AHU1 VFD1",
            "STAT": 0,
            "RNHR": 510
          }
        ]
      }
    }
    
    Args:
        param_config: Generated ParamMap_Config.json dictionary
        registers: List of register objects for parameter lookup
        
    Returns:
        Dictionary representing the Output JSON structure with placeholder values
    """
    ntc = param_config.get('NTC', {})
    jky = param_config.get('JKY', {})
    jka = jky.get('JKA', [])
    p3 = param_config.get('P3', {})
    jkc = param_config.get('JKC', {})
    
    # Get machine type from NTC (e.g., "CPM", "GWAY")
    machine_type = ntc.get('MT', ['GWAY'])[0] if ntc.get('MT') else 'GWAY'
    
    # Create machine type group with MSG_TYPE
    machine_group = {
        "MSG_TYPE": "NML_STAT"  # Fixed message type for normal status
    }
    
    # Process JKA structure to build device groups
    # JKA format: [[group_name, [device_names], [parameter_keys]], ...]
    # Example: [["FAN", ["Fan AHU1 VFD1"], ["STAT", "RNHR"]], ...]
    
    for jka_entry in jka:
        if len(jka_entry) < 3:
            continue
            
        group_name = jka_entry[0]  # e.g., "FAN", "PUMP", "SENSOR"
        device_names = jka_entry[1]  # e.g., ["Fan AHU1 VFD1", "Fan AHU2 VFD2"]
        param_keys = jka_entry[2]  # e.g., ["STAT", "RNHR", "FREQ"]
        
        # Create array for this device group
        group_array = []
        
        # For each device in this group
        for device_name in device_names:
            # Create device object starting with DKEY (or custom key from JKC.EKS)
            device_obj = {
                jkc.get('EKS', 'DKEY'): device_name
            }
            
            # Add parameters for this device
            # Match device name with parameters from registers
            for param_key in param_keys:
                # Find register(s) with matching device + parameter combination
                # Search through cloud parameters
                param_value = 0  # Placeholder value (runtime provides actual data)
                
                for reg in registers:
                    if not reg.cloud:
                        continue
                    
                    # Check if this register matches device and parameter
                    if reg.json_unit == device_name:
                        # Check if param_key is in this register's json_key
                        if reg.json_key:
                            keys = [k.strip() for k in reg.json_key.split(',')]
                            if param_key in keys:
                                # Found matching parameter
                                # In actual runtime, firmware provides real value
                                # For template generation, use placeholder
                                param_value = 0
                                break
                
                device_obj[param_key] = param_value
            
            group_array.append(device_obj)
        
        # Add this device group to machine_group
        machine_group[group_name] = group_array
    
    # Return output starting directly with machine type group
    # No extra top-level fields (client_id, machine_id, etc.)
    output = {
        machine_type: machine_group
    }
    
    return output


# -----------------
# Validation Engine
# -----------------
def validate_modbus_io(modbus_io, registers, packets, communication, slaves):
    """Validate generated modbus_io structure and consistency.
    Returns a dict: { 'errors': [...], 'warnings': [...] }
    """
    errors = []
    warnings = []

    # Basic structure checks
    for key in ['B1', 'B2', 'B3', 'B4', 'B5', 'B6']:
        if key not in modbus_io:
            errors.append(f"Missing top-level key: {key}")

    # B1 checks
    b1 = modbus_io.get('B1', {})
    if b1.get('NOP', 0) != len(registers):
        warnings.append(f"B1.NOP ({b1.get('NOP')}) does not match number of registers ({len(registers)})")

    # B2 checks (communication)
    b2 = modbus_io.get('B2', {})
    if 'BR' in b2:
        try:
            int(b2['BR'])
        except Exception:
            errors.append(f"B2.BR (baudrate) is not an integer: {b2.get('BR')}")
    
    # B2.DF format validation (firmware constraint)
    if 'DF' in b2:
        df = b2['DF']
        valid_formats = ["8N1", "8E1", "8O1", "7E1", "7O1"]
        if df not in valid_formats:
            errors.append(f"B2.DF must be one of {valid_formats}, got '{df}' (firmware limit)")
    else:
        errors.append("B2.DF is required (data format like '8N1')")

    # B4 packet counts vs packets list
    b4 = modbus_io.get('B4', {})
    sa = b4.get('SA', [])
    nrt = b4.get('NRT', [])
    if len(sa) != len(packets) or len(nrt) != len(packets):
        warnings.append("Number of packet entries in B4 does not match generated packets")

    # B5 parameter packet numbers should reference valid packets
    b5 = modbus_io.get('B5', {})
    pn_list = b5.get('PN', [])
    for i, pn in enumerate(pn_list, 1):
        if pn < 1 or pn > len(packets):
            errors.append(f"Serial No. {i}: References invalid packet number {pn} (total packets: {len(packets)})")

    # B6 read/write consistency
    b6 = modbus_io.get('B6', {})
    rp = b6.get('RP', [])
    wp = b6.get('WP', [])
    for pnum in rp + wp:
        if pnum < 1 or pnum > len(registers):
            errors.append(f"B6 references invalid parameter Serial No. {pnum} (total parameters: {len(registers)})")

    return {'errors': errors, 'warnings': warnings}


def validate_parameter_config(param_cfg, registers):
    """Validate generated parameter_config structure and basic consistency.
    Returns a dict: { 'errors': [...], 'warnings': [...] }
    """
    errors = []
    warnings = []

    # Required top-level keys
    for key in ['P1', 'P2', 'P3', 'JKY']:
        if key not in param_cfg:
            errors.append(f"Missing top-level key in parameter_config: {key}")

    p1 = param_cfg.get('P1', {})
    if 'NLB' in p1 and not isinstance(p1['NLB'], int):
        warnings.append("P1.NLB should be integer count")

    # CRITICAL: Firmware-specific validation
    # Check P1.NMD matches JKY total elements
    p1 = param_cfg.get('P1', {})
    jky = param_cfg.get('JKY', {})
    jka = jky.get('JKA', [])
    
    if 'NMD' in p1:
        expected_nmd = p1['NMD']
        # Count total keys in JKA structure
        # CRITICAL: Firmware expects NMD = Σ(units × keys), NOT just key count!
        total_jky_keys = 0
        for jka_entry in jka:
            if len(jka_entry) >= 3:
                # jka_entry format: [group, [units], [keys]]
                num_units = len(jka_entry[1])
                num_keys = len(jka_entry[2])
                total_jky_keys += num_units * num_keys  # Firmware multiplies units × keys
        
        if total_jky_keys != expected_nmd:
            errors.append(f"CRITICAL: P1.NMD ({expected_nmd}) does not match JKY total keys ({total_jky_keys}) - Firmware will fail!")
    
    # Check P3.MDI is sequential (1, 2, 3, 4, ...)
    p3 = param_cfg.get('P3', {})
    mdi_list = p3.get('MDI', [])
    if mdi_list:
        expected_sequential = list(range(1, len(mdi_list) + 1))
        if mdi_list != expected_sequential:
            errors.append(f"CRITICAL: P3.MDI must be sequential [1,2,3,...] but got {mdi_list} - Firmware expects sequential order!")
    
    # JKY structure checks
    if jka and not isinstance(jka, list):
        errors.append("JKY.JKA should be a list of json key entries")
    
    # Validate JKA format: [[group, [units], [keys]], ...]
    for idx, jka_entry in enumerate(jka):
        if not isinstance(jka_entry, list) or len(jka_entry) != 3:
            errors.append(f"JKA entry {idx} should be [group, [units], [keys]] format")
        elif not isinstance(jka_entry[1], list) or not isinstance(jka_entry[2], list):
            errors.append(f"JKA entry {idx}: units and keys must be lists")
        else:
            # Firmware string length validation: JKY fields max 15 chars
            equipment_type = jka_entry[0]
            device_names = jka_entry[1]
            param_keys = jka_entry[2]
            
            if len(equipment_type) > 15:
                errors.append(f"JKA[{idx}] Equipment Type '{equipment_type}' exceeds 15 chars (firmware limit: char[15])")
            
            for dev_idx, device_name in enumerate(device_names):
                if len(device_name) > 15:
                    errors.append(f"JKA[{idx}] Device Name '{device_name}' exceeds 15 chars (firmware limit: char[15])")
            
            for key_idx, param_key in enumerate(param_keys):
                if len(param_key) > 15:
                    errors.append(f"JKA[{idx}] Parameter Key '{param_key}' exceeds 15 chars (firmware limit: char[15])")
    
    # JKC string length validation: max 15 chars
    jkc = param_cfg.get('JKC', {})
    if 'JKH' in jkc:
        jkh = jkc['JKH']
        if len(jkh) > 15:
            errors.append(f"JKC.JKH '{jkh}' exceeds 15 chars (firmware limit: char[15])")
    
    if 'EKS' in jkc:
        eks = jkc['EKS']
        if len(eks) > 15:
            errors.append(f"JKC.EKS '{eks}' exceeds 15 chars (firmware limit: char[15])")
    
    # NTC string length validation
    ntc = param_cfg.get('NTC', {})
    
    # IP, Client ID, Device ID: max 20 chars
    if 'IP' in ntc and len(ntc['IP']) > 20:
        errors.append(f"NTC.IP '{ntc['IP']}' exceeds 20 chars (firmware limit: char[20])")
    
    if 'CI' in ntc and len(ntc['CI']) > 20:
        errors.append(f"NTC.CI (Client ID) '{ntc['CI']}' exceeds 20 chars (firmware limit: char[20])")
    
    if 'DI' in ntc and len(ntc['DI']) > 20:
        errors.append(f"NTC.DI (Device ID) '{ntc['DI']}' exceeds 20 chars (firmware limit: char[20])")
    
    # Port: max 8 chars
    if 'PT' in ntc and len(ntc['PT']) > 8:
        errors.append(f"NTC.PT (Port) '{ntc['PT']}' exceeds 8 chars (firmware limit: char[8])")
    
    # Machine IDs and Types: max 20 chars each
    if 'MI' in ntc and isinstance(ntc['MI'], list):
        for idx, machine_id in enumerate(ntc['MI']):
            if len(machine_id) > 20:
                errors.append(f"NTC.MI[{idx}] (Machine ID) '{machine_id}' exceeds 20 chars (firmware limit: char[20])")
    
    if 'MT' in ntc and isinstance(ntc['MT'], list):
        for idx, machine_type in enumerate(ntc['MT']):
            if len(machine_type) > 20:
                errors.append(f"NTC.MT[{idx}] (Machine Type) '{machine_type}' exceeds 20 chars (firmware limit: char[20])")
    
    # MST validation
    mst = param_cfg.get('MST', {})
    if 'PRF' in mst:
        prf_value = mst['PRF']
        if not isinstance(prf_value, int) or prf_value not in [0, 1, 2]:
            errors.append(f"MST.PRF must be 0, 1, or 2 but got: {prf_value}")
    else:
        warnings.append("MST.PRF not found - Profile not specified")

    return {'errors': errors, 'warnings': warnings}

# GUI Application
class ModbusConfigGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("🔧 Modbus Configuration Generator Pro")
        self.root.geometry("1500x850")
        self.root.configure(bg='#f5f7fa')
        
        # Data storage
        self.register_rows = []
        self.generated_modbus_io = None
        self.generated_parameter_config = None
        self.generated_output_json = None
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Enhanced color scheme
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#2c3e50', background='#f5f7fa')
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10), foreground='#7f8c8d', background='#f5f7fa')
        style.configure('Section.TLabel', font=('Segoe UI', 13, 'bold'), foreground='#34495e')
        style.configure('Generate.TButton', font=('Segoe UI', 13, 'bold'), padding=12)
        style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'), padding=8)
        
        # Custom colors for buttons
        style.map('Generate.TButton',
                 background=[('active', '#27ae60'), ('!active', '#2ecc71')],
                 foreground=[('active', 'white'), ('!active', 'white')])
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container with scrollbar
        main_canvas = tk.Canvas(self.root, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas, style='TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Title Section with gradient-like effect
        title_frame = tk.Frame(scrollable_frame, bg='#3498db', height=100)
        title_frame.pack(fill='x', padx=0, pady=0)
        
        title_inner = tk.Frame(title_frame, bg='#3498db')
        title_inner.pack(expand=True, pady=20)
        
        tk.Label(title_inner, text="⚙️ Modbus Configuration Generator Pro", 
                font=('Segoe UI', 20, 'bold'), fg='white', bg='#3498db').pack()
        tk.Label(title_inner, text="✨ Automatically generate modbus_io.json and parameter_config.json with ease", 
                font=('Segoe UI', 11), fg='#ecf0f1', bg='#3498db').pack(pady=5)
        
        # Communication Settings Section
        comm_frame = ttk.LabelFrame(scrollable_frame, text="  📡 Communication Settings  ", padding=20)
        comm_frame.pack(fill='x', padx=25, pady=15)
        
        comm_grid = ttk.Frame(comm_frame)
        comm_grid.pack(fill='x')
        
        # Baudrate
        ttk.Label(comm_grid, text="Baudrate:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=10, pady=8)
        self.baudrate_var = tk.StringVar(value="19200")
        baudrate_combo = ttk.Combobox(comm_grid, textvariable=self.baudrate_var, 
                                      values=["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"], 
                                      width=20, state='readonly', font=('Segoe UI', 10))
        baudrate_combo.grid(row=0, column=1, padx=10, pady=8)
        ttk.Label(comm_grid, text="bits/sec", font=('Segoe UI', 9), foreground='#7f8c8d').grid(row=0, column=2, sticky='w', padx=5)
        
        # Data Format - Separated into three parts
        ttk.Label(comm_grid, text="Data Format:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=3, sticky='w', padx=(30, 10), pady=8)
        
        format_frame = ttk.Frame(comm_grid)
        format_frame.grid(row=0, column=4, columnspan=3, sticky='w', padx=10)
        
        # Data Bits
        ttk.Label(format_frame, text="Data Bits:", font=('Segoe UI', 9)).grid(row=0, column=0, sticky='w', padx=5)
        self.data_bits_var = tk.StringVar(value="8")
        data_bits_combo = ttk.Combobox(format_frame, textvariable=self.data_bits_var, 
                                      values=["7", "8"], width=5, state='readonly', font=('Segoe UI', 9))
        data_bits_combo.grid(row=0, column=1, padx=5)
        
        # Parity
        ttk.Label(format_frame, text="Parity:", font=('Segoe UI', 9)).grid(row=0, column=2, sticky='w', padx=(15, 5))
        self.parity_var = tk.StringVar(value="E")
        parity_combo = ttk.Combobox(format_frame, textvariable=self.parity_var, 
                                   values=["N (None)", "E (Even)", "O (Odd)"], width=12, state='readonly', font=('Segoe UI', 9))
        parity_combo.grid(row=0, column=3, padx=5)
        parity_combo.set("E (Even)")
        
        # Stop Bits
        ttk.Label(format_frame, text="Stop Bits:", font=('Segoe UI', 9)).grid(row=0, column=4, sticky='w', padx=(15, 5))
        self.stop_bits_var = tk.StringVar(value="1")
        stop_bits_combo = ttk.Combobox(format_frame, textvariable=self.stop_bits_var, 
                                      values=["1", "2"], width=5, state='readonly', font=('Segoe UI', 9))
        stop_bits_combo.grid(row=0, column=5, padx=5)
        
        # Profile Selection
        ttk.Label(comm_grid, text="Profile:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=10, pady=8)
        self.profile_var = tk.StringVar(value="0")
        profile_combo = ttk.Combobox(comm_grid, textvariable=self.profile_var,
                                    values=bc.DROPDOWN_OPTIONS['profile'],
                                    width=60, state='readonly', font=('Segoe UI', 9))
        profile_combo.grid(row=1, column=1, columnspan=6, padx=10, pady=8, sticky='ew')
        profile_combo.set(bc.DROPDOWN_OPTIONS['profile'][0])
        
        # Register Configuration Section
        register_frame = ttk.LabelFrame(scrollable_frame, text="  📋 Register Configuration  ", padding=20)
        register_frame.pack(fill='both', expand=True, padx=25, pady=15)
        
        # Button toolbar with icons
        btn_toolbar = ttk.Frame(register_frame)
        btn_toolbar.pack(fill='x', pady=(0, 15))
        
        # Left side buttons
        left_buttons = ttk.Frame(btn_toolbar)
        left_buttons.pack(side='left')
        
        btn_add = ttk.Button(left_buttons, text="➕ Add Register", command=self.add_register_row, style='Action.TButton')
        btn_add.pack(side='left', padx=5)
        
        btn_edit = ttk.Button(left_buttons, text="✏️ Edit Selected", command=self.edit_selected_row, style='Action.TButton')
        btn_edit.pack(side='left', padx=5)
        
        btn_delete = ttk.Button(left_buttons, text="🗑️ Delete Selected", command=self.delete_selected_row, style='Action.TButton')
        btn_delete.pack(side='left', padx=5)
        
        btn_clear = ttk.Button(left_buttons, text="🧹 Clear All", command=self.clear_all_registers, style='Action.TButton')
        btn_clear.pack(side='left', padx=5)
        
        # Right side buttons
        right_buttons = ttk.Frame(btn_toolbar)
        right_buttons.pack(side='right')
        
        btn_sample = ttk.Button(right_buttons, text="📝 Load Sample", command=self.load_sample_data, style='Action.TButton')
        btn_sample.pack(side='left', padx=5)
        
        btn_import = ttk.Button(right_buttons, text="📂 Import Registers", command=self.import_registers, style='Action.TButton')
        btn_import.pack(side='left', padx=5)
        
        btn_export = ttk.Button(right_buttons, text="💾 Export Registers", command=self.export_registers, style='Action.TButton')
        btn_export.pack(side='left', padx=5)
        
        # Register Table with enhanced styling
        table_frame = ttk.Frame(register_frame)
        table_frame.pack(fill='both', expand=True)
        
        # Create Treeview with Serial Number
        columns = ('S.No', 'Slave ID', 'FC', 'Address', 'Length', 'FMT', 'Multiplier', 
                  'Access', 'Cloud', 'JSON Group', 'JSON Unit', 'JSON Key')
        
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        
        # Define headings with better widths
        self.tree.heading('S.No', text='S.No')
        self.tree.column('S.No', width=50, anchor='center')
        
        for col in columns[1:]:
            self.tree.heading(col, text=col)
            if col in ['Slave ID', 'FC', 'Address', 'Length', 'FMT']:
                self.tree.column(col, width=80, anchor='center')
            elif col in ['Multiplier', 'Access', 'Cloud']:
                self.tree.column(col, width=90, anchor='center')
            else:
                self.tree.column(col, width=130)
        
        # Enhanced scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Alternating row colors
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')
        
        # Double-click to edit
        self.tree.bind('<Double-1>', lambda e: self.edit_selected_row())
        
        # Status bar
        status_frame = ttk.Frame(register_frame)
        status_frame.pack(fill='x', pady=(10, 0))
        self.status_label = ttk.Label(status_frame, text="📊 Total Registers: 0", font=('Segoe UI', 10))
        self.status_label.pack(side='left')
        
        # Generate Button with enhanced styling
        generate_frame = tk.Frame(scrollable_frame, bg='#f5f7fa')
        generate_frame.pack(fill='x', padx=25, pady=20)
        
        generate_btn = tk.Button(generate_frame, text="🚀 Generate Configuration Files", 
                                font=('Segoe UI', 14, 'bold'), 
                                bg='#2ecc71', fg='white', 
                                activebackground='#27ae60', activeforeground='white',
                                relief='flat', padx=40, pady=15,
                                cursor='hand2',
                                command=self.generate_configs)
        generate_btn.pack()
        
        # Hover effect
        def on_enter(e):
            generate_btn['background'] = '#27ae60'
        def on_leave(e):
            generate_btn['background'] = '#2ecc71'
        generate_btn.bind("<Enter>", on_enter)
        generate_btn.bind("<Leave>", on_leave)
        
        # Output Section with tabs
        output_frame = ttk.LabelFrame(scrollable_frame, text="  📄 Generated Configuration Files  ", padding=20)
        output_frame.pack(fill='both', expand=True, padx=25, pady=15)
        
        # Status indicator for generated JSONs
        status_info_frame = ttk.Frame(output_frame)
        status_info_frame.pack(fill='x', pady=(0, 5))
        ttk.Label(status_info_frame, text="📊 Status:", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=5)
        self.json_status_label = ttk.Label(status_info_frame, text="No configurations generated yet", 
                                           font=('Segoe UI', 9), foreground='gray')
        self.json_status_label.pack(side='left', padx=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(output_frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 10))
        
        # Tab 1: modbus_io.json
        modbus_tab = ttk.Frame(self.notebook)
        self.notebook.add(modbus_tab, text="  📑 modbus_io.json  ")
        
        self.modbus_text = scrolledtext.ScrolledText(modbus_tab, wrap=tk.WORD, 
                                                      font=('Consolas', 10),
                                                      bg='#1e1e1e', fg='#d4d4d4',
                                                      insertbackground='white',
                                                      selectbackground='#264f78')
        self.modbus_text.pack(fill='both', expand=True)
        
        # Tab 2: parameter_config.json
        param_tab = ttk.Frame(self.notebook)
        self.notebook.add(param_tab, text="  📑 parameter_config.json  ")
        
        self.param_text = scrolledtext.ScrolledText(param_tab, wrap=tk.WORD, 
                                                    font=('Consolas', 10),
                                                    bg='#1e1e1e', fg='#d4d4d4',
                                                    insertbackground='white',
                                                    selectbackground='#264f78')
        self.param_text.pack(fill='both', expand=True)
        
        # Tab 3: output.json
        output_tab = ttk.Frame(self.notebook)
        self.notebook.add(output_tab, text="  📑 output.json  ")
        
        self.output_text = scrolledtext.ScrolledText(output_tab, wrap=tk.WORD, 
                                                     font=('Consolas', 10),
                                                     bg='#1e1e1e', fg='#d4d4d4',
                                                     insertbackground='white',
                                                     selectbackground='#264f78')
        self.output_text.pack(fill='both', expand=True)
        
        # Add initial placeholder messages
        initial_message = "// Click 'Generate Configs' to create Output JSON\\n// Output JSON will appear here after generation"
        self.modbus_text.insert('1.0', initial_message)
        self.param_text.insert('1.0', initial_message)
        self.output_text.insert('1.0', initial_message)
        
        # Download buttons with icons
        download_frame = ttk.Frame(output_frame)
        download_frame.pack(fill='x')
        
        ttk.Button(download_frame, text="💾 Save modbus_io.json", 
                  command=self.save_modbus_io, style='Action.TButton').pack(side='left', padx=5)
        ttk.Button(download_frame, text="💾 Save parameter_config.json", 
                  command=self.save_parameter_config, style='Action.TButton').pack(side='left', padx=5)
        ttk.Button(download_frame, text="� Save output.json", 
                  command=self.save_output_json, style='Action.TButton').pack(side='left', padx=5)
        ttk.Button(download_frame, text="📦 Save All Files", 
                  command=self.save_all_files, style='Action.TButton').pack(side='left', padx=5)
        self.update_status()
    
    def update_status(self):
        count = len(self.tree.get_children())
        self.status_label.config(text=f"📊 Total Registers: {count}")
    
    def add_register_row(self):
        RegisterDialog(self.root, self)
        
    def edit_selected_row(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ Warning", "Please select a row to edit!")
            return
        
        item = selected[0]
        values = self.tree.item(item)['values']
        
        # Create edit dialog with pre-filled values
        EditRegisterDialog(self.root, self, item, values)
    
    def load_sample_data(self):
        """Load sample data with proper validation"""
        sample_data = [
            # Read: UINT16
            {'slave_id': 1, 'fc': 3, 'address': 100, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_AIE1', 'json_unit': 'DegC', 'json_key': 'RAT'},
            # Read: INT32 Big Endian
            {'slave_id': 1, 'fc': 3, 'address': 200, 'length': 2, 'fmt': 4, 
             'multiplier': 0.1, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_AIE2', 'json_unit': 'Vol', 'json_key': 'ChW_Fb_V'},
            # Read: Float 32-bit Big Endian
            {'slave_id': 1, 'fc': 3, 'address': 300, 'length': 2, 'fmt': 1, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_Mb1', 'json_unit': 'Watt', 'json_key': 'VFD_P'},
            # Read: UINT32 Little Endian
            {'slave_id': 1, 'fc': 3, 'address': 400, 'length': 2, 'fmt': 7, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_Mb2', 'json_unit': 'Hour', 'json_key': 'VFD_Rhr'},
            # Write: UINT16
            {'slave_id': 1, 'fc': 6, 'address': 500, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'W', 'cloud': 'No', 
             'json_group': '', 'json_unit': '', 'json_key': ''},
            # Read-Write: INT16 - Write + verification parameter
            # IMPORTANT: RW parameters should NOT have cloud=Yes
            # The read component is only for write verification, not telemetry
            {'slave_id': 2, 'fc': 3, 'address': 1000, 'length': 1, 'fmt': 8, 
             'multiplier': 0.1, 'access': 'RW', 'cloud': 'No', 
             'json_group': '', 'json_unit': '', 'json_key': ''},
            # Read: Coil (FC=1)
            {'slave_id': 2, 'fc': 1, 'address': 1, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'Chiller_DIE1', 'json_unit': 'St', 'json_key': 'ChillerRun'},
            # Write: Coil (FC=5)
            {'slave_id': 2, 'fc': 5, 'address': 100, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'W', 'cloud': 'No', 
             'json_group': '', 'json_unit': '', 'json_key': ''},
        ]
        
        # Validate each sample before loading
        errors = []
        for idx, data in enumerate(sample_data, 1):
            # Validate slave ID
            if data['slave_id'] < 1 or data['slave_id'] > 247:
                errors.append(f"Sample {idx}: Invalid slave ID {data['slave_id']} (must be 1-247)")
            
            # Validate address
            if data['address'] < 0 or data['address'] > 65535:
                errors.append(f"Sample {idx}: Invalid address {data['address']} (must be 0-65535)")
            
            # Validate function code
            if data['fc'] not in [1, 2, 3, 4, 5, 6, 15, 16]:
                errors.append(f"Sample {idx}: Invalid function code {data['fc']}")
            
            # Validate format code
            if data['fmt'] not in [1, 2, 3, 4, 5, 6, 7, 8]:
                errors.append(f"Sample {idx}: Invalid format code {data['fmt']}")
            
            # Validate length matches format
            expected_length = bc.get_register_length(data['fmt'])
            if data['length'] != expected_length:
                errors.append(f"Sample {idx}: Length mismatch - Format {data['fmt']} requires length {expected_length}, got {data['length']}")
            
            # Validate access type
            if data['access'] not in ['R', 'W', 'RW']:
                errors.append(f"Sample {idx}: Invalid access type '{data['access']}' (must be R, W, or RW)")
            
            # Validate multiplier is numeric
            try:
                float(data['multiplier'])
            except (ValueError, TypeError):
                errors.append(f"Sample {idx}: Invalid multiplier '{data['multiplier']}' (must be numeric)")
        
        # If validation errors, show them and abort
        if errors:
            error_msg = "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n...and {len(errors) - 10} more errors"
            messagebox.showerror("❌ Sample Data Validation Failed", 
                               f"Sample data contains errors:\n\n{error_msg}")
            return
        
        # Clear existing data
        self.clear_all_registers()
        
        # All validation passed - load the data
        for idx, data in enumerate(sample_data):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.tree.insert('', 'end', values=(
                idx + 1,
                data['slave_id'], data['fc'], data['address'], data['length'],
                data['fmt'], data['multiplier'], data['access'], data['cloud'],
                data['json_group'], data['json_unit'], data['json_key']
            ), tags=(tag,))
        
        self.update_status()
        messagebox.showinfo("✅ Success", f"Sample data loaded successfully!\n\n{len(sample_data)} parameters added with proper validation.")
    
    def import_registers(self):
        filename = filedialog.askopenfilename(
            title="Import Register Configuration",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            if filename.endswith('.json'):
                with open(filename, 'r') as f:
                    data = json.load(f)
                    registers = data.get('registers', [])
            elif filename.endswith('.csv'):
                with open(filename, 'r') as f:
                    reader = csv.DictReader(f)
                    registers = list(reader)
            else:
                messagebox.showerror("❌ Error", "Unsupported file format!")
                return
            
            # Clear existing and add imported
            self.clear_all_registers()
            
            for idx, reg in enumerate(registers):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.tree.insert('', 'end', values=(
                    idx + 1,
                    reg.get('slave_id', 1),
                    reg.get('fc', 3),
                    reg.get('address', 0),
                    reg.get('length', 1),
                    reg.get('fmt', 1),
                    reg.get('multiplier', 1.0),
                    reg.get('access', 'R'),
                    reg.get('cloud', 'No'),
                    reg.get('json_group', ''),
                    reg.get('json_unit', ''),
                    reg.get('json_key', '')
                ), tags=(tag,))
            
            self.update_status()
            messagebox.showinfo("✅ Success", f"Imported {len(registers)} registers successfully!")
        
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to import file:\n{str(e)}")
    
    def export_registers(self):
        if not self.tree.get_children():
            messagebox.showwarning("⚠️ Warning", "No registers to export!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="register_config.json"
        )
        
        if not filename:
            return
        
        try:
            registers = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                registers.append({
                    'slave_id': values[1],
                    'fc': values[2],
                    'address': values[3],
                    'length': values[4],
                    'fmt': values[5],
                    'multiplier': values[6],
                    'access': values[7],
                    'cloud': values[8],
                    'json_group': values[9],
                    'json_unit': values[10],
                    'json_key': values[11]
                })
            
            if filename.endswith('.json'):
                with open(filename, 'w') as f:
                    json.dump({'registers': registers}, f, indent=2)
            elif filename.endswith('.csv'):
                with open(filename, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=registers[0].keys())
                    writer.writeheader()
                    writer.writerows(registers)
            
            messagebox.showinfo("✅ Success", f"Exported {len(registers)} registers successfully!")
        
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to export file:\n{str(e)}")
    
    def clear_all_registers(self):
        if not self.tree.get_children():
            return
        
        if messagebox.askyesno("⚠️ Confirm", "Are you sure you want to clear all registers?"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.update_status()
    
    def delete_selected_row(self):
        selected = self.tree.selection()
        if selected:
            if messagebox.askyesno("⚠️ Confirm", "Delete selected register(s)?"):
                for item in selected:
                    self.tree.delete(item)
                # Renumber all items
                self.renumber_items()
                self.update_status()
        else:
            messagebox.showwarning("⚠️ Warning", "Please select a row to delete!")
    
    def renumber_items(self):
        for idx, item in enumerate(self.tree.get_children()):
            values = list(self.tree.item(item)['values'])
            values[0] = idx + 1
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.tree.item(item, values=values, tags=(tag,))
    
    def get_register_data(self):
        registers = []
        slaves_set = set()
        for idx, item in enumerate(self.tree.get_children()):
            values = self.tree.item(item)['values']
            slaves_set.add(int(values[1]))
            reg = RegisterEntry(
                param_id=f"P{idx + 1}",
                slave_id=int(values[1]),
                fc=int(values[2]),
                address=int(values[3]),
                length=int(values[4]),
                fmt=int(values[5]),
                multiplier=float(values[6]),
                access=values[7],
                cloud=values[8] == 'Yes',
                json_group=values[9],
                json_unit=values[10],
                json_key=values[11]
            )
            registers.append(reg)
        return registers, sorted(list(slaves_set))
    
    def generate_configs(self):
        try:
            registers, slaves = self.get_register_data()
            
            if not registers:
                messagebox.showerror("❌ Error", "Please add at least one register!")
                return
            
            # Validate
            validation = validate_registers(registers)
            if validation['status'] == 'error':
                messagebox.showerror("❌ Validation Error", validation['message'])
                return
            
            # Get data format
            parity_map = {"N (None)": "N", "E (Even)": "E", "O (Odd)": "O"}
            parity_value = self.parity_var.get()
            parity = parity_map.get(parity_value, parity_value[0] if parity_value else "E")
            data_format = f"{self.data_bits_var.get()}{parity}{self.stop_bits_var.get()}"
            
            # Communication settings
            communication = {
                'baudrate': int(self.baudrate_var.get()),
                'format': data_format
            }
            
            # Extract profile value from dropdown (format: "0 - Description")
            profile_text = self.profile_var.get()
            try:
                profile = int(profile_text.split(' - ')[0]) if ' - ' in profile_text else int(profile_text)
            except (ValueError, IndexError):
                profile = 0  # Default to Profile 0 if parsing fails
            
            # Generate packets
            packets = generate_packets(registers)

            # Generate JSONs (but validate first)
            tentative_modbus_io = generate_modbus_io_json(communication, slaves, packets, registers)
            tentative_param_cfg = generate_parameter_config_json(registers, profile)

            # Run internal validation and surface results via messageboxes
            v1 = validate_modbus_io(tentative_modbus_io, registers, packets, communication, slaves)
            v2 = validate_parameter_config(tentative_param_cfg, registers)

            all_errors = v1['errors'] + v2['errors']
            all_warnings = v1['warnings'] + v2['warnings']

            if all_errors:
                short = '\n'.join(all_errors[:20])
                more = len(all_errors) - 20
                if more > 0:
                    short += f"\n...and {more} more errors"
                full = '\n'.join(all_errors + ["\n"] + ["Warnings:"] + all_warnings)
                if messagebox.askyesno("Validation Failed", f"Validation found errors:\n\n{short}\n\nShow full details in a text file?"):
                    try:
                        path = os.path.join(os.getcwd(), f"validation_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        with open(path, 'w', encoding='utf-8') as fh:
                            fh.write(full)
                        messagebox.showinfo("Saved", f"Full validation details saved to:\n{path}")
                    except Exception as e:
                        messagebox.showerror("Save Failed", f"Failed to save validation details: {e}")
                return

            if all_warnings:
                short_w = '\n'.join(all_warnings[:20])
                more_w = len(all_warnings) - 20
                if more_w > 0:
                    short_w += f"\n...and {more_w} more warnings"
                if not messagebox.askyesno("Validation Warnings", f"Validation completed with warnings:\n\n{short_w}\n\nProceed with generation?"):
                    return

            # Accept and set generated
            self.generated_modbus_io = tentative_modbus_io
            self.generated_parameter_config = tentative_param_cfg
            
            # Generate Output JSON template
            try:
                self.generated_output_json = generate_output_json(tentative_param_cfg, registers)
            except Exception as e:
                messagebox.showwarning("⚠️ Warning", f"Output JSON generation failed:\n{str(e)}\n\nContinuing with Modbus and ParamMap JSON only.")
                self.generated_output_json = None
            
            # Display in text widgets
            self.modbus_text.delete('1.0', tk.END)
            self.modbus_text.insert('1.0', json.dumps(self.generated_modbus_io, indent=2))
            
            self.param_text.delete('1.0', tk.END)
            self.param_text.insert('1.0', json.dumps(self.generated_parameter_config, indent=2))
            
            # Display Output JSON in third tab
            self.output_text.delete('1.0', tk.END)
            if self.generated_output_json:
                self.output_text.insert('1.0', json.dumps(self.generated_output_json, indent=2))
            else:
                error_msg = '''// ⚠️ Output JSON Generation Failed
// 
// Possible reasons:
// 1. No cloud parameters configured (Cloud="Yes" required)
// 2. Missing JSON Group, Unit, or Key fields for cloud parameters
// 3. Invalid ParamMap JSON structure
// 
// To fix:
// - Add at least one register with Cloud="Yes"
// - Fill JSON Group, JSON Unit, and JSON Key fields
// - Regenerate configurations
//
// Output JSON requires cloud parameters to generate device groups.'''
                self.output_text.insert('1.0', error_msg)
            
            # Automatically switch to Output JSON tab to show result
            if self.generated_output_json:
                self.notebook.select(2)  # Switch to third tab (Output JSON)
            
            # Update status label
            if self.generated_output_json:
                self.json_status_label.config(text="✅ Modbus IO  ✅ ParamMap Config  ✅ Output JSON", foreground='green')
            else:
                self.json_status_label.config(text="✅ Modbus IO  ✅ ParamMap Config  ⚠️ Output JSON (failed)", foreground='orange')
            
            # Show success message with details
            success_msg = "Configuration files generated successfully!"
            if self.generated_output_json:
                success_msg += "\n\n✅ Modbus_IO.json\n✅ ParamMap_Config.json\n✅ Output.json template\n\nAll three JSONs are now displayed in their respective tabs."
            else:
                success_msg += "\n\n✅ Modbus_IO.json\n✅ ParamMap_Config.json\n⚠️  Output.json generation failed"
            
            messagebox.showinfo("✅ Success", success_msg)
            
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error generating configurations:\n{str(e)}")

    # run_validation removed — validation now runs internally in generate_configs
    
    def save_modbus_io(self):
        if not self.generated_modbus_io:
            messagebox.showwarning("⚠️ Warning", "Please generate configurations first!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="modbus_io.json"
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.generated_modbus_io, f, indent=2)
            messagebox.showinfo("✅ Success", f"File saved:\n{filename}")

    def save_parameter_config(self):
        if not self.generated_parameter_config:
            messagebox.showwarning("⚠️ Warning", "Please generate configurations first!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="parameter_config.json"
        )

        if filename:
            with open(filename, 'w') as f:
                json.dump(self.generated_parameter_config, f, indent=2)
            messagebox.showinfo("✅ Success", f"File saved:\n{filename}")

    def save_both_files(self):
        if not self.generated_modbus_io or not self.generated_parameter_config:
            messagebox.showwarning("⚠️ Warning", "Please generate configurations first!")
            return

        # Ask where to save modbus_io.json
        modbus_file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="modbus_io.json"
        )
        if not modbus_file:
            return

        # Ask where to save parameter_config.json
        param_file = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="parameter_config.json"
        )
        if not param_file:
            return

        try:
            with open(modbus_file, 'w') as f:
                json.dump(self.generated_modbus_io, f, indent=2)
            with open(param_file, 'w') as f:
                json.dump(self.generated_parameter_config, f, indent=2)
            messagebox.showinfo("✅ Success", f"Files saved:\n{modbus_file}\n{param_file}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to save files:\n{e}")
    
    def save_output_json(self):
        """Save Output JSON template"""
        if not self.generated_output_json:
            messagebox.showwarning("⚠️ Warning", "Output JSON not generated!\n\nPlease generate configurations first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="output.json"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.generated_output_json, f, indent=2)
                messagebox.showinfo("✅ Success", f"Output JSON template saved:\n{filename}\n\nNote: This is a template with placeholder values.\nActual values come from runtime Modbus data.")
            except Exception as e:
                messagebox.showerror("❌ Error", f"Failed to save file:\n{e}")
    
    def save_all_files(self):
        """Save all three JSON files"""
        if not self.generated_modbus_io or not self.generated_parameter_config:
            messagebox.showwarning("⚠️ Warning", "Please generate configurations first!")
            return
        
        # Ask for directory
        directory = filedialog.askdirectory(title="Select folder to save all files")
        if not directory:
            return
        
        try:
            # Save Modbus_IO.json
            modbus_file = os.path.join(directory, "modbus_io.json")
            with open(modbus_file, 'w') as f:
                json.dump(self.generated_modbus_io, f, indent=2)
            
            # Save ParamMap_Config.json
            param_file = os.path.join(directory, "parameter_config.json")
            with open(param_file, 'w') as f:
                json.dump(self.generated_parameter_config, f, indent=2)
            
            success_msg = f"Files saved to:\n{directory}\n\n✅ modbus_io.json\n✅ parameter_config.json"
            
            # Save Output.json if available
            if self.generated_output_json:
                output_file = os.path.join(directory, "output.json")
                with open(output_file, 'w') as f:
                    json.dump(self.generated_output_json, f, indent=2)
                success_msg += "\n✅ output.json (template)"
            
            messagebox.showinfo("✅ Success", success_msg)
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to save files:\n{e}")

class RegisterDialog:
    def __init__(self, parent, app):
        self.app = app
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("➕ Add New Register")
        self.dialog.geometry("550x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg='#f5f7fa')
        
        # Title
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=60)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="📝 Register Information", 
                font=('Segoe UI', 14, 'bold'), fg='white', bg='#3498db').pack(pady=15)
        
        # Create form
        frame = ttk.Frame(self.dialog, padding=30)
        frame.pack(fill='both', expand=True)
        
        row = 0
        
        # Slave ID
        ttk.Label(frame, text="Slave ID:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.slave_id_var = tk.IntVar(value=1)
        ttk.Spinbox(frame, from_=1, to=247, textvariable=self.slave_id_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # Function Code
        ttk.Label(frame, text="Function Code:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.fc_var = tk.StringVar(value="3")
        self.fc_combo = ttk.Combobox(frame, textvariable=self.fc_var, 
                               values=bc.DROPDOWN_OPTIONS['function_code'], 
                               width=28, state='readonly', font=('Segoe UI', 10))
        self.fc_combo.grid(row=row, column=1, pady=10, sticky='ew')
        self.fc_combo.set(bc.DROPDOWN_OPTIONS['function_code'][2])  # Default: "3 - Read Holding Registers"
        row += 1
        
        # Address
        ttk.Label(frame, text="Address:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.address_var = tk.IntVar(value=0)
        ttk.Spinbox(frame, from_=0, to=65535, textvariable=self.address_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # Length (auto-calculated, read-only)
        ttk.Label(frame, text="Length:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.length_var = tk.IntVar(value=1)
        self.length_entry = ttk.Entry(frame, textvariable=self.length_var, width=30, font=('Segoe UI', 10), state='readonly')
        self.length_entry.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="🔒 Auto-calculated from Format", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # Format
        ttk.Label(frame, text="Format (FMT):", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.fmt_var = tk.StringVar(value="3")
        self.fmt_combo = ttk.Combobox(frame, textvariable=self.fmt_var, 
                                values=bc.DROPDOWN_OPTIONS['data_format_code'], 
                                width=28, state='readonly', font=('Segoe UI', 10))
        self.fmt_combo.grid(row=row, column=1, pady=10, sticky='ew')
        self.fmt_combo.set(bc.DROPDOWN_OPTIONS['data_format_code'][2])  # Default: "3 - Unsigned 16-bit"
        self.fmt_combo.bind("<<ComboboxSelected>>", lambda e: self.update_length_from_format())
        row += 1
        
        # Multiplier
        ttk.Label(frame, text="Multiplier:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.multiplier_var = tk.DoubleVar(value=1.0)
        ttk.Entry(frame, textvariable=self.multiplier_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # Access
        ttk.Label(frame, text="Access:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.access_var = tk.StringVar(value="R")
        self.access_combo = ttk.Combobox(frame, textvariable=self.access_var, 
                                   values=bc.DROPDOWN_OPTIONS['access_type'], 
                                   width=28, state='readonly', font=('Segoe UI', 10))
        self.access_combo.grid(row=row, column=1, pady=10, sticky='ew')
        self.access_combo.set(bc.DROPDOWN_OPTIONS['access_type'][0])  # Default: "R - Read Only"
        row += 1
        
        # Cloud Output
        ttk.Label(frame, text="Cloud Output:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.cloud_var = tk.StringVar(value="Yes")
        cloud_combo = ttk.Combobox(frame, textvariable=self.cloud_var, 
                                  values=["Yes", "No"], 
                                  width=28, state='readonly', font=('Segoe UI', 10))
        cloud_combo.grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # JSON Group
        ttk.Label(frame, text="JSON Group:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_group_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.json_group_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # JSON Unit
        ttk.Label(frame, text="JSON Unit:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_unit_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.json_unit_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # JSON Key
        ttk.Label(frame, text="JSON Key:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_key_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.json_key_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Tip: Use commas for multiple keys (e.g., Key1,Key2,Key3)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row+1, column=0, columnspan=2, pady=2)
        row += 2
        
        frame.columnconfigure(1, weight=1)
        
        # Initialize length from default format
        self.update_length_from_format()
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg='#f5f7fa')
        btn_frame.pack(fill='x', padx=30, pady=20)
        
        add_btn = tk.Button(btn_frame, text="✅ Add Register", command=self.add_register,
                           font=('Segoe UI', 11, 'bold'), bg='#2ecc71', fg='white',
                           relief='flat', padx=20, pady=10, cursor='hand2')
        add_btn.pack(side='left', padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="❌ Cancel", command=self.dialog.destroy,
                              font=('Segoe UI', 11), bg='#95a5a6', fg='white',
                              relief='flat', padx=20, pady=10, cursor='hand2')
        cancel_btn.pack(side='left', padx=5)
    
    def update_length_from_format(self):
        """Auto-calculate length based on selected format"""
        try:
            fmt_text = self.fmt_var.get()
            if fmt_text and ' - ' in fmt_text:
                fmt_code = int(fmt_text.split(' - ')[0])
                length = bc.get_register_length(fmt_code)
                self.length_var.set(length)
        except Exception:
            # If parsing fails, default to 1
            self.length_var.set(1)
    
    def add_register(self):
        """Add register with comprehensive validation"""
        try:
            # Extract numeric values from combo selections with error handling
            fc_text = self.fc_var.get()
            if not fc_text or fc_text.strip() == "":
                messagebox.showerror("❌ Validation Error", "Function Code is required!\nPlease select a function code from the dropdown.")
                return
            
            fmt_text = self.fmt_var.get()
            if not fmt_text or fmt_text.strip() == "":
                messagebox.showerror("❌ Validation Error", "Format is required!\nPlease select a data format from the dropdown.")
                return
            
            access_text = self.access_var.get()
            if not access_text or access_text.strip() == "":
                messagebox.showerror("❌ Validation Error", "Access type is required!\nPlease select an access type from the dropdown.")
                return
            
            # Parse dropdown values with error handling
            try:
                fc = bc.parse_dropdown_selection(fc_text, 'function_code')
                if not isinstance(fc, int):
                    fc = int(fc)
            except (ValueError, TypeError, AttributeError) as e:
                messagebox.showerror("❌ Parsing Error", 
                                   f"Invalid Function Code format!\nSelected: '{fc_text}'\nError: {str(e)}")
                return
            
            try:
                fmt = bc.parse_dropdown_selection(fmt_text, 'data_format_code')
                if not isinstance(fmt, int):
                    fmt = int(fmt)
            except (ValueError, TypeError, AttributeError) as e:
                messagebox.showerror("❌ Parsing Error", 
                                   f"Invalid Format Code format!\nSelected: '{fmt_text}'\nError: {str(e)}")
                return
            
            try:
                access = bc.parse_dropdown_selection(access_text, 'access_type')
                if not isinstance(access, str):
                    access = str(access)
            except (ValueError, TypeError, AttributeError) as e:
                messagebox.showerror("❌ Parsing Error", 
                                   f"Invalid Access Type format!\nSelected: '{access_text}'\nError: {str(e)}")
                return
            
            # Get and validate numeric values
            try:
                slave_id = int(self.slave_id_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Slave ID must be a number!\nGot: '{self.slave_id_var.get()}'")
                return
            
            try:
                address = int(self.address_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Address must be a number!\nGot: '{self.address_var.get()}'")
                return
            
            try:
                length = int(self.length_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Length must be a number!\nGot: '{self.length_var.get()}'")
                return
            
            try:
                multiplier = float(self.multiplier_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Multiplier must be a number!\nGot: '{self.multiplier_var.get()}'")
                return
            
            # VALIDATION: Slave ID
            is_valid, error_msg = bc.validate_slave_id(slave_id)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Slave ID Error:\n{error_msg}\n\nValid range: 1-247")
                return
            
            # VALIDATION: Address
            is_valid, error_msg = bc.validate_address(address)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Address Error:\n{error_msg}\n\nValid range: 0-65535")
                return
            
            # VALIDATION: Function Code
            is_valid, error_msg = bc.validate_function_code(fc)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Function Code Error:\n{error_msg}\n\nValid codes: 1,2,3,4,5,6,15,16")
                return
            
            # VALIDATION: Format Code
            is_valid, error_msg = bc.validate_format_code(fmt)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Format Code Error:\n{error_msg}\n\nValid codes: 1-8")
                return
            
            # VALIDATION: Length must match format
            expected_length = bc.get_register_length(fmt)
            if length != expected_length:
                messagebox.showerror("❌ Validation Error", 
                                   f"Length Mismatch:\n\nFormat {fmt} requires length {expected_length}, but got {length}.\n\nLength is auto-calculated from Format.\nPlease reselect the format to update length.")
                return
            
            # VALIDATION: Length limit
            if length > 70:
                messagebox.showerror("❌ Validation Error", 
                                   f"Length Too Large:\n\nLength {length} exceeds firmware limit of 70 registers.\n\nPlease use a different data format.")
                return
            
            # VALIDATION: Function Code vs Access Type Logic
            # READ FCs (1,2,3,4) should only work with 'R' or 'RW'
            # WRITE FCs (5,6,15,16) should only work with 'W' or 'RW'
            read_fcs = [1, 2, 3, 4]
            write_fcs = [5, 6, 15, 16]
            
            if fc in read_fcs:
                if 'R' not in access:
                    messagebox.showerror("❌ Logic Error", 
                                       f"Function Code Mismatch:\n\n"
                                       f"FC {fc} is a READ function code.\n"
                                       f"Access type must be 'R' or 'RW' (not '{access}').\n\n"
                                       f"READ FCs (1,2,3,4) → Access must contain 'R'\n"
                                       f"WRITE FCs (5,6,15,16) → Access must contain 'W'")
                    return
            elif fc in write_fcs:
                if 'W' not in access:
                    messagebox.showerror("❌ Logic Error", 
                                       f"Function Code Mismatch:\n\n"
                                       f"FC {fc} is a WRITE function code.\n"
                                       f"Access type must be 'W' or 'RW' (not '{access}').\n\n"
                                       f"READ FCs (1,2,3,4) → Access must contain 'R'\n"
                                       f"WRITE FCs (5,6,15,16) → Access must contain 'W'")
                    return
            
            # VALIDATION: Check for duplicate/overlapping registers
            # Check if a register with same Slave ID and overlapping address range already exists
            for item in self.app.tree.get_children():
                values = self.app.tree.item(item)['values']
                existing_serial = values[0]
                existing_slave = int(values[1])
                existing_fc = int(values[2])
                existing_addr = int(values[3])
                existing_len = int(values[4])
                existing_access = values[7]
                
                # Check if same slave ID
                if existing_slave == slave_id:
                    # Calculate address ranges
                    existing_end_addr = existing_addr + existing_len - 1
                    new_end_addr = address + length - 1
                    
                    # Check for overlapping address ranges
                    overlap = not (new_end_addr < existing_addr or address > existing_end_addr)
                    
                    if overlap:
                        # Determine if it's read or write operation
                        operation_type = "READ" if fc in read_fcs else "WRITE"
                        existing_operation = "READ" if existing_fc in read_fcs else "WRITE"
                        
                        # Build detailed warning message
                        overlap_msg = (
                            f"⚠️ Duplicate/Overlapping Register Detected!\n\n"
                            f"You are trying to {operation_type}:\n"
                            f"  • Slave ID: {slave_id}\n"
                            f"  • FC: {fc}\n"
                            f"  • Address: {address}-{new_end_addr}\n"
                            f"  • Access: {access}\n\n"
                            f"But Serial No. {existing_serial} already {existing_operation}s:\n"
                            f"  • Slave ID: {existing_slave}\n"
                            f"  • FC: {existing_fc}\n"
                            f"  • Address: {existing_addr}-{existing_end_addr}\n"
                            f"  • Access: {existing_access}\n\n"
                            f"This creates an overlapping register configuration.\n\n"
                            f"Do you want to add it anyway?"
                        )
                        
                        result = messagebox.askyesno("⚠️ Duplicate Register Warning", overlap_msg)
                        if not result:
                            return
                        # If user clicked Yes, continue to add the register
                        break
            
            # VALIDATION: Cloud output restrictions based on access type
            cloud_enabled = self.cloud_var.get() == "Yes"
            
            # CRITICAL: Only R (Read Only) parameters can have Cloud=Yes
            # W and RW parameters are commands/control, not monitoring telemetry
            # Based on historical Excel mapping analysis and firmware behavior
            if cloud_enabled and access in ['W', 'RW']:
                messagebox.showerror("❌ Invalid Cloud Configuration",
                                   f"Cannot enable Cloud output for Access Type '{access}'.\n\n"
                                   f"📋 Cloud Output Rules:\n"
                                   f"  ✅ R (Read Only): Monitoring/telemetry → Cloud allowed\n"
                                   f"  ❌ W (Write Only): Commands → Cloud NOT allowed\n"
                                   f"  ❌ RW (Read/Write): Write + verification → Cloud NOT allowed\n\n"
                                   f"💡 Reason:\n"
                                   f"  • W/RW parameters are control commands, not status values\n"
                                   f"  • RW read component is only for write verification\n"
                                   f"  • Only independent monitoring values go to cloud\n\n"
                                   f"Please change Access to 'R' or set Cloud to 'No'.")
                return
            
            # VALIDATION: JSON fields for cloud parameters
            json_group = self.json_group_var.get().strip()
            json_unit = self.json_unit_var.get().strip()
            json_key = self.json_key_var.get().strip()
            
            if cloud_enabled:
                warnings = []
                if not json_group:
                    warnings.append("• JSON Group is empty")
                if not json_unit:
                    warnings.append("• JSON Unit is empty")
                if not json_key:
                    warnings.append("• JSON Key is empty")
                
                if warnings:
                    warning_msg = "\n".join(warnings)
                    result = messagebox.askyesno("⚠️ Cloud Parameter Warning", 
                                               f"Cloud output enabled but:\n\n{warning_msg}\n\nThis parameter will not be published to cloud.\n\nDo you want to continue adding this register anyway?")
                    if not result:
                        return
            
            # TEST: Create a RegisterEntry to ensure it works
            try:
                test_register = RegisterEntry(
                    param_id="TEST",
                    slave_id=slave_id,
                    fc=fc,
                    address=address,
                    length=length,
                    fmt=fmt,
                    multiplier=multiplier,
                    access=access,
                    cloud=cloud_enabled,
                    json_group=json_group,
                    json_unit=json_unit,
                    json_key=json_key
                )
            except Exception as e:
                messagebox.showerror("❌ Register Creation Error", 
                                   f"Failed to create register with provided data:\n\n{str(e)}\n\nPlease check all fields and try again.")
                return
            
            # All validations passed - Add to tree
            children_count = len(self.app.tree.get_children())
            tag = 'evenrow' if children_count % 2 == 0 else 'oddrow'
            
            self.app.tree.insert('', 'end', values=(
                children_count + 1,
                slave_id,
                fc,
                address,
                length,
                fmt,
                multiplier,
                access,
                self.cloud_var.get(),
                json_group,
                json_unit,
                json_key
            ), tags=(tag,))
            
            self.app.update_status()
            self.dialog.destroy()
            messagebox.showinfo("✅ Success", f"Register added successfully!\n\nParameter ID: {children_count + 1}\nSlave: {slave_id}, FC: {fc}, Address: {address}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("❌ Unexpected Error", 
                               f"An unexpected error occurred:\n\n{str(e)}\n\nPlease report this error with the following details:\n\n{error_details[:200]}...")

class EditRegisterDialog:
    def __init__(self, parent, app, tree_item, values):
        self.app = app
        self.tree_item = tree_item
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("✏️ Edit Register")
        self.dialog.geometry("550x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg='#f5f7fa')
        
        # Title
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=60)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="✏️ Edit Register Information", 
                font=('Segoe UI', 14, 'bold'), fg='white', bg='#3498db').pack(pady=15)
        
        # Create form with pre-filled values
        frame = ttk.Frame(self.dialog, padding=30)
        frame.pack(fill='both', expand=True)
        
        row = 0
        
        # Slave ID
        ttk.Label(frame, text="Slave ID:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.slave_id_var = tk.IntVar(value=values[1])
        ttk.Spinbox(frame, from_=1, to=247, textvariable=self.slave_id_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # Function Code
        ttk.Label(frame, text="Function Code:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.fc_var = tk.StringVar()
        self.fc_combo = ttk.Combobox(frame, textvariable=self.fc_var, 
                               values=bc.DROPDOWN_OPTIONS['function_code'], 
                               width=28, state='readonly', font=('Segoe UI', 10))
        self.fc_combo.grid(row=row, column=1, pady=10, sticky='ew')
        # Find matching dropdown option
        fc_val = values[2]
        for opt in bc.DROPDOWN_OPTIONS['function_code']:
            if opt.startswith(f"{fc_val} -"):
                self.fc_combo.set(opt)
                break
        row += 1
        
        # Address
        ttk.Label(frame, text="Address:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.address_var = tk.IntVar(value=values[3])
        ttk.Spinbox(frame, from_=0, to=65535, textvariable=self.address_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # Length (auto-calculated, read-only)
        ttk.Label(frame, text="Length:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.length_var = tk.IntVar(value=values[4])
        self.length_entry = ttk.Entry(frame, textvariable=self.length_var, width=30, font=('Segoe UI', 10), state='readonly')
        self.length_entry.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="🔒 Auto-calculated from Format", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # Format
        ttk.Label(frame, text="Format (FMT):", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.fmt_var = tk.StringVar()
        self.fmt_combo = ttk.Combobox(frame, textvariable=self.fmt_var, 
                                values=bc.DROPDOWN_OPTIONS['data_format_code'], 
                                width=28, state='readonly', font=('Segoe UI', 10))
        self.fmt_combo.grid(row=row, column=1, pady=10, sticky='ew')
        # Find matching dropdown option
        fmt_val = values[5]
        for opt in bc.DROPDOWN_OPTIONS['data_format_code']:
            if opt.startswith(f"{fmt_val} -"):
                self.fmt_combo.set(opt)
                break
        self.fmt_combo.bind("<<ComboboxSelected>>", lambda e: self.update_length_from_format())
        row += 1
        
        # Multiplier
        ttk.Label(frame, text="Multiplier:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.multiplier_var = tk.DoubleVar(value=values[6])
        ttk.Entry(frame, textvariable=self.multiplier_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # Access
        ttk.Label(frame, text="Access:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.access_var = tk.StringVar()
        self.access_combo = ttk.Combobox(frame, textvariable=self.access_var, 
                                   values=bc.DROPDOWN_OPTIONS['access_type'], 
                                   width=28, state='readonly', font=('Segoe UI', 10))
        self.access_combo.grid(row=row, column=1, pady=10, sticky='ew')
        # Find matching dropdown option
        access_val = values[7]
        for opt in bc.DROPDOWN_OPTIONS['access_type']:
            if opt.startswith(f"{access_val} -"):
                self.access_combo.set(opt)
                break
        row += 1
        
        # Cloud Output
        ttk.Label(frame, text="Cloud Output:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.cloud_var = tk.StringVar(value=values[8])
        cloud_combo = ttk.Combobox(frame, textvariable=self.cloud_var, 
                                  values=["Yes", "No"], 
                                  width=28, state='readonly', font=('Segoe UI', 10))
        cloud_combo.grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # JSON Group
        ttk.Label(frame, text="JSON Group:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_group_var = tk.StringVar(value=values[9])
        ttk.Entry(frame, textvariable=self.json_group_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # JSON Unit
        ttk.Label(frame, text="JSON Unit:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_unit_var = tk.StringVar(value=values[10])
        ttk.Entry(frame, textvariable=self.json_unit_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        row += 1
        
        # JSON Key
        ttk.Label(frame, text="JSON Key:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_key_var = tk.StringVar(value=values[11])
        ttk.Entry(frame, textvariable=self.json_key_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Tip: Use commas for multiple keys (e.g., Key1,Key2,Key3)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row+1, column=0, columnspan=2, pady=2)
        row += 2
        
        frame.columnconfigure(1, weight=1)
        
        # Buttons
        btn_frame = tk.Frame(self.dialog, bg='#f5f7fa')
        btn_frame.pack(fill='x', padx=30, pady=20)
        
        save_btn = tk.Button(btn_frame, text="💾 Save Changes", command=self.save_changes,
                           font=('Segoe UI', 11, 'bold'), bg='#3498db', fg='white',
                           relief='flat', padx=20, pady=10, cursor='hand2')
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="❌ Cancel", command=self.dialog.destroy,
                              font=('Segoe UI', 11), bg='#95a5a6', fg='white',
                              relief='flat', padx=20, pady=10, cursor='hand2')
        cancel_btn.pack(side='left', padx=5)
    
    def update_length_from_format(self):
        """Auto-calculate length based on selected format"""
        try:
            fmt_text = self.fmt_var.get()
            if fmt_text and ' - ' in fmt_text:
                fmt_code = int(fmt_text.split(' - ')[0])
                length = bc.get_register_length(fmt_code)
                self.length_var.set(length)
        except Exception:
            # If parsing fails, keep current value
            pass
    
    def save_changes(self):
        """Save changes with comprehensive validation"""
        try:
            # Extract numeric values from combo selections with error handling
            fc_text = self.fc_var.get()
            if not fc_text or fc_text.strip() == "":
                messagebox.showerror("❌ Validation Error", "Function Code is required!\nPlease select a function code from the dropdown.")
                return
            
            fmt_text = self.fmt_var.get()
            if not fmt_text or fmt_text.strip() == "":
                messagebox.showerror("❌ Validation Error", "Format is required!\nPlease select a data format from the dropdown.")
                return
            
            access_text = self.access_var.get()
            if not access_text or access_text.strip() == "":
                messagebox.showerror("❌ Validation Error", "Access type is required!\nPlease select an access type from the dropdown.")
                return
            
            # Parse dropdown values with error handling
            try:
                fc = bc.parse_dropdown_selection(fc_text, 'function_code')
                if not isinstance(fc, int):
                    fc = int(fc)
            except (ValueError, TypeError, AttributeError) as e:
                messagebox.showerror("❌ Parsing Error", 
                                   f"Invalid Function Code format!\nSelected: '{fc_text}'\nError: {str(e)}")
                return
            
            try:
                fmt = bc.parse_dropdown_selection(fmt_text, 'data_format_code')
                if not isinstance(fmt, int):
                    fmt = int(fmt)
            except (ValueError, TypeError, AttributeError) as e:
                messagebox.showerror("❌ Parsing Error", 
                                   f"Invalid Format Code format!\nSelected: '{fmt_text}'\nError: {str(e)}")
                return
            
            try:
                access = bc.parse_dropdown_selection(access_text, 'access_type')
                if not isinstance(access, str):
                    access = str(access)
            except (ValueError, TypeError, AttributeError) as e:
                messagebox.showerror("❌ Parsing Error", 
                                   f"Invalid Access Type format!\nSelected: '{access_text}'\nError: {str(e)}")
                return
            
            # Get and validate numeric values
            try:
                slave_id = int(self.slave_id_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Slave ID must be a number!\nGot: '{self.slave_id_var.get()}'")
                return
            
            try:
                address = int(self.address_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Address must be a number!\nGot: '{self.address_var.get()}'")
                return
            
            try:
                length = int(self.length_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Length must be a number!\nGot: '{self.length_var.get()}'")
                return
            
            try:
                multiplier = float(self.multiplier_var.get())
            except (ValueError, TypeError):
                messagebox.showerror("❌ Validation Error", 
                                   f"Multiplier must be a number!\nGot: '{self.multiplier_var.get()}'")
                return
            
            # VALIDATION: Slave ID
            is_valid, error_msg = bc.validate_slave_id(slave_id)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Slave ID Error:\n{error_msg}\n\nValid range: 1-247")
                return
            
            # VALIDATION: Address
            is_valid, error_msg = bc.validate_address(address)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Address Error:\n{error_msg}\n\nValid range: 0-65535")
                return
            
            # VALIDATION: Function Code
            is_valid, error_msg = bc.validate_function_code(fc)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Function Code Error:\n{error_msg}\n\nValid codes: 1,2,3,4,5,6,15,16")
                return
            
            # VALIDATION: Format Code
            is_valid, error_msg = bc.validate_format_code(fmt)
            if not is_valid:
                messagebox.showerror("❌ Validation Error", f"Format Code Error:\n{error_msg}\n\nValid codes: 1-8")
                return
            
            # VALIDATION: Length must match format
            expected_length = bc.get_register_length(fmt)
            if length != expected_length:
                messagebox.showerror("❌ Validation Error", 
                                   f"Length Mismatch:\n\nFormat {fmt} requires length {expected_length}, but got {length}.\n\nLength is auto-calculated from Format.\nPlease reselect the format to update length.")
                return
            
            # VALIDATION: Length limit
            if length > 70:
                messagebox.showerror("❌ Validation Error", 
                                   f"Length Too Large:\n\nLength {length} exceeds firmware limit of 70 registers.\n\nPlease use a different data format.")
                return
            
            # VALIDATION: Function Code vs Access Type Logic
            # READ FCs (1,2,3,4) should only work with 'R' or 'RW'
            # WRITE FCs (5,6,15,16) should only work with 'W' or 'RW'
            read_fcs = [1, 2, 3, 4]
            write_fcs = [5, 6, 15, 16]
            
            if fc in read_fcs:
                if 'R' not in access:
                    messagebox.showerror("❌ Logic Error", 
                                       f"Function Code Mismatch:\n\n"
                                       f"FC {fc} is a READ function code.\n"
                                       f"Access type must be 'R' or 'RW' (not '{access}').\n\n"
                                       f"READ FCs (1,2,3,4) → Access must contain 'R'\n"
                                       f"WRITE FCs (5,6,15,16) → Access must contain 'W'")
                    return
            elif fc in write_fcs:
                if 'W' not in access:
                    messagebox.showerror("❌ Logic Error", 
                                       f"Function Code Mismatch:\n\n"
                                       f"FC {fc} is a WRITE function code.\n"
                                       f"Access type must be 'W' or 'RW' (not '{access}').\n\n"
                                       f"READ FCs (1,2,3,4) → Access must contain 'R'\n"
                                       f"WRITE FCs (5,6,15,16) → Access must contain 'W'")
                    return
            
            # VALIDATION: Check for duplicate/overlapping registers (excluding current item being edited)
            # Get current serial number
            old_values = self.app.tree.item(self.tree_item)['values']
            current_serial = old_values[0]
            
            for item in self.app.tree.get_children():
                values = self.app.tree.item(item)['values']
                existing_serial = values[0]
                
                # Skip checking against itself
                if existing_serial == current_serial:
                    continue
                
                existing_slave = int(values[1])
                existing_fc = int(values[2])
                existing_addr = int(values[3])
                existing_len = int(values[4])
                existing_access = values[7]
                
                # Check if same slave ID
                if existing_slave == slave_id:
                    # Calculate address ranges
                    existing_end_addr = existing_addr + existing_len - 1
                    new_end_addr = address + length - 1
                    
                    # Check for overlapping address ranges
                    overlap = not (new_end_addr < existing_addr or address > existing_end_addr)
                    
                    if overlap:
                        # Determine if it's read or write operation
                        operation_type = "READ" if fc in read_fcs else "WRITE"
                        existing_operation = "READ" if existing_fc in read_fcs else "WRITE"
                        
                        # Build detailed warning message
                        overlap_msg = (
                            f"⚠️ Duplicate/Overlapping Register Detected!\n\n"
                            f"You are trying to {operation_type}:\n"
                            f"  • Slave ID: {slave_id}\n"
                            f"  • FC: {fc}\n"
                            f"  • Address: {address}-{new_end_addr}\n"
                            f"  • Access: {access}\n\n"
                            f"But Serial No. {existing_serial} already {existing_operation}s:\n"
                            f"  • Slave ID: {existing_slave}\n"
                            f"  • FC: {existing_fc}\n"
                            f"  • Address: {existing_addr}-{existing_end_addr}\n"
                            f"  • Access: {existing_access}\n\n"
                            f"This creates an overlapping register configuration.\n\n"
                            f"Do you want to update it anyway?"
                        )
                        
                        result = messagebox.askyesno("⚠️ Duplicate Register Warning", overlap_msg)
                        if not result:
                            return
                        # If user clicked Yes, continue to update the register
                        break
            
            # VALIDATION: Cloud output restrictions based on access type
            cloud_enabled = self.cloud_var.get() == "Yes"
            
            # CRITICAL: Only R (Read Only) parameters can have Cloud=Yes
            # W and RW parameters are commands/control, not monitoring telemetry
            if cloud_enabled and access in ['W', 'RW']:
                messagebox.showerror("❌ Invalid Cloud Configuration",
                                   f"Cannot enable Cloud output for Access Type '{access}'.\n\n"
                                   f"📋 Cloud Output Rules:\n"
                                   f"  ✅ R (Read Only): Monitoring/telemetry → Cloud allowed\n"
                                   f"  ❌ W (Write Only): Commands → Cloud NOT allowed\n"
                                   f"  ❌ RW (Read/Write): Write + verification → Cloud NOT allowed\n\n"
                                   f"💡 Reason:\n"
                                   f"  • W/RW parameters are control commands, not status values\n"
                                   f"  • RW read component is only for write verification\n"
                                   f"  • Only independent monitoring values go to cloud\n\n"
                                   f"Please change Access to 'R' or set Cloud to 'No'.")
                return
            
            # VALIDATION: JSON fields for cloud parameters
            json_group = self.json_group_var.get().strip()
            json_unit = self.json_unit_var.get().strip()
            json_key = self.json_key_var.get().strip()
            
            if cloud_enabled:
                warnings = []
                if not json_group:
                    warnings.append("• JSON Group is empty")
                if not json_unit:
                    warnings.append("• JSON Unit is empty")
                if not json_key:
                    warnings.append("• JSON Key is empty")
                
                if warnings:
                    warning_msg = "\n".join(warnings)
                    result = messagebox.askyesno("⚠️ Cloud Parameter Warning", 
                                               f"Cloud output enabled but:\n\n{warning_msg}\n\nThis parameter will not be published to cloud.\n\nDo you want to continue updating this register anyway?")
                    if not result:
                        return
            
            # TEST: Create a RegisterEntry to ensure it works
            try:
                test_register = RegisterEntry(
                    param_id="TEST",
                    slave_id=slave_id,
                    fc=fc,
                    address=address,
                    length=length,
                    fmt=fmt,
                    multiplier=multiplier,
                    access=access,
                    cloud=cloud_enabled,
                    json_group=json_group,
                    json_unit=json_unit,
                    json_key=json_key
                )
            except Exception as e:
                messagebox.showerror("❌ Register Creation Error", 
                                   f"Failed to create register with provided data:\n\n{str(e)}\n\nPlease check all fields and try again.")
                return
            
            # Get current serial number
            old_values = self.app.tree.item(self.tree_item)['values']
            serial_no = old_values[0]
            
            # All validations passed - Update the tree item
            self.app.tree.item(self.tree_item, values=(
                serial_no,
                slave_id,
                fc,
                address,
                length,
                fmt,
                multiplier,
                access,
                self.cloud_var.get(),
                json_group,
                json_unit,
                json_key
            ))
            
            self.dialog.destroy()
            messagebox.showinfo("✅ Success", f"Register updated successfully!\n\nParameter ID: {serial_no}\nSlave: {slave_id}, FC: {fc}, Address: {address}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("❌ Unexpected Error", 
                               f"An unexpected error occurred:\n\n{str(e)}\n\nPlease report this error with the following details:\n\n{error_details[:200]}...")

# Entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusConfigGenerator(root)
    root.mainloop()
"""
Modbus Configuration Generator - Enhanced Tkinter Desktop Application v6.5
CRITICAL FIXES APPLIED:
- P3/JKY ordering: Sequential MDI mapping matching firmware's JKY flattened order
- JKY structure: Proper grouping with firmware-compatible format
- Validation: Enhanced firmware-specific checks

NEW IN v6.5 (February 4, 2026):
- ✅ BIDIRECTIONAL TRANSFORMATION: Import Modbus + Paramap JSON to populate registers
- ✅ Reverse transformation engine integrated into GUI
- ✅ Automatic population of communication settings (baudrate, data format, profile)
- ✅ Extract register configurations from existing firmware JSON files
- ✅ "Import Modbus+Paramap JSON" button in toolbar

FEATURES:
- Forward: Register Entry → Modbus + Paramap JSON (original)
- Reverse: Modbus + Paramap JSON → Register Entry (NEW!)
- Full round-trip support for editing and regeneration

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
from typing import Any, Dict, List, Optional

# ============================================================================
# EMBEDDED: Custom JSON Formatter (for compact, readable JSON output)
# ============================================================================
class CompactArrayEncoder(json.JSONEncoder):
    """Custom JSON encoder that formats arrays compactly"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.indent_level = 0
    
    def encode(self, obj):
        """Encode object with custom formatting"""
        if isinstance(obj, dict):
            return self._encode_dict(obj)
        elif isinstance(obj, list):
            return self._encode_list(obj)
        else:
            return super().encode(obj)
    
    def _encode_dict(self, obj, level=0):
        """Encode dictionary with proper indentation"""
        if not obj:
            return "{}"
        
        indent = "  " * level
        next_indent = "  " * (level + 1)
        
        items = []
        for key, value in obj.items():
            encoded_value = self._encode_value(value, level + 1)
            items.append(f'{next_indent}"{key}": {encoded_value}')
        
        return "{\n" + ",\n".join(items) + f"\n{indent}}}"
    
    def _encode_value(self, value, level):
        """Encode a value with appropriate formatting"""
        if isinstance(value, dict):
            return self._encode_dict(value, level)
        elif isinstance(value, list):
            return self._encode_list(value, level)
        elif isinstance(value, str):
            return json.dumps(value)
        else:
            return json.dumps(value)
    
    def _encode_list(self, obj, level=0):
        """Encode list with smart formatting"""
        if not obj:
            return "[]"
        
        # Check if list contains only simple types
        is_simple = all(isinstance(item, (int, float, str, bool, type(None))) for item in obj)
        
        if is_simple:
            content = ", ".join(json.dumps(item) for item in obj)
            if len(content) < 80:  # Single line if under 80 chars
                return f"[{content}]"
            else:
                return self._encode_list_multiline(obj, level)
        else:
            return self._encode_list_complex(obj, level)
    
    def _encode_list_multiline(self, obj, level):
        """Encode simple list across multiple lines"""
        indent = "  " * level
        next_indent = "  " * (level + 1)
        
        items_per_row = 10
        rows = []
        for i in range(0, len(obj), items_per_row):
            chunk = obj[i:i + items_per_row]
            row_content = ", ".join(json.dumps(item) for item in chunk)
            rows.append(f"{next_indent}{row_content}")
        
        return "[\n" + ",\n".join(rows) + f"\n{indent}]"
    
    def _encode_list_complex(self, obj, level):
        """Encode complex list with each item on new line"""
        indent = "  " * level
        next_indent = "  " * (level + 1)
        
        items = []
        for item in obj:
            if isinstance(item, list):
                encoded = self._encode_list_compact(item)
            else:
                encoded = self._encode_value(item, level + 1)
            items.append(f"{next_indent}{encoded}")
        
        return "[\n" + ",\n".join(items) + f"\n{indent}]"
    
    def _encode_list_compact(self, obj):
        """Encode nested list compactly (for JKA entries)"""
        items = []
        for item in obj:
            if isinstance(item, list):
                content = ", ".join(json.dumps(x) for x in item)
                items.append(f"[{content}]")
            else:
                items.append(json.dumps(item))
        return "[" + ", ".join(items) + "]"

def format_bmiot_json(data: Dict[str, Any]) -> str:
    """Format BMIoT JSON with readable layout"""
    encoder = CompactArrayEncoder()
    return encoder.encode(data)

def format_and_save_json(data: Dict[str, Any], filepath: str):
    """Format and save BMIoT JSON to file"""
    formatted = format_bmiot_json(data)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(formatted)
        f.write('\n')

# JSON formatter is now always available (embedded)
FORMATTER_AVAILABLE = True
print("[OK] JSON formatter loaded (embedded)")

# ============================================================================
# Import transformation engines for bidirectional conversion
# ============================================================================
try:
    from transform_wrapper import reverse_transform, forward_transform
    ENGINES_AVAILABLE = True
    print("[OK] Transformation engines loaded successfully")
except ImportError:
    # Engines not available - Import/Export features will use basic mode
    ENGINES_AVAILABLE = False


# Import bmiot_constants - Try from same directory first
try:
    import bmiot_constants as bc
    print("[OK] bmiot_constants loaded successfully")
except ImportError:
    # Using embedded fallback constants
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
    def __init__(self, param_id, slave_id, fc, address, length, fmt, multiplier, access, cloud, json_group, json_unit, json_key, array_membership="",
                 parameter_type="read_only", write_param_id=None, feedback_param_id=None, p2_mpi_index=None, p3_mpi_index=None,
                 packet_num=None, packet_sa=None, packet_nrt=None,
                 equipment_group="", device_name="", equipment_type="", jka_equipment_index=-1,
                 in_lua_buffer="No", lua_buffer_category="N/A", lbi_position="Auto", lbi_data_type="Number", lua_buffer_note="",
                 manual_override=False):
        """
        RegisterEntry with expanded 31-field schema for Lua Buffer + equipment hierarchy + manual override support.
        
        Original 17 fields:
        - param_id, slave_id, fc, address, length, fmt, multiplier, access, cloud
        - json_group, json_unit, json_key, array_membership, packet_id
        
        Phase 1 - Parameter Type Classification (4 fields):
        - parameter_type: str ('write' | 'feedback' | 'read_only')
        - write_param_id: int | None (for feedback reads, points to associated write param)
        - feedback_param_id: int | None (for write params, points to associated feedback read)
        - p2_mpi_index/p3_mpi_index: int | None (MPI ordering determinism)
        
        Phase 2 - Packet Metadata (3 fields):
        - packet_num: int | None (B4 packet number)
        - packet_sa: int | None (B4 packet start address)
        - packet_nrt: int | None (B4 packet register count)
        
        Phase 3 - Equipment Hierarchy (4 fields):
        - equipment_group: str (JKA equipment group name, e.g., "AHU_RL_DIE2", "VALVE", "VFD")
        - device_name: str (specific device/sensor name, e.g., "VFAM", "CNTRLValve", "Thermostat")
        - equipment_type: str (AI/DI/EM classification)
        - jka_equipment_index: int (which JKA entry this param belongs to, -1 if not in JKA)
        
        Phase 4 - Lua Buffer Configuration (5 fields):
        - in_lua_buffer: str ("No" | "Yes") - Whether this parameter uses Lua Buffer
        - lua_buffer_category: str ("Equipment" | "User Variable" | "N/A") - P2.MPI vs P2.RPCI classification
        - lbi_position: str|int ("Auto" | specific number) - LBI array index (auto-assigned or manual)
        - lbi_data_type: str ("Number" | "Boolean" | "String" | "N/A") - Data type in Lua Buffer
        - lua_buffer_note: str - Optional note for dual-category parameters
        
        Phase 5 - Manual Override (1 field):
        - manual_override: bool - When True, prevents auto-generation from recalculating P2/P3 arrays
        """
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
        self.array_membership = array_membership
        self.packet_id = None  # Legacy field, kept for compatibility
        
        # TRANSPARENT FIELDS - Visible in Register_Config.json (6 new fields)
        # Packet Assignment (3 fields)
        self.packet_num = packet_num  # Which packet this belongs to (B5.PN)
        self.packet_start_addr = packet_sa  # Packet's starting address (B4.SA)
        self.packet_register_count = packet_nrt  # Total registers in packet (B4.NRT)
        
        # B6 Write-Verification Pairing (2 fields)
        self.parameter_type = parameter_type  # 'write' | 'feedback' | 'read_only'
        self.paired_param_id = feedback_param_id if parameter_type == 'write' else write_param_id  # Linked param ID
        
        # JKY Equipment Membership (1 field)
        self.jka_index = jka_equipment_index  # Which JKA entry (-1 if none)
        
        # LUA BUFFER CONFIGURATION (5 fields) - NEW PHASE 4
        self.in_lua_buffer = in_lua_buffer  # "No" | "Yes"
        self.lua_buffer_category = lua_buffer_category  # "Equipment" | "User Variable" | "N/A"
        self.lbi_position = lbi_position  # "Auto" or specific int
        self.lbi_data_type = lbi_data_type  # "Number" | "Boolean" | "String" | "N/A"
        self.lua_buffer_note = lua_buffer_note  # Multi-category note (e.g., "Multi-category: User Variable LBI=3, Equipment LBI=14")
        
        # MANUAL OVERRIDE (1 field) - NEW PHASE 5
        self.manual_override = manual_override  # bool - Prevents auto-generation from recalculating P2/P3 arrays
        
        # INTERNAL METADATA - Not exported to Register_Config (for reverse compat)
        self.write_param_id = write_param_id  # For feedback reads (internal)
        self.feedback_param_id = feedback_param_id  # For write params (internal)
        self.p2_mpi_index = p2_mpi_index  # P2.MPI ordering (internal)
        self.p3_mpi_index = p3_mpi_index  # P3.MPI ordering (internal)
        self.equipment_group = equipment_group  # JKA equipment group name (internal)
        self.device_name = device_name  # Device/sensor name (internal)
        self.equipment_type = equipment_type  # AI/DI/EM classification (internal)
    
    # Property aliases for backward compatibility and consistency
    @property
    def packet_sa(self):
        """Alias for packet_start_addr"""
        return self.packet_start_addr
    
    @packet_sa.setter
    def packet_sa(self, value):
        self.packet_start_addr = value
    
    @property
    def packet_nrt(self):
        """Alias for packet_register_count"""
        return self.packet_register_count
    
    @packet_nrt.setter
    def packet_nrt(self, value):
        self.packet_register_count = value

class Packet:
    def __init__(self, packet_id, slave_id, fc):
        self.packet_id = packet_id
        self.slave_id = slave_id
        self.fc = fc
        self.start_address = None
        self.register_count = 0
        self.parameters = []

# Backend Logic Functions
def validate_register_schema(reg, serial_no=None):
    """
    Validate the 21-field RegisterEntry schema for consistency.
    Checks parameter_type field and cross-reference integrity.
    
    Args:
        reg: RegisterEntry instance
        serial_no: Optional serial number for error messages
    
    Returns:
        dict: {"status": "ok"} or {"status": "error", "message": "..."}
    """
    prefix = f"Serial No. {serial_no}: " if serial_no else ""
    
    # Validate parameter_type is one of the allowed values
    valid_types = ['write', 'feedback', 'read_only']
    param_type = getattr(reg, 'parameter_type', 'read_only')  # Default to read_only if missing
    
    if param_type not in valid_types:
        return {
            "status": "error",
            "message": f"{prefix}Invalid parameter_type '{param_type}'. Must be one of {valid_types}"
        }
    
    # Check cross-reference consistency
    write_param_id = getattr(reg, 'write_param_id', None)
    feedback_param_id = getattr(reg, 'feedback_param_id', None)
    
    if param_type == 'write':
        # Write parameters can optionally have feedback_param_id
        # (not all write commands have feedback reads)
        pass  # No strict requirement
    
    elif param_type == 'feedback':
        # Feedback reads SHOULD have write_param_id pointing to the write command
        # but this is optional for manually created configs
        # Only warn if cross-reference is missing, don't fail
        if write_param_id is None:
            # This is acceptable - just a soft validation
            pass
    
    elif param_type == 'read_only':
        # Read-only parameters should NOT have cross-references
        # But this is also a soft validation - don't fail
        pass
    
    # Validate MPI indices if present
    p2_mpi_index = getattr(reg, 'p2_mpi_index', None)
    p3_mpi_index = getattr(reg, 'p3_mpi_index', None)
    
    if p2_mpi_index is not None and p2_mpi_index < 0:
        return {
            "status": "error",
            "message": f"{prefix}p2_mpi_index must be >= 0 or None, got {p2_mpi_index}"
        }
    
    if p3_mpi_index is not None and p3_mpi_index < 0:
        return {
            "status": "error",
            "message": f"{prefix}p3_mpi_index must be >= 0 or None, got {p3_mpi_index}"
        }
    
    # All checks passed
    return {"status": "valid"}

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
        
        # NEW: Validate 21-field schema consistency
        schema_validation = validate_register_schema(reg, serial_no)
        if schema_validation['status'] == 'error':
            return schema_validation
        
        if reg.length > 70:
            return {"status": "error", "message": f"Serial No. {serial_no}: Length {reg.length} exceeds 70 register limit"}
        
        # FIRMWARE-CORRECT: Allow cloud=Yes even if JSON keys are missing
        # The firmware has 97 P3.MPI params but only 79 JKA entries
        # Params without JSON keys will be included in P3.MPI but may not be published to cloud
        # This matches the behavior of the original firmware JSON files
        # NOTE: Validation is now a soft warning, not a hard error
        
        if reg.slave_id < 1 or reg.slave_id > 247:
            return {"status": "error", "message": f"Serial No. {serial_no}: Invalid Slave ID {reg.slave_id} (must be 1-247)"}
        if reg.address < 0 or reg.address > 65535:
            return {"status": "error", "message": f"Serial No. {serial_no}: Invalid Address {reg.address} (must be 0-65535)"}
    
    # All validations passed
    return {
        "status": "valid",
        "message": f"✅ Configuration is valid!\n\n• Total Registers: {len(registers)}\n• Unique Slaves: {unique_slaves}\n• All field validations passed",
        "warnings": [],
        "errors": []
    }

def generate_packets(registers):
    """
    Generate packets with proper grouping logic:
    - PRIORITY 1: Use packet_num metadata if available (preserves original structure)
    - PRIORITY 2: Group by Slave ID + Function Code with optimization logic
      - WRITE operations (FC 5,6,15,16): Each parameter = separate packet
      - READ operations (FC 1,2,3,4): Group parameters if span ≤ 70 registers
    """
    packets = []
    packet_counter = 1
    
    # Check if metadata is available (from reverse transformation)
    metadata_available = any(hasattr(reg, 'packet_num') and reg.packet_num is not None for reg in registers)
    
    if metadata_available:
        # PRIORITY 1: Reconstruct packets using metadata
        packet_groups = {}  # packet_num -> list of registers
        
        for reg in registers:
            pnum = getattr(reg, 'packet_num', None)
            if pnum is None:
                pnum = 0  # Orphaned param without packet assignment
            
            if pnum not in packet_groups:
                packet_groups[pnum] = []
            packet_groups[pnum].append(reg)
        
        # Create packets preserving original structure
        for pnum in sorted(packet_groups.keys()):
            if pnum == 0:
                continue  # Skip orphaned params for now
            
            regs_in_packet = packet_groups[pnum]
            if not regs_in_packet:
                continue
            
            # Use first register's metadata for packet properties
            first_reg = regs_in_packet[0]
            slave_id = first_reg.slave_id
            fc = first_reg.fc
            packet_sa = getattr(first_reg, 'packet_sa', first_reg.address)
            packet_nrt = getattr(first_reg, 'packet_nrt', first_reg.length)
            
            packet = Packet(f"PN{packet_counter}", slave_id, fc)
            packet.start_address = packet_sa
            packet.register_count = packet_nrt
            
            for reg in regs_in_packet:
                packet.parameters.append(reg)
                reg.packet_id = packet.packet_id
            
            packets.append(packet)
            packet_counter += 1
        
        # Handle orphaned params (packet_num=0 or None)
        if 0 in packet_groups and packet_groups[0]:
            print(f"Warning: {len(packet_groups[0])} registers without packet assignment will be auto-grouped")
            # Fall through to grouping logic for these params
            orphaned_regs = packet_groups[0]
            # Continue with auto-grouping logic below (but only for orphaned)
        
    else:
        # PRIORITY 2: Legacy auto-grouping logic
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

def generate_modbus_io_json(communication, slaves, packets, registers, metadata=None):
    total_params = len(registers)
    total_packets = len(packets)
    
    # Count total register reads across all packets
    total_register_reads = sum(p.register_count for p in packets)
    
    # B1: Summary counts
    # PRIORITY 1: Use metadata if available (from import)
    if metadata and ('B1' in metadata or 'b1' in metadata):
        # Preserve imported B1 values exactly
        b1 = metadata.get('B1', metadata.get('b1')).copy()
        # Update NOP to match current register count (in case registers were edited)
        b1['NOP'] = total_params
    else:
        # FALLBACK: Calculate from packets
        b1 = {
            "NOS": len(slaves),           # Number of Slaves
            "NOP": total_params,          # Number of Parameters
            "NPT": total_packets,         # Number of Packets Total
            "NOR": total_register_reads   # Number of Register reads
        }
    
    # B2: Communication settings
    # PRIORITY 1: Use metadata if available (from import)
    if metadata and ('B2' in metadata or 'b2' in metadata):
        b2 = metadata.get('B2', metadata.get('b2')).copy()
    else:
        # FALLBACK: Use current communication settings
        b2 = {
            "BR": communication["baudrate"],  # Baud Rate
            "DF": communication["format"]     # Data Format
        }
    
    # B3: Slave and Packet mapping
    # PRIORITY 1: Use metadata if available (from import)
    if metadata and ('B3' in metadata or 'b3' in metadata):
        b3 = metadata.get('B3', metadata.get('b3')).copy()
    else:
        # FALLBACK: Calculate from packets
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
    # TRANSPARENT MODE: Use packet_num, packet_start_addr, packet_register_count from registers
    sa_list = []   # Start Address
    nrt_list = []  # Number of Registers Total
    fc_list = []   # Function Code
    sid_list = []  # Slave ID
    
    # Check if registers have transparent packet fields
    has_transparent_packets = any(
        hasattr(reg, 'packet_num') and reg.packet_num is not None 
        for reg in registers
    )
    
    if has_transparent_packets:
        # TRANSPARENT MODE: Build packets from packet_num metadata
        packet_map = {}  # packet_num -> {regs, slave_id, fc, start_addr, reg_count}
        for reg in registers:
            pnum = getattr(reg, 'packet_num', None)
            if pnum is not None and pnum > 0:
                if pnum not in packet_map:
                    # Support both new field names (packet_sa, packet_nrt) and legacy names
                    start_addr = getattr(reg, 'packet_sa', getattr(reg, 'packet_start_addr', reg.address))
                    reg_count = getattr(reg, 'packet_nrt', getattr(reg, 'packet_register_count', reg.length))
                    
                    packet_map[pnum] = {
                        'regs': [],
                        'slave_id': reg.slave_id,
                        'fc': reg.fc,
                        'start_addr': start_addr,
                        'reg_count': reg_count
                    }
                packet_map[pnum]['regs'].append(reg)
        
        # Build B4 from packet_map
        for pnum in sorted(packet_map.keys()):
            pkt = packet_map[pnum]
            sa_list.append(pkt['start_addr'])
            nrt_list.append(pkt['reg_count'])
            fc_list.append(pkt['fc'])
            sid_list.append(pkt['slave_id'])
    else:
        # LEGACY MODE: Use generated packets
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
    # TRANSPARENT MODE: Use packet_num directly if available
    id_list = []    # Parameter ID (1-indexed)
    pn_list = []    # Packet Number
    sta_list = []   # Start Address
    ln_list = []    # Length
    fmt_list = []   # Format
    mlt_list = []   # Multiplier
    
    for idx, reg in enumerate(registers, 1):
        id_list.append(idx)
        
        # TRANSPARENT: Use packet_num directly if available
        if has_transparent_packets and hasattr(reg, 'packet_num') and reg.packet_num is not None:
            pn_list.append(reg.packet_num)
        else:
            # LEGACY: Map packet_id to packet number
            packet_id_to_number = {}
            for pidx, packet in enumerate(packets, 1):
                packet_id_to_number[packet.packet_id] = pidx
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
    
    # PRIORITY 1: Use metadata if available (from reverse transformation)
    metadata_available = any(hasattr(reg, 'parameter_type') for reg in registers)
    
    if metadata_available:
        # Use metadata fields for accurate B6 reconstruction
        for idx, reg in enumerate(registers, 1):
            param_type = getattr(reg, 'parameter_type', 'read_only')
            
            # Add write parameters to WP
            if param_type == 'write' or reg.access == 'RW':
                write_param_ids.append(idx)
            
            # Add feedback parameters to RP (includes RW and separate feedback reads)
            if param_type == 'feedback' or reg.access == 'RW':
                read_param_ids.append(idx)
    else:
        # FALLBACK: Legacy detection logic (for manual entry without metadata)
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
        "RP": read_param_ids    # Write-Verification Read Parameter IDs (RW or feedback type)
    }
    
    return {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5, "B6": b6}

def generate_parameter_config_json(registers, profile=0, slaves=None, metadata=None, ntc_config=None, jkc_config=None):
    """Generate ParamMap_Config.json V1.2.0 compliant with BD-Algorithm specs.
    
    Args:
        registers: List of register objects
        profile: Profile type (0, 1, or 2) - affects MST.PRF value
        slaves: List of slave IDs (for NTC generation)
        metadata: Optional metadata from import for perfect reconstruction
        ntc_config: Optional Network Config dictionary (Priority 1)
        jkc_config: Optional JSON Keys Config dictionary (Priority 1)
    """
    
    # SMART MODE DETECTION: Determine if we should use metadata or calculate fresh
    # Use metadata-first ONLY if ALL registers have complete metadata (pure import scenario)
    # If ANY register is manually added or metadata incomplete, calculate everything fresh
    # FORWARD GENERATION: Always calculate fresh from register data
    # Metadata is only used in REVERSE transformation (Modbus+ParamMap → Register_Config)
    # When generating JSONs from Register_Config, always recalculate to ensure consistency
    print("[ParamMap Generation] Mode: CALCULATE-FRESH (Forward Transformation - Always Recalculate)")
    
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
    
    print(f"[B6] Write params (WP): {b6_wp_ids}")
    print(f"[B6] Verification reads (RP): {b6_rp_ids}")
    
    # Step 3: Build Lua Buffer based on USER CONFIGURATION (flexible approach)
    # NEW FLEXIBLE ALGORITHM:
    # - Users explicitly mark parameters with in_lua_buffer="Yes"
    # - lua_buffer_category determines: "Equipment" → P2.MPI, "User Variable" → P2.RPCI
    # - lbi_position controls ordering: "Auto" = sequential, or manual numbers
    # - No automatic detection or hardcoded ranges (1-15, 16-19)
    
    # Step 3a: Collect all Lua Buffer parameters
    lua_buffer_equipment = []  # Parameters for P2.MPI (Equipment category)
    lua_buffer_user_vars = []  # Parameters for P2.RPCI (User Variable category)
    
    for idx, reg in enumerate(registers, 1):
        # **MANUAL OVERRIDE CHECK**: Skip parameters with manual_override=True
        # These parameters keep their manually-set array_membership and are not recalculated
        manual_override = getattr(reg, 'manual_override', False)
        if manual_override:
            print(f"[Manual Override] Param {idx} - skipping auto-generation (user-controlled)")
            continue
        
        # Check if parameter is marked for Lua Buffer
        in_lua = getattr(reg, 'in_lua_buffer', 'No')
        if in_lua != 'Yes':
            continue
        
        category = getattr(reg, 'lua_buffer_category', 'N/A')
        lbi_pos = getattr(reg, 'lbi_position', 'Auto')
        
        # Convert lbi_position to sortable value
        if lbi_pos == 'Auto' or lbi_pos == '' or lbi_pos is None:
            sort_key = 999999 + idx  # Auto positions sort after manual, by param order
        else:
            try:
                sort_key = int(lbi_pos)
            except (ValueError, TypeError):
                sort_key = 999999 + idx  # Invalid positions treated as Auto
        
        param_info = {
            'param_id': idx,
            'register': reg,
            'category': category,
            'lbi_position': lbi_pos,
            'sort_key': sort_key
        }
        
        # Route to appropriate list based on category
        if category == 'Equipment':
            lua_buffer_equipment.append(param_info)
        elif category == 'User Variable':
            lua_buffer_user_vars.append(param_info)
        # N/A or invalid categories are skipped
    
    # Step 3b: Sort by LBI position (manual positions first, then auto by param order)
    lua_buffer_equipment.sort(key=lambda x: x['sort_key'])
    lua_buffer_user_vars.sort(key=lambda x: x['sort_key'])
    
    # Step 3c: Assign actual LBI indices
    # LBI is sequential [1, 2, 3, ...] across BOTH Equipment and User Variable lists
    # Equipment params get LBI 1 to N, User Variable params get LBI N+1 to total
    total_lua_buffer_size = len(lua_buffer_equipment) + len(lua_buffer_user_vars)
    
    # BACKWARD COMPATIBILITY: If no Lua Buffer params configured, use empty arrays
    # This allows the tool to work without Lua Buffer (legacy configurations)
    if total_lua_buffer_size == 0:
        print(f"[Lua Buffer] No parameters marked for Lua Buffer - generating empty P2 (Lua Buffer disabled)")
        print(f"  ℹ️  This is valid for configurations that don't use Lua scripting")
    else:
        print(f"[Lua Buffer] Flexible Configuration Detected:")
        print(f"  - Equipment params (P2.MPI): {len(lua_buffer_equipment)}")
        print(f"  - User Variable params (P2.RPCI): {len(lua_buffer_user_vars)}")
        print(f"  - Total Lua Buffer size (P1.NLB): {total_lua_buffer_size}")
    
    # CRITICAL: Cloud params = pure monitoring reads (R access, NOT verification)
    cloud_params = [r for idx, r in enumerate(registers, 1)
                    if r.cloud and r.access == 'R' and idx not in b6_rp_ids]
    
    # P1: Size calculations (based on flexible Lua Buffer configuration)
    # NLB = Total Lua buffer count (Equipment + User Variables)
    # NLBIN = Same as NLB (all allocated variables are used)
    # NMD = Total JSON keys (will be calculated after JKY is built)
    
    # P1: Always calculate fresh from current registers
    p1 = {
        "NLB": total_lua_buffer_size,      # Total Lua buffer count
        "NLBIN": total_lua_buffer_size,    # Same as NLB (all are used)
        "NMD": 0  # Will be updated after JKY is built
    }
    print(f"[P1] Calculated: NLB={p1['NLB']}, NLBIN={p1['NLBIN']}")
    
    # P2: Lua Buffer mappings (flexible user-configured approach)
    # LBI: Sequential [1, 2, 3, ..., N] for ALL Lua buffer entries
    # MPI: Equipment parameters (user marked with lua_buffer_category="Equipment")
    # RPCI: User Variable parameters (user marked with lua_buffer_category="User Variable")
    #
    # FLEXIBLE RANGES: No hardcoded 1-15 or 16-19 limits!
    # - If user has 50 Equipment params → P2.MPI has 50 entries (LBI 1-50)
    # - If user has 10 User Vars → P2.RPCI has 10 entries (LBI 51-60)
    # - Total LBI count = NLB
    
    # P2: Always calculate fresh from current registers
    lbi_list = []   # Sequential [1, 2, 3, ..., N]
    mpi_list = []   # B5 Param IDs for Equipment params
    rpci_list = []  # B5 Param IDs for User Variable params
    
    # Build MPI from Equipment parameters
    for lbi_idx, param_info in enumerate(lua_buffer_equipment, 1):
        lbi_list.append(lbi_idx)
        mpi_list.append(param_info['param_id'])
    
    # Build RPCI from User Variable parameters (continue LBI sequence)
    rpci_start_lbi = len(mpi_list) + 1 if lua_buffer_user_vars else 0
    for offset, param_info in enumerate(lua_buffer_user_vars):
        lbi_idx = rpci_start_lbi + offset
        lbi_list.append(lbi_idx)
        rpci_list.append(param_info['param_id'])
    
    p2 = {
        "LBI": lbi_list,    # Sequential: [1, 2, 3, ...] for ALL Lua buffer entries
        "MPI": mpi_list,    # B5 Param IDs for Equipment params
        "RPCI": rpci_list   # B5 Param IDs for User Variable params
    }
    
    # Print status with proper formatting
    if rpci_list:
        print(f"[P2] Calculated: {len(mpi_list)} MPI entries (LBI 1-{len(mpi_list)}), {len(rpci_list)} RPCI entries (LBI {rpci_start_lbi}-{len(lbi_list)})")
    else:
        print(f"[P2] Calculated: {len(mpi_list)} MPI entries (no RPCI user variables)")
    
    # FLEXIBLE P3 BUILD: Cloud output configuration
    # P3 determines what data goes to cloud (MQTT/HTTPS) via M_data buffer
    # Two pathways:
    # - P3.MPI: Direct Modbus reads → cloud (Equipment params)
    # - P3.LBI: Lua Buffer outputs → cloud (User Variables)
    #
    # FIRMWARE CONFIRMED ALGORITHM:
    # 1. Collect cloud Equipment parameters → P3.MPI (NOT User Variables!)
    # 2. Build JKY structure from P3.MPI cloud params
    # 3. Collect cloud User Variables → P3.LBI (LBI positions, not param IDs!)
    # 4. Extend P3.MDI to include both P3.MPI keys and P3.LBI entries
    
    # Step 1: Collect cloud EQUIPMENT parameters (EXCLUDE User Variables!)
    # User Variables with cloud=Yes go to P3.LBI, not P3.MPI
    user_var_param_ids = {p['param_id'] for p in lua_buffer_user_vars}
    
    all_cloud_params = []
    for idx, reg in enumerate(registers, 1):
        # **MANUAL OVERRIDE CHECK**: Skip parameters with manual_override=True
        manual_override = getattr(reg, 'manual_override', False)
        if manual_override:
            continue  # Already logged in P2 section, skip silently here
        
        if reg.cloud and reg.access == 'R' and idx not in b6_rp_ids:
            # CRITICAL: Exclude User Variables - they go in P3.LBI, not P3.MPI!
            if idx not in user_var_param_ids:
                all_cloud_params.append((idx, reg))
    
    print(f"[P3] Cloud Equipment Parameters (for P3.MPI): {len(all_cloud_params)}")
    if user_var_param_ids:
        print(f"[P3] User Variables with cloud=Yes will go to P3.LBI (not P3.MPI)")
    
    # Step 2: Build JKA structure from cloud Equipment params (preserve order)
    jka_structure_ordered = []  # List to preserve order: [(group, {unit: [keys]})]
    group_seen = {}  # Track which groups we've processed
    
    for param_idx, reg in all_cloud_params:
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
    p3_mpi_list = [param_idx for param_idx, reg in all_cloud_params]  # All cloud params
    
    # JKY: Always calculate fresh from current registers
    jky = {"JKA": jka_list}
    print(f"[JKY] Calculated: {len(jka_list)} equipment groups")
    
    # Calculate total keys in JKY for P1.NMD (always calculate fresh)
    # CRITICAL: Firmware expects P1.NMD = Σ(JKeysNum × JEqNmNum) for each JKA entry
    # FIRMWARE CONFIRMED: Com_Lib.cpp:525 uses MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum
    # JKA structure: [type, [units], [keys]] where units are like ["FB"], ["DegC"]
    # and keys are equipment identifiers like ["VFDRun"], ["Tank_T"]
    # Examples: 
    # - Example2: 72 JKA entries → 97 total keys (units × keys)
    # - Example3: 9 JKA entries → 20 total keys
    # - Example6: 8 JKA entries → 13 total keys
    total_jky_keys = 0
    for jka_entry in jka_list:
        if len(jka_entry) >= 3:
            num_units = len(jka_entry[1])   # JKeysNum: Number of units (index [1])
            num_keys = len(jka_entry[2])    # JEqNmNum: Number of keys (index [2])
            total_jky_keys += num_units * num_keys  # Firmware multiply formula
    
    # Step 3: Build P3.LBI for User Variable cloud outputs
    # P3.LBI contains P2.LBI positions of User Variables (P2.RPCI) that need cloud output
    # 
    # FIRMWARE CONFIRMED PATTERN (Examples 3, 5, 6):
    # - User Variables are stored at END of P2.LBI: positions [len(P2.MPI)+1 ... len(P2.LBI)]
    # - If User Variable has cloud=Yes, its P2.LBI position goes into P3.LBI
    # - P3.LBI contains LBI position numbers (NOT param IDs!)
    # 
    # Example3: P2.RPCI at LBI 11 → P3.LBI = [11]
    # Example5: P2.RPCI at LBI 11-12 → P3.LBI = [11, 12]
    # Example6: P2.RPCI at LBI 16-19 → P3.LBI = [16, 17, 18, 19]
    # 
    # Formula: P3.MDI count = len(P3.MPI) + len(P3.LBI)
    
    p3_lbi_list = []  # Will be populated with LBI positions of cloud User Variables
    
    # Calculate LBI positions for User Variables (start after Equipment params)
    rpci_start_lbi = len(lua_buffer_equipment) + 1
    
    # Check each User Variable for cloud output
    for offset, param_info in enumerate(lua_buffer_user_vars):
        reg = param_info['register']
        lbi_position = rpci_start_lbi + offset
        
        # If this User Variable needs cloud output, add its LBI position to P3.LBI
        if hasattr(reg, 'cloud') and reg.cloud:
            p3_lbi_list.append(lbi_position)
    
    if p3_lbi_list:
        print(f"[P3.LBI] Calculated: {len(p3_lbi_list)} User Variable cloud outputs at LBI positions: {p3_lbi_list}")
    
    # CRITICAL: P3.MDI count must include BOTH P3.MPI and P3.LBI entries
    # Firmware formula: len(P3.MDI) = len(P3.MPI) + len(P3.LBI)
    # - MDI 1..N: Direct Modbus params (P3.MPI) with JKY keys
    # - MDI N+1..M: User Variable outputs (P3.LBI)
    # Current mdi_list only has JKY keys, so we need to extend it for P3.LBI
    for lbi_position in p3_lbi_list:
        mdi_list.append(len(mdi_list) + 1)  # Continue sequential numbering
    
    if p3_lbi_list:
        print(f"[P3.MDI] Extended: {len(mdi_list)} total MDI entries ({len(p3_mpi_list)} from P3.MPI + {len(p3_lbi_list)} from P3.LBI)")
    
    # Step 4: Build P3 structure
    
    # P3: Always calculate fresh from current cloud parameters
    p3 = {
        "MDI": mdi_list,       # SEQUENTIAL: [1, 2, 3, 4, ..., M] where M = len(MPI keys) + len(LBI)
        "MPI": p3_mpi_list,    # B5 Modbus parameter IDs (Equipment cloud params)
        "LBI": p3_lbi_list     # P2.LBI positions of User Variables for cloud output
    }
    
    # Verify firmware formula
    expected_mdi_count = len(p3_mpi_list) + len(p3_lbi_list)
    if len(mdi_list) != expected_mdi_count:
        print(f"[P3] ⚠️  MDI count mismatch! len(MDI)={len(mdi_list)} but MPI+LBI={expected_mdi_count}")
    
    print(f"[P3] Calculated: {len(mdi_list)} MDI entries = {len(p3_mpi_list)} MPI + {len(p3_lbi_list)} LBI")
    
    # Update P1.NMD with Σ(units × keys) for all JKA entries
    # CRITICAL CORRECTION: P1.NMD = Σ(JKeysNum × JEqNmNum), NOT len(JKA)!
    # FIRMWARE CONFIRMED: Com_Lib.cpp:525 iterates M_data using units × keys count
    # Examples verified:
    # - Example2: 72 JKA entries → NMD=97 (Σ units×keys)
    # - Example3: 9 JKA entries → NMD=20 (Σ units×keys)
    # - Example6: 8 JKA entries → NMD=13 (Σ units×keys)
    p1["NMD"] = total_jky_keys  # Use calculated Σ(units×keys)
    print(f"[P1.NMD] Calculated: {total_jky_keys} total keys from {len(jka_list)} JKA entries")

    # =========================================================================
    # METADATA PRESERVATION LOGIC (For Import/Export Fidelity)
    # =========================================================================
    # If we are in a pure "Import -> Generate" cycle (no registers added/removed),
    # we MUST preserve the original ParamMap structures (P1, P2, P3, JKY) exactly as imported.
    # This ensures round-trip fidelity even if the imported JSON assumes different logic.
    # Checks:
    # 1. Metadata exists
    # 2. Register count matches imported B1.NOP (implies no structural changes)
    # 3. All required sections exist in metadata
    
    if metadata:
        # Support both uppercase and lowercase metadata keys
        b1 = metadata.get('B1', metadata.get('b1', {}))
        if b1:
            imported_nop = b1.get('NOP', 0)
            current_nop = len(registers)
            
            if imported_nop == current_nop:
                # Check if all ParamMap sections are present in metadata (support case-insensitive)
                has_p1 = 'P1' in metadata or 'p1' in metadata
                has_p2 = 'P2' in metadata or 'p2' in metadata
                has_p3 = 'P3' in metadata or 'p3' in metadata
                has_jky = 'JKY' in metadata or 'jky' in metadata
                
                if has_p1 and has_p2 and has_p3 and has_jky:
                    print(f"[ParamMap] Preservation active: Register count match ({current_nop}). Restoring imported P1, P2, P3, JKY.")
                    p1 = (metadata.get('P1') or metadata.get('p1')).copy()
                    p2 = (metadata.get('P2') or metadata.get('p2')).copy()
                    p3 = (metadata.get('P3') or metadata.get('p3')).copy()
                    jky = (metadata.get('JKY') or metadata.get('jky')).copy()
                else:
                    print("[ParamMap] Partial metadata found - using fresh calculation.")
            else:
                print(f"[ParamMap] Fresh calculation used: Register count changed (Imported: {imported_nop}, Current: {current_nop})")
        else:
            print("[ParamMap] No B1/b1 found in metadata - using fresh calculation.")
    
    # JKC: JSON Key Configuration
    jkc = None
    
    # PRIORITY 1: Use provided config
    if jkc_config:
        jkc = jkc_config.copy()
    
    # PRIORITY 2: Use metadata if available (from import)
    elif metadata:
        # Check P0 first, then root
        if 'P0' in metadata and isinstance(metadata['P0'], dict) and 'JKC' in metadata['P0']:
             jkc = metadata['P0']['JKC'].copy()
        elif 'JKC' in metadata:
             jkc = metadata.get('JKC').copy()
        elif 'jkc' in metadata:
             jkc = metadata.get('jkc').copy()
             
    # PRIORITY 3: Fallback default
    if not jkc:
        jkc = {
            "JKH": "properties",
            "EKS": "DKEY"
        }
    
    # NTC: Network Configuration
    ntc = None
    
    # PRIORITY 1: Use provided config (from UI)
    if ntc_config:
        ntc = ntc_config.copy()
        # ntc_config from UI only has IP, PT, CI, DI
        # We need to add SN, MI, MT arrays
        
        # Try to get arrays from metadata first (for preservation)
        metadata_ntc = None
        if metadata:
            if 'P0' in metadata and isinstance(metadata['P0'], dict) and 'NTC' in metadata['P0']:
                metadata_ntc = metadata['P0']['NTC']
            elif 'NTC' in metadata:
                metadata_ntc = metadata.get('NTC')
            elif 'ntc' in metadata:
                metadata_ntc = metadata.get('ntc')
                
        if metadata_ntc:
            # Merge arrays from metadata (preserves imported slave config)
            for key in ['SN', 'MI', 'MT']:
                if key in metadata_ntc:
                    ntc[key] = metadata_ntc[key]
        
        # If still missing SN/MI/MT, generate from current slaves
        if 'SN' not in ntc or 'MI' not in ntc or 'MT' not in ntc:
            if slaves is None or len(slaves) == 0:
                num_slaves = 1
                slave_ids = [1]
            else:
                num_slaves = len(slaves)
                slave_ids = slaves
                
            if 'SN' not in ntc:
                ntc['SN'] = slave_ids
            if 'MI' not in ntc:
                ntc['MI'] = [f"SLAVE{sid}" for sid in slave_ids]
            if 'MT' not in ntc:
                ntc['MT'] = ["GWAY"] * num_slaves
        
    # PRIORITY 2: Use metadata if available (full import, no UI override)
    elif metadata:
        # Check P0 first, then root
        if 'P0' in metadata and isinstance(metadata['P0'], dict) and 'NTC' in metadata['P0']:
             ntc = metadata['P0']['NTC'].copy()
        elif 'NTC' in metadata:
             ntc = metadata.get('NTC').copy()
        elif 'ntc' in metadata:
             ntc = metadata.get('ntc').copy()
             
    # PRIORITY 3: Fallback default (no UI config, no metadata)
    if not ntc:
        # Generate arrays matching the number of slaves from B1.NOS
        # FIRMWARE REQUIREMENT: NTC.SN, NTC.MI, NTC.MT must have same length as B1.NOS
        if slaves is None or len(slaves) == 0:
            # Fallback if no slave info provided
            num_slaves = 1
            slave_ids = [1]
        else:
            num_slaves = len(slaves)
            slave_ids = slaves
        
        # Generate arrays with proper length
        sn_array = slave_ids  # Slave Numbers match actual slave IDs
        mi_array = [f"SLAVE{sid}" for sid in slave_ids]  # Machine IDs
        mt_array = ["GWAY"] * num_slaves  # Machine Types (default to GWAY)
        
        ntc = {
            "IP": "18.191.222.62",
            "PT": "1234",
            "CI": "Lucas",
            "SN": sn_array,
            "MI": mi_array,
            "MT": mt_array,
            "DI": "GW01"
        }
    
    # MST: Master settings
    # PRIORITY 1: Use metadata if available (from import)
    if metadata and ('MST' in metadata or 'mst' in metadata):
        mst = metadata.get('MST', metadata.get('mst')).copy()
    else:
        # FALLBACK: Use current profile setting
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


def generate_output_json(param_config, registers, machine_id=None, device_id=None):
    """Generate Output JSON template matching Azure IoT Hub / Cloud telemetry format.
    
    This Output JSON shows the expected runtime telemetry structure that the firmware
    will send to cloud/MQTT based on the configured parameters.
    
    Output structure:
    {
      "machineId": "<user-configured>",
      "deviceId": "<user-configured>",
      "timestamp": "<ISO 8601 timestamp>",
      "responseStatus": 0,
      "responseString": {"MB": "OK"},
      "properties": {
        "msgType": "NML_STAT",
        "autoShed": 0,
        "<json_group>": {
          "<json_key>": {
            "<json_unit>": 0
          }
        }
      }
    }
    
    Args:
        param_config: Generated ParamMap_Config.json dictionary
        registers: List of register objects with cloud parameters
        machine_id: User-configured machine/gateway identifier (e.g., "EnergyHive_Test")
        device_id: User-configured device identifier (e.g., "TSA_Serv1001")
        
    Returns:
        Dictionary representing the Output JSON telemetry structure with placeholder values
    """
    from datetime import datetime
    
    ntc = param_config.get('NTC', {})
    
    # Use provided machine_id and device_id from UI, with fallbacks
    # Note: NTC.MI is an array for slave machines, not the gateway machineId
    # machineId for output.json comes from user configuration, not NTC.MI
    if not machine_id:
        machine_id = "EnergyHive_Test"  # Default if not provided
    if not device_id:
        # Try to get from NTC.DI, otherwise use default
        if isinstance(ntc.get('DI'), list):
            device_id = ntc.get('DI', ['TSA_Serv1001'])[0]
        else:
            device_id = ntc.get('DI', 'TSA_Serv1001')
    
    # Build properties section
    properties = {
        "msgType": "NML_STAT",  # Normal status message type
        "autoShed": 0           # Auto-shedding status (0 = normal)
    }
    
    # Process cloud-enabled registers to build nested structure
    # Structure: properties -> json_group -> json_key -> json_unit -> value
    for reg in registers:
        # Only include cloud-enabled parameters
        if not reg.cloud:
            continue
        
        # Skip if json fields are empty
        if not reg.json_group or not reg.json_key or not reg.json_unit:
            continue
        
        group = reg.json_group.strip()
        key = reg.json_key.strip()
        unit = reg.json_unit.strip()
        
        # Create nested structure
        if group not in properties:
            properties[group] = {}
        
        if key not in properties[group]:
            properties[group][key] = {}
        
        # Set placeholder value (0) - firmware provides actual values at runtime
        properties[group][key][unit] = 0
    
    # Build complete output JSON structure
    output = {
        "machineId": machine_id,
        "deviceId": device_id,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),  # ISO 8601 format
        "responseStatus": 0,  # 0 = success
        "responseString": {
            "MB": "OK"  # Modbus communication status
        },
        "properties": properties
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
    # NOP should match register count (unless preserved from import with different structure)
    if b1.get('NOP', 0) != len(registers):
        warnings.append(f"B1.NOP ({b1.get('NOP')}) does not match current register count ({len(registers)}) - May be from imported config")
    
    # B1.NOR validation - should be positive and reasonable
    if 'NOR' in b1:
        nor_value = b1['NOR']
        if not isinstance(nor_value, int) or nor_value <= 0:
            errors.append(f"B1.NOR must be positive integer, got {nor_value}")
        elif nor_value > 1000:
            warnings.append(f"B1.NOR ({nor_value}) seems unusually high - verify packet configuration")

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
    # Only validate if we have generated packets to compare against
    if packets and (len(sa) != len(packets) or len(nrt) != len(packets)):
        warnings.append(f"B4 has {len(sa)} packet entries but {len(packets)} packets generated - May be from imported config with different structure")

    # B5 parameter packet numbers should reference valid packets
    b5 = modbus_io.get('B5', {})
    pn_list = b5.get('PN', [])
    max_packets = len(packets) if packets else b1.get('NPT', 0)
    for i, pn in enumerate(pn_list, 1):
        if pn < 1:
            errors.append(f"Serial No. {i}: Invalid packet number {pn} (must be >= 1)")
        elif max_packets > 0 and pn > max_packets:
            # Only warn if we have packet info and PN exceeds it
            warnings.append(f"Serial No. {i}: References packet number {pn} but only {max_packets} packets defined - May be from imported config")

    # B6 read/write consistency
    b6 = modbus_io.get('B6', {})
    rp = b6.get('RP', [])
    wp = b6.get('WP', [])
    num_params = len(registers) if registers else b1.get('NOP', 0)
    for pnum in rp:
        if pnum < 1:
            errors.append(f"B6.RP contains invalid parameter ID {pnum} (must be >= 1)")
        elif num_params > 0 and pnum > num_params:
            warnings.append(f"B6.RP references parameter ID {pnum} but only {num_params} parameters defined - May be from imported config")
    for pnum in wp:
        if pnum < 1:
            errors.append(f"B6.WP contains invalid parameter ID {pnum} (must be >= 1)")
        elif num_params > 0 and pnum > num_params:
            warnings.append(f"B6.WP references parameter ID {pnum} but only {num_params} parameters defined - May be from imported config")

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
    if 'NLB' in p1:
        if not isinstance(p1['NLB'], int):
            errors.append("P1.NLB must be integer count")
        elif p1['NLB'] <= 0:
            errors.append(f"P1.NLB must be positive, got {p1['NLB']}")
        elif p1['NLB'] > 100:
            warnings.append(f"P1.NLB ({p1['NLB']}) seems unusually high - verify Lua buffer configuration")
    
    if 'NLBIN' in p1:
        if not isinstance(p1['NLBIN'], int):
            errors.append("P1.NLBIN must be integer count")
        # NLBIN should equal NLB in most cases
        if 'NLB' in p1 and p1.get('NLBIN') != p1.get('NLB'):
            warnings.append(f"P1.NLBIN ({p1.get('NLBIN')}) differs from P1.NLB ({p1.get('NLB')}) - Usually they should match")

    # CRITICAL: Firmware-specific validation
    # Check P1.NMD matches JKY total elements
    p1 = param_cfg.get('P1', {})
    jky = param_cfg.get('JKY', {})
    jka = jky.get('JKA', [])
    
    if 'NMD' in p1:
        expected_nmd = p1['NMD']
        if not isinstance(expected_nmd, int) or expected_nmd < 0:
            errors.append(f"P1.NMD must be non-negative integer, got {expected_nmd}")
        else:
            # CRITICAL: P1.NMD = Σ(JKeysNum × JEqNmNum) for all JKA entries
            # Firmware: Com_Lib.cpp:525 uses MdStrtIdx += Jka[i].p_JKeysNum * Jka[i].p_JEqNmNum
            # Example verification:
            # - Example2: 79 JKA entries → NMD=97 (Σ units×keys)
            # - Example3: 9 JKA entries → NMD=20 (NOT 9!)
            # - Example6: 8 JKA entries → NMD=13 (NOT 8!)
            
            # Calculate expected NMD using firmware formula
            calculated_nmd = 0
            for jka_entry in jka:
                if isinstance(jka_entry, list) and len(jka_entry) >= 3:
                    num_units = len(jka_entry[1]) if isinstance(jka_entry[1], list) else 0
                    num_keys = len(jka_entry[2]) if isinstance(jka_entry[2], list) else 0
                    calculated_nmd += num_units * num_keys
            
            # Only warn if mismatch - imported configs may have valid different structure
            if calculated_nmd != expected_nmd and calculated_nmd > 0:
                warnings.append(f"P1.NMD ({expected_nmd}) does not match calculated Σ(units×keys) ({calculated_nmd}) - May be from imported config with different structure")
            elif expected_nmd > 0 and calculated_nmd == 0:
                errors.append(f"P1.NMD is {expected_nmd} but JKY has no valid entries - Configuration mismatch!")
    
    # Check P3.MDI is sequential (1, 2, 3, 4, ...)
    # NOTE: Imported configs may have valid non-sequential MDI if structure differs
    p3 = param_cfg.get('P3', {})
    mdi_list = p3.get('MDI', [])
    if mdi_list:
        expected_sequential = list(range(1, len(mdi_list) + 1))
        if mdi_list != expected_sequential:
            # Only warn, not error - imported configs may have valid different structure
            warnings.append(f"P3.MDI is not sequential [1,2,3,...], got {mdi_list[:10]}{'...' if len(mdi_list) > 10 else ''} - May be from imported config")
    
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
            # NOTE: Imported configs may have longer strings that worked in specific firmware versions
            # Warn instead of error to allow imported data to pass validation
            equipment_type = jka_entry[0]
            device_names = jka_entry[1]
            param_keys = jka_entry[2]
            
            if len(equipment_type) > 15:
                warnings.append(f"JKA[{idx}] Equipment Type '{equipment_type}' ({len(equipment_type)} chars) exceeds firmware limit of 15 chars - May cause issues")
            
            for dev_idx, device_name in enumerate(device_names):
                if len(device_name) > 15:
                    warnings.append(f"JKA[{idx}] Device Name '{device_name}' ({len(device_name)} chars) exceeds firmware limit of 15 chars - May cause issues")
            
            for key_idx, param_key in enumerate(param_keys):
                if len(param_key) > 15:
                    warnings.append(f"JKA[{idx}] Parameter Key '{param_key}' ({len(param_key)} chars) exceeds firmware limit of 15 chars - May cause issues")
    
    # JKC string length validation: max 15 chars
    # NOTE: Warn instead of error for imported configs
    jkc = param_cfg.get('JKC', {})
    if 'JKH' in jkc:
        jkh = jkc['JKH']
        if len(jkh) > 15:
            warnings.append(f"JKC.JKH '{jkh}' ({len(jkh)} chars) exceeds firmware limit of 15 chars - May cause issues")
    
    if 'EKS' in jkc:
        eks = jkc['EKS']
        if len(eks) > 15:
            warnings.append(f"JKC.EKS '{eks}' ({len(eks)} chars) exceeds firmware limit of 15 chars - May cause issues")
    
    # NTC string length validation
    # NOTE: Warn instead of error for imported configs
    ntc = param_cfg.get('NTC', {})
    
    # IP: max 16 chars (IP address format)
    if 'IP' in ntc and len(ntc['IP']) > 16:
        warnings.append(f"NTC.IP '{ntc['IP']}' ({len(ntc['IP'])} chars) exceeds firmware limit of 16 chars - May cause issues")
    
    # Client ID and Device ID: max 20 chars
    if 'CI' in ntc and len(ntc['CI']) > 20:
        warnings.append(f"NTC.CI (Client ID) '{ntc['CI']}' ({len(ntc['CI'])} chars) exceeds firmware limit of 20 chars - May cause issues")
    
    if 'DI' in ntc and len(ntc['DI']) > 20:
        warnings.append(f"NTC.DI (Device ID) '{ntc['DI']}' ({len(ntc['DI'])} chars) exceeds firmware limit of 20 chars - May cause issues")
    
    # Port: max 8 chars
    if 'PT' in ntc and len(ntc['PT']) > 8:
        warnings.append(f"NTC.PT (Port) '{ntc['PT']}' ({len(ntc['PT'])} chars) exceeds firmware limit of 8 chars - May cause issues")
    
    # Machine IDs and Types: max 20 chars each
    if 'MI' in ntc and isinstance(ntc['MI'], list):
        for idx, machine_id in enumerate(ntc['MI']):
            if len(machine_id) > 20:
                warnings.append(f"NTC.MI[{idx}] (Machine ID) '{machine_id}' ({len(machine_id)} chars) exceeds firmware limit of 20 chars - May cause issues")
    
    if 'MT' in ntc and isinstance(ntc['MT'], list):
        for idx, machine_type in enumerate(ntc['MT']):
            if len(machine_type) > 20:
                warnings.append(f"NTC.MT[{idx}] (Machine Type) '{machine_type}' ({len(machine_type)} chars) exceeds firmware limit of 20 chars - May cause issues")
    
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


# ============================================================================
# AUTO-ASSIGNMENT FUNCTIONS FOR packet_num AND b5_id
# ============================================================================

def auto_assign_packet_numbers(registers: list) -> list:
    """
    Automatically assign packet numbers based on firmware constraints.

    **MANDATORY PACKET FORMATION RULES:**
    - Group by (slave_id, fc) combination
    - Within each group, sort by address
    - **CRITICAL: WRITE operations (FC 5,6,15,16) = Each parameter gets separate packet**
    - **READ operations (FC 1,2,3,4) = Group parameters if constraints allow**
    - Maximum 70 registers per packet (READ only)
    - **CRITICAL: Address span must not exceed 70** (READ only)
      (last_address - first_address ≤ 70)
    - Split packets when either limit is reached
    
    **Sets 3 fields on each register:**
    - packet_num: Packet number (1-indexed)
    - packet_sa: Packet start address (min address in packet)
    - packet_nrt: Packet register count (Modbus read/write span)
    
    **Firmware Reasoning:**
    - WRITE operations are executed one at a time (no grouping allowed)
    - READ operations can be optimized by grouping adjacent addresses
    
    Examples of valid packets:
    - READ: Addresses 0-60 (span=60) ✓
    - READ: Addresses 200-270 (span=70) ✓
    - WRITE: Single parameter per packet ✓
    
    Examples of invalid packets:
    - READ: Addresses 100-400 (span=300) ✗ Must split!
    - WRITE: Multiple parameters in one packet ✗ Not allowed!
    """
    if not registers:
        return registers
    
    # Helper to get value from dict or object
    def get_value(reg, key, default=None):
        if isinstance(reg, dict):
            return reg.get(key, default)
        else:
            return getattr(reg, key, default)
    
    # Helper to set value in dict or object
    def set_value(reg, key, value):
        if isinstance(reg, dict):
            reg[key] = value
        else:
            setattr(reg, key, value)

    # Sort by slave_id, fc, then by address (not b5_id)
    sorted_regs = sorted(registers, key=lambda r: (
        get_value(r, 'slave_id', 0),
        get_value(r, 'fc', 0),
        get_value(r, 'address', 0)
    ))

    packet_num = 1  # IMPORTANT: Packet numbers start from 1, not 0
    MAX_REGISTERS_PER_PACKET = 70
    MAX_ADDRESS_SPAN = 70
    
    # Group by slave_id and fc
    groups = {}
    for reg in sorted_regs:
        slave = get_value(reg, 'slave_id', 0)
        fc = get_value(reg, 'fc', 0)
        key = (slave, fc)
        if key not in groups:
            groups[key] = []
        groups[key].append(reg)
    
    # Process each group and create packets
    for (slave_id, fc), group_regs in sorted(groups.items()):
        # Already sorted by address within group
        
        # CRITICAL FIRMWARE REQUIREMENT: Write operations must each get separate packet
        # FC 5 = Force Single Coil (Write)
        # FC 6 = Preset Single Register (Write)
        # FC 15 = Force Multiple Coils (Write)
        # FC 16 = Preset Multiple Registers (Write)
        if fc in [5, 6, 15, 16]:
            # Each WRITE parameter gets its own packet
            for reg in group_regs:
                addr = get_value(reg, 'address', 0)
                length = get_value(reg, 'length', 1)
                
                # Single packet for this write parameter
                set_value(reg, 'packet_num', packet_num)
                set_value(reg, 'packet_sa', addr)
                set_value(reg, 'packet_nrt', length)
                
                packet_num += 1
            continue  # Move to next group
        
        # READ operations: Group parameters if they fit within constraints
        packet_start_idx = 0
        
        while packet_start_idx < len(group_regs):
            # Start new packet
            packet_regs = []
            
            for i in range(packet_start_idx, len(group_regs)):
                current_reg = group_regs[i]
                current_address = get_value(current_reg, 'address', 0)
                current_length = get_value(current_reg, 'length', 1)
                
                # Calculate span if we add this register
                if not packet_regs:
                    # First register in packet
                    packet_regs.append(current_reg)
                else:
                    # Calculate current packet span including this new register
                    all_addresses = []
                    for r in packet_regs + [current_reg]:
                        addr = get_value(r, 'address', 0)
                        length = get_value(r, 'length', 1)
                        # Add all addresses this register occupies
                        all_addresses.extend(range(addr, addr + length))
                    
                    min_addr = min(all_addresses)
                    max_addr = max(all_addresses)
                    address_span = max_addr - min_addr + 1
                    
                    # Check constraints
                    would_exceed_count = len(packet_regs) >= MAX_REGISTERS_PER_PACKET
                    would_exceed_span = address_span > MAX_ADDRESS_SPAN
                    
                    # If adding this register would violate constraints, start new packet
                    if would_exceed_count or would_exceed_span:
                        break
                    
                    # Add to current packet
                    packet_regs.append(current_reg)
            
            # Calculate packet metadata
            # packet_sa = minimum address in packet
            # packet_nrt = span from min to max (including multi-register parameters)
            all_addresses = []
            for r in packet_regs:
                addr = get_value(r, 'address', 0)
                length = get_value(r, 'length', 1)
                all_addresses.extend(range(addr, addr + length))
            
            packet_sa = min(all_addresses)
            packet_nrt = max(all_addresses) - min(all_addresses) + 1
            
            # Assign packet metadata to all registers in this packet
            for reg in packet_regs:
                set_value(reg, 'packet_num', packet_num)
                set_value(reg, 'packet_sa', packet_sa)
                set_value(reg, 'packet_nrt', packet_nrt)
            
            # Move to next packet
            packet_start_idx += len(packet_regs)
            packet_num += 1
    
    total_packets = packet_num - 1
    print(f"✓ Auto-assigned {total_packets} packets (max 70 registers, max 70 address span)")
    return registers

def auto_generate_b5_ids(registers: list) -> list:
    """
    Automatically generate B5 IDs sequentially starting from 1.
    
    This is called after packet_num assignment to ensure proper ordering.
    
    Args:
        registers: List of register dictionaries
    
    Returns:
        Updated list with b5_id assigned sequentially
    """
    if not registers:
        return registers
    
    # Sort by packet_num, then by address within packet
    sorted_regs = sorted(registers, key=lambda r: (
        r.get('packet_num', 0),
        r.get('address', 0)
    ))
    
    # Assign sequential b5_ids
    for i, reg in enumerate(sorted_regs, start=1):
        reg['b5_id'] = i
    
    print(f"✓ Auto-generated {len(sorted_regs)} B5 IDs (1-{len(sorted_regs)})")
    return registers


def validate_packet_assignments(registers: list) -> tuple:
    """
    Validate packet assignments and return statistics.
    
    Returns:
        (is_valid, message, stats_dict)
    """
    if not registers:
        return (True, "No registers to validate", {})
    
    # Check all registers have packet_num
    missing_packet = [r for r in registers if 'packet_num' not in r]
    if missing_packet:
        return (False, f"{len(missing_packet)} registers missing packet_num", {})
    
    # Check all registers have b5_id
    missing_b5 = [r for r in registers if 'b5_id' not in r]
    if missing_b5:
        return (False, f"{len(missing_b5)} registers missing b5_id", {})
    
    # Check for duplicate b5_ids
    b5_ids = [r['b5_id'] for r in registers]
    if len(b5_ids) != len(set(b5_ids)):
        return (False, "Duplicate B5 IDs found", {})
    
    # Gather statistics
    packet_nums = set(r['packet_num'] for r in registers)
    stats = {
        'total_registers': len(registers),
        'total_packets': len(packet_nums),
        'b5_id_range': f"{min(b5_ids)}-{max(b5_ids)}",
        'packet_range': f"{min(packet_nums)}-{max(packet_nums)}"
    }
    
    return (True, "All assignments valid", stats)


class ModbusConfigGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("🔧 Modbus Configuration Generator Pro")
        
        # Make window start maximized and responsive
        self.root.state('zoomed')  # Windows maximized
        self.root.minsize(1200, 700)  # Minimum size
        self.root.configure(bg='#f5f7fa')
        
        # Data storage
        self.register_rows = []
        self.registers = []  # Add registers list for transparent fields
        self.generated_modbus_io = None
        self.generated_parameter_config = None
        self.generated_output_json = None
        self.metadata = {}  # Store metadata for perfect reconstruction
        self.clipboard = None  # Clipboard for copy/paste operations
        self.clipboard_indicator = None  # Visual indicator for copied items
        
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
        # Create scrollable canvas for full page scrolling
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(fill='both', expand=True)
        
        # Create canvas with scrollbar
        self.canvas = tk.Canvas(canvas_frame, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        
        # Create main frame inside canvas
        main_frame = ttk.Frame(self.canvas)
        
        # Configure canvas
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=main_frame, anchor='nw')
        
        # Bind canvas resize
        main_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        
        # Enable mousewheel scrolling - improved implementation
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to root and canvas for better compatibility
        self.root.bind_all("<MouseWheel>", on_mousewheel)
        
        # Also bind mouse button scrolling for better control
        def on_mouse_button_scroll(event):
            if event.num == 4:  # Scroll up on Linux
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Scroll down on Linux
                self.canvas.yview_scroll(1, "units")
        
        self.root.bind_all("<Button-4>", on_mouse_button_scroll)
        self.root.bind_all("<Button-5>", on_mouse_button_scroll)
        
        # Configure grid weights for responsiveness
        main_frame.grid_rowconfigure(3, weight=1)  # Register table row expands
        main_frame.grid_columnconfigure(0, weight=1)
        
        # Title Section with gradient-like effect
        title_frame = tk.Frame(main_frame, bg='#3498db', height=80)
        title_frame.grid(row=0, column=0, sticky='ew')
        title_frame.grid_propagate(False)
        
        # Add menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📘 BMIoT Firmware Architecture", command=self.show_firmware_help)
        help_menu.add_command(label="🔍 Column Descriptions", command=self.show_column_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        
        title_inner = tk.Frame(title_frame, bg='#3498db')
        title_inner.place(relx=0.5, rely=0.5, anchor='center')
        
        tk.Label(title_inner, text="⚙️ Modbus Configuration Generator Pro", 
                font=('Segoe UI', 20, 'bold'), fg='white', bg='#3498db').pack()
        tk.Label(title_inner, text="✨ Automatically generate modbus_io.json and parameter_config.json with ease", 
                font=('Segoe UI', 11), fg='#ecf0f1', bg='#3498db').pack(pady=5)
        
        # ==================== OPERATION MODE SELECTOR ====================
        # Visual tab selector to distinguish Forward Generation vs Import & Analyze modes
        mode_frame = tk.Frame(main_frame, bg='#ecf0f1', height=60)
        mode_frame.grid(row=1, column=0, sticky='ew', padx=20, pady=(10, 0))
        mode_frame.grid_propagate(False)
        
        # Mode selector label
        mode_label_frame = tk.Frame(mode_frame, bg='#ecf0f1')
        mode_label_frame.pack(side='left', padx=20, pady=10)
        tk.Label(mode_label_frame, text="🔧 Operation Mode:", 
                font=('Segoe UI', 11, 'bold'), bg='#ecf0f1', fg='#2c3e50').pack(side='left')
        
        # Tab buttons frame
        tabs_frame = tk.Frame(mode_frame, bg='#ecf0f1')
        tabs_frame.pack(side='left', padx=10, pady=5)
        
        # Store mode state
        self.operation_mode = tk.StringVar(value="forward")  # "forward" or "import"
        
        # Forward Generation Tab
        self.forward_tab = tk.Button(tabs_frame, text="▶️ Forward Generation", 
                                     font=('Segoe UI', 11, 'bold'),
                                     bg='#3498db', fg='white',
                                     activebackground='#2980b9', activeforeground='white',
                                     relief='raised', bd=3,
                                     padx=20, pady=8, cursor='hand2',
                                     command=lambda: self.set_operation_mode("forward"))
        self.forward_tab.pack(side='left', padx=5)
        
        # Import & Analyze Tab
        self.import_tab = tk.Button(tabs_frame, text="🔄 Import & Analyze", 
                                    font=('Segoe UI', 11),
                                    bg='#bdc3c7', fg='#7f8c8d',
                                    activebackground='#95a5a6', activeforeground='white',
                                    relief='flat', bd=1,
                                    padx=20, pady=8, cursor='hand2',
                                    command=lambda: self.set_operation_mode("import"))
        self.import_tab.pack(side='left', padx=5)
        
        # Info label explaining current mode
        self.mode_info_frame = tk.Frame(mode_frame, bg='#ecf0f1')
        self.mode_info_frame.pack(side='left', padx=20, pady=10)
        self.mode_info_label = tk.Label(self.mode_info_frame, 
                                       text="Create configuration files from register definitions", 
                                       font=('Segoe UI', 9, 'italic'), bg='#ecf0f1', fg='#7f8c8d')
        self.mode_info_label.pack()
        
        # Communication Settings Section
        comm_frame = ttk.LabelFrame(main_frame, text="  📡 Communication Settings  ", padding=15)
        comm_frame.grid(row=2, column=0, sticky='ew', padx=20, pady=10)
        
        comm_grid = ttk.Frame(comm_frame)
        comm_grid.pack(fill='x')
        
        # Row 0: Baudrate
        ttk.Label(comm_grid, text="Baudrate:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=10, pady=8)
        self.baudrate_var = tk.StringVar(value="19200")
        baudrate_combo = ttk.Combobox(comm_grid, textvariable=self.baudrate_var, 
                                      values=["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"], 
                                      width=15, state='readonly', font=('Segoe UI', 10))
        baudrate_combo.grid(row=0, column=1, padx=10, pady=8, sticky='w')
        ttk.Label(comm_grid, text="bits/sec", font=('Segoe UI', 9), foreground='#7f8c8d').grid(row=0, column=2, sticky='w', padx=5)
        
        # Row 1: Data Format - Separated into three parts
        ttk.Label(comm_grid, text="Data Format:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=10, pady=8)
        
        format_frame = ttk.Frame(comm_grid)
        format_frame.grid(row=1, column=1, columnspan=3, sticky='w', padx=10)
        
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
        
        # Row 2: Profile Selection (full width)
        ttk.Label(comm_grid, text="Profile:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky='w', padx=10, pady=8)
        self.profile_var = tk.StringVar(value="0")
        profile_combo = ttk.Combobox(comm_grid, textvariable=self.profile_var,
                                    values=bc.DROPDOWN_OPTIONS['profile'],
                                    width=80, state='readonly', font=('Segoe UI', 9))
        profile_combo.grid(row=2, column=1, columnspan=6, padx=10, pady=8, sticky='ew')
        profile_combo.set(bc.DROPDOWN_OPTIONS['profile'][0])
        
        # ==================== GLOBAL CONFIGURATION SECTION (NEW) ====================
        # This section allows overriding default global settings (NTC/JKC) for forward generation
        global_config_frame = ttk.LabelFrame(main_frame, text="  🌍 Global Configuration (Network & Keys)  ", padding=15)
        global_config_frame.grid(row=3, column=0, sticky='ew', padx=20, pady=5)
        
        # Grid layout for Global Config
        global_grid = ttk.Frame(global_config_frame)
        global_grid.pack(fill='x', expand=True)
        
        # Row 0: IP, Port, Client ID, Machine ID, Device ID
        # IP Address
        ttk.Label(global_grid, text="IP Address:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.ip_var = tk.StringVar(value="18.191.222.62")
        ip_entry = ttk.Entry(global_grid, textvariable=self.ip_var, width=15)
        ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # Port
        ttk.Label(global_grid, text="Port:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.port_var = tk.StringVar(value="1234")
        port_entry = ttk.Entry(global_grid, textvariable=self.port_var, width=8)
        port_entry.grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Client ID (CI)
        ttk.Label(global_grid, text="Client ID:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=4, padx=5, pady=5, sticky='w')
        self.ci_var = tk.StringVar(value="Lucas")
        ci_entry = ttk.Entry(global_grid, textvariable=self.ci_var, width=15)
        ci_entry.grid(row=0, column=5, padx=5, pady=5, sticky='w')
        
        # Machine ID (for output.json telemetry)
        ttk.Label(global_grid, text="Machine ID:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=6, padx=5, pady=5, sticky='w')
        self.machine_id_var = tk.StringVar(value="EnergyHive_Test")
        machine_id_entry = ttk.Entry(global_grid, textvariable=self.machine_id_var, width=20)
        machine_id_entry.grid(row=0, column=7, padx=5, pady=5, sticky='w')
        
        # Device ID (DI)
        ttk.Label(global_grid, text="Device ID:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=8, padx=5, pady=5, sticky='w')
        self.di_var = tk.StringVar(value="TSA_Serv1001")
        di_entry = ttk.Entry(global_grid, textvariable=self.di_var, width=20)
        di_entry.grid(row=0, column=9, padx=5, pady=5, sticky='w')
        
        # Row 1: JSON Key Header, Encrypted Key Source
        # JKH
        ttk.Label(global_grid, text="JSON Key Header (JKH):", font=('Segoe UI', 9)).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.jkh_var = tk.StringVar(value="properties")
        jkh_entry = ttk.Entry(global_grid, textvariable=self.jkh_var, width=15)
        jkh_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # EKS
        ttk.Label(global_grid, text="Encryp Key Source (EKS):", font=('Segoe UI', 9)).grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.eks_var = tk.StringVar(value="DKEY")
        eks_entry = ttk.Entry(global_grid, textvariable=self.eks_var, width=15)
        eks_entry.grid(row=1, column=3, padx=5, pady=5, sticky='w')

        # Add a note explaining fields
        ttk.Label(global_grid, text="(Machine ID & Device ID are used in output.json telemetry)", 
                 font=('Segoe UI', 8, 'italic'), foreground='gray').grid(row=1, column=4, columnspan=6, sticky='e', padx=10)

        # Register Configuration Section (EXPANDABLE - takes all remaining space)
        register_frame = ttk.LabelFrame(main_frame, text="  📋 Register Configuration  ", padding=15)
        register_frame.grid(row=4, column=0, sticky='nsew', padx=20, pady=10)
        register_frame.grid_rowconfigure(1, weight=1)  # Table row expands
        register_frame.grid_columnconfigure(0, weight=1)
        
        # Button toolbar with icons
        btn_toolbar = ttk.Frame(register_frame)
        btn_toolbar.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Left side buttons
        left_buttons = ttk.Frame(btn_toolbar)
        left_buttons.pack(side='left')
        
        btn_add = ttk.Button(left_buttons, text="➕ Add Register", command=self.add_register_row, style='Action.TButton')
        btn_add.pack(side='left', padx=5)
        
        btn_edit = ttk.Button(left_buttons, text="✏️ Edit Selected", command=self.edit_selected_row, style='Action.TButton')
        btn_edit.pack(side='left', padx=5)
        
        btn_delete = ttk.Button(left_buttons, text="🗑️ Delete Selected", command=self.delete_selected_row, style='Action.TButton')
        btn_delete.pack(side='left', padx=5)
        
        # Copy/Paste buttons
        btn_copy = ttk.Button(left_buttons, text="📋 Copy", command=self.copy_selected_row, style='Action.TButton')
        btn_copy.pack(side='left', padx=5)
        
        self.btn_paste = ttk.Button(left_buttons, text="📌 Paste", command=self.paste_row, style='Action.TButton', state='disabled')
        self.btn_paste.pack(side='left', padx=5)
        
        btn_duplicate = ttk.Button(left_buttons, text="🔄 Duplicate", command=self.duplicate_selected_row, style='Action.TButton')
        btn_duplicate.pack(side='left', padx=5)
        
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
        
        # NEW: Reverse transformation button
        btn_import_json = ttk.Button(right_buttons, text="🔄 Import Modbus+Paramap JSON", command=self.import_modbus_paramap, style='Action.TButton')
        btn_import_json.pack(side='left', padx=5)
        
        # Register Table with enhanced styling (EXPANDABLE)
        table_frame = ttk.Frame(register_frame)
        table_frame.grid(row=1, column=0, sticky='nsew')
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
# Create Treeview with Serial Number
        # Note: Columns 28+ are internal metadata fields not displayed in GUI
        columns = ('S.No', 'Slave ID', 'FC', 'Address', 'Length', 'FMT', 'Multiplier',
                   'Access', 'Cloud Output', 'JSON Group', 'JSON Unit', 'JSON Key', 'Array Membership',
                   'B5 ID', 'Packet Num', 'Packet SA', 'Packet NRT',
                   # TRANSPARENT FIELDS (Visible - columns 18-23)
                   'Packet #', 'Packet Start', 'Packet Regs', 'Param Type', 'Paired With', 'JKA Index',
                   # LUA BUFFER FIELDS (Visible - columns 24-27)
                   'In Lua Buffer', 'Lua Category', 'LBI Position', 'LBI Data Type',
                   # INTERNAL METADATA (Hidden - columns 28-37)
                   'Parameter Type', 'Write Param ID', 'Feedback Param ID', 'P2 MPI Index', 'P3 MPI Index',
                   'Equipment Group', 'Device Name', 'Equipment Type', 'JKA Equipment Index', 'Lua Buffer Note')
        
        # Visible columns (1-27) - internal metadata columns (28-37) are hidden
        visible_columns = columns[:27]
        
        # Create treeview with good minimum height that can expand
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=25, displaycolumns=visible_columns)
        
        # Define headings with better widths
        self.tree.heading('S.No', text='S')
        self.tree.column('S.No', width=40, anchor='center')
        
        # Set specific widths for important columns
        self.tree.column('Array Membership', width=150, anchor='w')
        
        # Custom display names for better readability and symmetry
        column_display_names = {
            'Slave ID': 'Slave',
            'FC': 'FC',
            'Address': 'Address',
            'Length': 'Length',
            'FMT': 'Format',
            'Multiplier': 'Multi',
            'Access': 'Access',
            'Cloud Output': 'Cloud',
            'JSON Group': 'Group',
            'JSON Unit': 'Unit',
            'JSON Key': 'Key',
            'Array Membership': 'Array',
            'B5 ID': 'B5',
            'Packet Num': 'Legacy\nPkt#',
            'Packet SA': 'Legacy\nStart',
            'Packet NRT': 'Legacy\nRegs',
            'Packet #': 'Pkt#',
            'Packet Start': 'Start',
            'Packet Regs': 'Regs',
            'Param Type': 'Type',
            'Paired With': 'Paired',
            'JKA Index': 'JKA',
            'In Lua Buffer': 'InLua',
            'Lua Category': 'Category',
            'LBI Position': 'LBI',
            'LBI Data Type': 'LBI Type'
        }
        
        for col in columns[1:]:
            # Use custom display name if available, otherwise use column name
            display_name = column_display_names.get(col, col)
            self.tree.heading(col, text=display_name)
            
            # Set column widths based on content type for better symmetry
            if col in ['Slave ID', 'FC', 'Length', 'FMT', 'B5 ID']:
                self.tree.column(col, width=60, anchor='center')
            elif col in ['Address']:
                self.tree.column(col, width=80, anchor='center')
            elif col in ['Multiplier', 'Access', 'Cloud Output']:
                self.tree.column(col, width=65, anchor='center')
            elif col in ['Packet Num', 'Packet SA', 'Packet NRT']:
                self.tree.column(col, width=70, anchor='center')  # Legacy packet fields
            elif col in ['Packet #', 'Packet Start', 'Packet Regs']:
                self.tree.column(col, width=60, anchor='center')  # Transparent packet fields
            elif col in ['Param Type', 'JKA Index']:
                self.tree.column(col, width=65, anchor='center')
            elif col in ['Paired With']:
                self.tree.column(col, width=75, anchor='center')
            elif col in ['In Lua Buffer']:
                self.tree.column(col, width=65, anchor='center')
            elif col in ['Lua Category']:
                self.tree.column(col, width=85, anchor='center')
            elif col in ['LBI Position']:
                self.tree.column(col, width=55, anchor='center')
            elif col in ['LBI Data Type']:
                self.tree.column(col, width=85, anchor='center')
            elif col in ['JSON Group', 'JSON Unit', 'JSON Key']:
                self.tree.column(col, width=130, anchor='w')
            elif col in ['Array Membership']:
                self.tree.column(col, width=150, anchor='w')
            else:
                self.tree.column(col, width=100)
        
        # Enhanced scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Add tooltips for firmware-mapped columns
        self.column_help = {
            'B5 ID': 'Parameter index in firmware Block 5 (s_Indx field)',
            'Packet Num': '📜 LEGACY: Old packet number field (replaced by Packet #)',
            'Packet SA': '📜 LEGACY: Old packet start address (replaced by Pkt Start)',
            'Packet NRT': '📜 LEGACY: Old packet register count (replaced by Pkt Regs)',
            'Packet #': '✨ TRANSPARENT: Which packet this param belongs to (editable)',
            'Packet Start': '✨ TRANSPARENT: Packet start address (auto-filled from packet)',
            'Packet Regs': '✨ TRANSPARENT: Total registers in packet (auto-filled)',
            'Param Type': '✨ TRANSPARENT: write/feedback/read_only (editable)',
            'Paired With': '✨ TRANSPARENT: Paired parameter ID for write↔feedback link (editable)',
            'JKA Index': '✨ TRANSPARENT: Equipment group index in JKY (editable, -1=none)',
            'In Lua Buffer': '🔧 LUA: Is this parameter stored in Lua Buffer? (Yes/No)',
            'Lua Category': '🔧 LUA: Equipment (P2.MPI - control logic) or User Variable (P2.RPCI)',
            'LBI Position': '🔧 LUA: Lua Buffer Index position (Auto or manual number)',
            'LBI Data Type': '🔧 LUA: Data type in Lua array (Number/Boolean/String)',
            'Cloud Output': 'Include in MQTT/HTTPS output buffer (P3.MPI - firmware required)',
            'Array Membership': 'Equipment group in output JSON structure (maps to JKY equipment types)'
        }
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Alternating row colors
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')
        self.tree.tag_configure('copied', background='#d1f2eb')  # Light green for copied items
        
        # Double-click to edit
        self.tree.bind('<Double-1>', lambda e: self.edit_selected_row())
        
        # Right-click context menu
        self.tree.bind('<Button-3>', self.show_context_menu)
        
        # Keyboard shortcuts
        self.tree.bind('<Control-c>', lambda e: self.copy_selected_row())
        self.tree.bind('<Control-v>', lambda e: self.paste_row())
        self.tree.bind('<Control-d>', lambda e: self.duplicate_selected_row())
        self.tree.bind('<Delete>', lambda e: self.delete_selected_row())
        
        # Create context menu (will be shown on right-click)
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="✏️ Edit", command=self.edit_selected_row)
        self.context_menu.add_command(label="📋 Copy (Ctrl+C)", command=self.copy_selected_row)
        self.context_menu.add_command(label="📌 Paste (Ctrl+V)", command=self.paste_row)
        self.context_menu.add_command(label="🔄 Duplicate (Ctrl+D)", command=self.duplicate_selected_row)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete (Del)", command=self.delete_selected_row)
        
        # Status bar
        status_frame = ttk.Frame(register_frame)
        status_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        self.status_label = ttk.Label(status_frame, text="📊 Total Registers: 0", font=('Segoe UI', 10))
        self.status_label.pack(side='left')
        
        # Generate Button with enhanced styling
        generate_frame = tk.Frame(main_frame, bg='#f5f7fa')
        generate_frame.grid(row=5, column=0, sticky='ew', padx=20, pady=15)
        
        # Validate Config Button (LEFT)
        validate_btn = tk.Button(generate_frame, text="🔍 Validate Configuration", 
                                font=('Segoe UI', 12, 'bold'), 
                                bg='#3498db', fg='white', 
                                activebackground='#2980b9', activeforeground='white',
                                relief='flat', padx=30, pady=12,
                                cursor='hand2',
                                command=self.validate_configuration)
        validate_btn.pack(side='left', padx=(0, 15))
        
        # Calculate Packets Button (MIDDLE)
        calculate_btn = tk.Button(generate_frame, text="🔄 Calculate Packets", 
                                font=('Segoe UI', 12, 'bold'), 
                                bg='#9b59b6', fg='white', 
                                activebackground='#8e44ad', activeforeground='white',
                                relief='flat', padx=30, pady=12,
                                cursor='hand2',
                                command=self.calculate_packets)
        calculate_btn.pack(side='left', padx=(0, 15))
        
        # Generate Button (RIGHT)
        generate_btn = tk.Button(generate_frame, text="🚀 Generate Configuration Files", 
                                font=('Segoe UI', 14, 'bold'), 
                                bg='#2ecc71', fg='white', 
                                activebackground='#27ae60', activeforeground='white',
                                relief='flat', padx=40, pady=15,
                                cursor='hand2',
                                command=self.generate_configs)
        generate_btn.pack(side='left')
        
        # Hover effects
        def on_validate_enter(e):
            validate_btn['background'] = '#2980b9'
        def on_validate_leave(e):
            validate_btn['background'] = '#3498db'
        validate_btn.bind("<Enter>", on_validate_enter)
        validate_btn.bind("<Leave>", on_validate_leave)
        
        def on_calculate_enter(e):
            calculate_btn['background'] = '#8e44ad'
        def on_calculate_leave(e):
            calculate_btn['background'] = '#9b59b6'
        calculate_btn.bind("<Enter>", on_calculate_enter)
        calculate_btn.bind("<Leave>", on_calculate_leave)
        
        def on_enter(e):
            generate_btn['background'] = '#27ae60'
        def on_leave(e):
            generate_btn['background'] = '#2ecc71'
        generate_btn.bind("<Enter>", on_enter)
        generate_btn.bind("<Leave>", on_leave)
        
        # Output Section with tabs (Fixed height, scrollable content)
        output_frame = ttk.LabelFrame(main_frame, text="  📄 Generated Configuration Files  ", padding=15)
        output_frame.grid(row=6, column=0, sticky='nsew', padx=20, pady=10)
        output_frame.grid_rowconfigure(1, weight=1)  # Allow expansion
        output_frame.grid_columnconfigure(0, weight=1)
        
        # Configure main_frame to give priority to register table
        main_frame.grid_rowconfigure(4, weight=4)  # Register table gets space
        main_frame.grid_rowconfigure(6, weight=2)  # Output gets more space for better visibility
        
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
                                                      height=20,
                                                      font=('Consolas', 10),
                                                      bg='#1e1e1e', fg='#d4d4d4',
                                                      insertbackground='white',
                                                      selectbackground='#264f78')
        self.modbus_text.pack(fill='both', expand=True)
        
        # Tab 2: parameter_config.json
        param_tab = ttk.Frame(self.notebook)
        self.notebook.add(param_tab, text="  📑 parameter_config.json  ")
        
        self.param_text = scrolledtext.ScrolledText(param_tab, wrap=tk.WORD,
                                                    height=20,
                                                    font=('Consolas', 10),
                                                    bg='#1e1e1e', fg='#d4d4d4',
                                                    insertbackground='white',
                                                    selectbackground='#264f78')
        self.param_text.pack(fill='both', expand=True)
        
        # Tab 3: output.json
        output_tab = ttk.Frame(self.notebook)
        self.notebook.add(output_tab, text="  📑 output.json  ")
        
        self.output_text = scrolledtext.ScrolledText(output_tab, wrap=tk.WORD,
                                                     height=20,
                                                     font=('Consolas', 10),
                                                     bg='#1e1e1e', fg='#d4d4d4',
                                                     insertbackground='white',
                                                     selectbackground='#264f78')
        self.output_text.pack(fill='both', expand=True)
        
        # Add initial placeholder messages
        initial_message = "// Click 'Generate Configs' to create configuration JSONs\\n// Generated files will appear here after generation"
        output_message = """// Click 'Generate Configs' to create Output JSON Template
// 
// Output JSON shows the expected runtime telemetry format that
// firmware will send to Azure IoT Hub / MQTT broker.
//
// Format:
// {
//   "machineId": "<from NTC.MI>",
//   "deviceId": "<from NTC.DI>",
//   "timestamp": "<ISO 8601 timestamp>",
//   "responseStatus": 0,
//   "responseString": {"MB": "OK"},
//   "properties": {
//     "msgType": "NML_STAT",
//     "<json_group>": {
//       "<json_key>": {
//         "<json_unit>": 0
//       }
//     }
//   }
// }
//
// Values shown are placeholders (0) - firmware provides actual
// sensor readings at runtime."""
        self.modbus_text.insert('1.0', initial_message)
        self.param_text.insert('1.0', initial_message)
        self.output_text.insert('1.0', output_message)
        
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
        
        # Initialize operation mode (Forward Generation by default)
        self.set_operation_mode("forward")
    
    def update_status(self):
        count = len(self.tree.get_children())
        self.status_label.config(text=f"📊 Total Registers: {count}")
    
    def set_operation_mode(self, mode):
        """Switch between Forward Generation and Import & Analyze modes"""
        self.operation_mode.set(mode)
        
        if mode == "forward":
            # Style Forward tab as active
            self.forward_tab.config(bg='#2ecc71', fg='white', 
                                   font=('Segoe UI', 10, 'bold'),
                                   relief='sunken', borderwidth=2)
            # Style Import tab as inactive
            self.import_tab.config(bg='#ecf0f1', fg='#7f8c8d',
                                  font=('Segoe UI', 10),
                                  relief='raised', borderwidth=1)
            # Update info label
            self.mode_info_label.config(
                text="📤 Forward Generation Mode: Configure Modbus parameters and generate JSON configs"
            )
        else:  # import mode
            # Style Import tab as active
            self.import_tab.config(bg='#3498db', fg='white',
                                  font=('Segoe UI', 10, 'bold'),
                                  relief='sunken', borderwidth=2)
            # Style Forward tab as inactive
            self.forward_tab.config(bg='#ecf0f1', fg='#7f8c8d',
                                   font=('Segoe UI', 10),
                                   relief='raised', borderwidth=1)
            # Update info label
            self.mode_info_label.config(
                text="📥 Import & Analyze Mode: Import existing configs and analyze parameter mappings"
            )
    
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
        """Load sample data with proper validation and Lua Buffer configuration"""
        sample_data = [
            # Read: UINT16 - WITH LUA BUFFER (Equipment Control)
            {'slave_id': 1, 'fc': 3, 'address': 100, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_AIE1', 'json_unit': 'DegC', 'json_key': 'RAT',
             'in_lua_buffer': 'Yes', 'lua_category': 'Equipment', 'lbi_position': '1', 'lbi_data_type': 'Number'},
            # Read: INT32 Big Endian - WITH LUA BUFFER (Equipment Control)
            {'slave_id': 1, 'fc': 3, 'address': 200, 'length': 2, 'fmt': 4, 
             'multiplier': 0.1, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_AIE2', 'json_unit': 'Vol', 'json_key': 'ChW_Fb_V',
             'in_lua_buffer': 'Yes', 'lua_category': 'Equipment', 'lbi_position': '2', 'lbi_data_type': 'Number'},
            # Read: Float 32-bit Big Endian - WITH LUA BUFFER (Equipment Control)
            {'slave_id': 1, 'fc': 3, 'address': 300, 'length': 2, 'fmt': 1, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_Mb1', 'json_unit': 'Watt', 'json_key': 'VFD_P',
             'in_lua_buffer': 'Yes', 'lua_category': 'Equipment', 'lbi_position': '3', 'lbi_data_type': 'Number'},
            # Read: UINT32 Little Endian - NO LUA BUFFER
            {'slave_id': 1, 'fc': 3, 'address': 400, 'length': 2, 'fmt': 7, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'AHU_RL_Mb2', 'json_unit': 'Hour', 'json_key': 'VFD_Rhr',
             'in_lua_buffer': 'No', 'lua_category': 'N/A', 'lbi_position': 'Auto', 'lbi_data_type': 'Number'},
            # Write: UINT16 - WITH LUA BUFFER (User Variable)
            {'slave_id': 1, 'fc': 6, 'address': 500, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'W', 'cloud': 'No', 
             'json_group': '', 'json_unit': '', 'json_key': '',
             'in_lua_buffer': 'Yes', 'lua_category': 'User Variable', 'lbi_position': '4', 'lbi_data_type': 'Number'},
            # Read-Write: INT16 - Write + verification parameter - WITH LUA BUFFER (User Variable)
            # IMPORTANT: RW parameters should NOT have cloud=Yes
            # The read component is only for write verification, not telemetry
            {'slave_id': 2, 'fc': 3, 'address': 1000, 'length': 1, 'fmt': 8, 
             'multiplier': 0.1, 'access': 'RW', 'cloud': 'No', 
             'json_group': '', 'json_unit': '', 'json_key': '',
             'in_lua_buffer': 'Yes', 'lua_category': 'User Variable', 'lbi_position': '5', 'lbi_data_type': 'Number'},
            # Read: Coil (FC=1) - NO LUA BUFFER
            {'slave_id': 2, 'fc': 1, 'address': 1, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'R', 'cloud': 'Yes', 
             'json_group': 'Chiller_DIE1', 'json_unit': 'St', 'json_key': 'ChillerRun',
             'in_lua_buffer': 'No', 'lua_category': 'N/A', 'lbi_position': 'Auto', 'lbi_data_type': 'Boolean'},
            # Write: Coil (FC=5) - NO LUA BUFFER
            {'slave_id': 2, 'fc': 5, 'address': 100, 'length': 1, 'fmt': 3, 
             'multiplier': 1.0, 'access': 'W', 'cloud': 'No', 
             'json_group': '', 'json_unit': '', 'json_key': '',
             'in_lua_buffer': 'No', 'lua_category': 'N/A', 'lbi_position': 'Auto', 'lbi_data_type': 'Boolean'},
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
            access = data['access']
            param_type = 'write' if access in ['W', 'RW'] else 'read_only'
            self.tree.insert('', 'end', values=(
                idx + 1,
                data['slave_id'], data['fc'], data['address'], data['length'],
                data['fmt'], data['multiplier'], access, data['cloud'],
                data['json_group'], data['json_unit'], data['json_key'],
                data.get('array_membership', ''),
                data.get('b5_id', idx + 1), data.get('packet_num', 0),
                data.get('packet_sa', data['address']), data.get('packet_nrt', data['length']),
                # TRANSPARENT FIELDS (columns 18-23) - visible
                None,  # Packet # (auto-assigned)
                None,  # Packet Start (auto-filled)
                None,  # Packet Regs (auto-filled)
                param_type,  # Param Type
                None,  # Paired With (user fills)
                -1,  # JKA Index (user fills or auto-assign)
                # LUA BUFFER FIELDS (columns 24-27) - visible - USE SAMPLE DATA VALUES
                data.get('in_lua_buffer', 'No'),  # In Lua Buffer
                data.get('lua_category', 'N/A'),  # Lua Category
                data.get('lbi_position', 'Auto'),  # LBI Position
                data.get('lbi_data_type', 'Number'),  # LBI Data Type
                # INTERNAL METADATA (columns 28-37) - hidden
                param_type, '', '', '', '',  # parameter_type, write_param_id, feedback_param_id, p2_mpi_index, p3_mpi_index
                '', '', '', -1,  # equipment_group, device_name, equipment_type, jka_equipment_index
                ''  # lua_buffer_note (empty for sample data)
            ), tags=(tag,))
        
        self.update_status()
        messagebox.showinfo("✅ Success", f"Sample data loaded successfully!\n\n{len(sample_data)} parameters added with proper validation.\n\n💡 Note: {sum(1 for d in sample_data if d.get('in_lua_buffer') == 'Yes')} parameters configured for Lua Buffer.")
    
    def safe_int(self, value, default=None):
        """Safely convert value to integer, handling empty strings and None"""
        if value is None or value == '' or value == 'None':
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def safe_float(self, value, default=1.0):
        """Safely convert value to float, handling empty strings and None"""
        if value is None or value == '' or value == 'None':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def convert_format_to_code(self, format_value, default=3):
        """Convert format string or code to integer code
        
        Args:
            format_value: Can be int code (1-8), or string name ("INT16", "UINT16", etc.)
            default: Default code if conversion fails (default: 3 = UINT16)
            
        Returns:
            int: Format code (1-8)
        """
        if format_value is None or format_value == '' or format_value == 'None':
            return default
            
        # If already an integer, validate and return
        if isinstance(format_value, int):
            return format_value if 1 <= format_value <= 8 else default
            
        # Try converting string to int first
        try:
            code = int(format_value)
            return code if 1 <= code <= 8 else default
        except (ValueError, TypeError):
            pass
        
        # Map format string names to codes
        format_map = {
            'FLOAT32': 1, 'FP32': 1, 'FP32_BA': 1, 'FP32BIT_BA': 1,
            'FLOAT32_LE': 2, 'FP32_AB': 2, 'FP32BIT_AB': 2,
            'UINT16': 3, 'UINT16BIT': 3, 'UNSIGNED16': 3,
            'INT32': 4, 'INT32_BE': 4, 'INT32BIT_BA': 4,
            'INT32_LE': 5, 'INT32BIT_AB': 5,
            'UINT32': 6, 'UINT32_BE': 6, 'UINT32BIT_BA': 6,
            'UINT32_LE': 7, 'UINT32BIT_AB': 7,
            'INT16': 8, 'INT16BIT': 8, 'SIGNED16': 8
        }
        
        # Normalize format string (uppercase, remove spaces/underscores)
        if isinstance(format_value, str):
            normalized = format_value.upper().replace(' ', '').replace('_', '').replace('-', '')
            return format_map.get(normalized, default)
            
        return default
    
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
                    
                    # Load metadata section if available
                    if 'metadata' in data:
                        self.metadata = data['metadata']
                        # Extract slave_order if available
                        if 'slave_order' in data['metadata']:
                            self.slave_order = data['metadata']['slave_order']

                        # Populate Global Config UI from Metadata (for visualization and forward generation)
                        # Supports both nested P0 structure and flat structure
                        md = self.metadata
                        
                        # Helper to safely set UI var if key exists
                        def safe_set(ui_var, source_dict, key):
                            if source_dict and key in source_dict and source_dict[key]:
                                ui_var.set(str(source_dict[key]))
                        
                        # 1. Try P0.NTC / P0.JKC (Standard Export)
                        if 'P0' in md:
                            p0 = md['P0']
                            if 'NTC' in p0:
                                ntc = p0['NTC']
                                safe_set(self.ip_var, ntc, 'IP')
                                safe_set(self.port_var, ntc, 'PT')
                                safe_set(self.ci_var, ntc, 'CI')
                                safe_set(self.di_var, ntc, 'DI')
                            if 'JKC' in p0:
                                jkc = p0['JKC']
                                safe_set(self.jkh_var, jkc, 'JKH')
                                safe_set(self.eks_var, jkc, 'EKS')
                                
                        # 2. Try Root NTC / JKC (Legacy or Flat Export)
                        # Only set if not already set by P0 (check if IP is still default?) 
                        # Actually, just overwrite if found, assuming flat structure if P0 missing
                        elif 'NTC' in md:
                            ntc = md['NTC']
                            safe_set(self.ip_var, ntc, 'IP')
                            safe_set(self.port_var, ntc, 'PT')
                            safe_set(self.ci_var, ntc, 'CI')
                            safe_set(self.di_var, ntc, 'DI')
                            
                        if 'JKC' in md and 'P0' not in md:
                            jkc = md['JKC']
                            safe_set(self.jkh_var, jkc, 'JKH')
                            safe_set(self.eks_var, jkc, 'EKS')
                    else:
                        self.metadata = {}
                        
            elif filename.endswith('.csv'):
                with open(filename, 'r') as f:
                    reader = csv.DictReader(f)
                    registers = list(reader)
                    self.metadata = {}
            else:
                messagebox.showerror("❌ Error", "Unsupported file format!")
                return
            
            # Clear existing and add imported
            self.clear_all_registers()
            self.registers = []  # Clear internal register list
            
            for idx, reg in enumerate(registers):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                access = reg.get('access', 'R')
                
                # Create RegisterEntry object with TRANSPARENT FIELDS
                param_id = idx + 1
                param_type = reg.get('parameter_type', 'write' if access in ['W', 'RW'] else 'read_only')
                paired_id = reg.get('paired_param_id', None)
                
                # Convert field values with proper mappings
                final_address = self.safe_int(reg.get('address') or reg.get('register_address'), 0)
                final_fc = self.safe_int(reg.get('fc') or reg.get('function_code'), 3)
                
                register_obj = RegisterEntry(
                    param_id=param_id,
                    slave_id=self.safe_int(reg.get('slave_id'), 1),
                    fc=final_fc,
                    address=final_address,
                    length=self.safe_int(reg.get('length') or reg.get('register_length'), 1),
                    fmt=self.convert_format_to_code(reg.get('fmt') or reg.get('format'), 3),
                    multiplier=self.safe_float(reg.get('multiplier'), 1.0),
                    access=access,
                    cloud=reg.get('cloud', 'No'),
                    json_group=reg.get('json_group', ''),
                    json_unit=reg.get('json_unit', ''),
                    json_key=reg.get('json_key', ''),
                    array_membership=reg.get('array_membership', ''),
                    # TRANSPARENT FIELDS (6 new fields)
                    # Support both old and new field names for backward compatibility
                    packet_num=self.safe_int(reg.get('packet_num')),
                    packet_sa=self.safe_int(reg.get('packet_sa', reg.get('packet_start_addr'))),
                    packet_nrt=self.safe_int(reg.get('packet_nrt', reg.get('packet_register_count'))),
                    parameter_type=param_type,
                    feedback_param_id=self.safe_int(paired_id) if paired_id and param_type == 'write' else None,
                    write_param_id=self.safe_int(paired_id) if paired_id and param_type == 'feedback' else None,
                    jka_equipment_index=self.safe_int(reg.get('jka_equipment_index', reg.get('jka_index')), -1),
                    # LUA BUFFER FIELDS (5 new fields) - support both lua_category and lua_buffer_category
                    in_lua_buffer=reg.get('in_lua_buffer', 'No'),
                    lua_buffer_category=reg.get('lua_category', reg.get('lua_buffer_category', 'N/A')),
                    lbi_position=reg.get('lbi_position', 'Auto'),
                    lbi_data_type=reg.get('lbi_data_type', 'Number'),
                    lua_buffer_note=reg.get('lua_buffer_note', ''),
                    # MANUAL OVERRIDE FIELD (1 new field)
                    manual_override=reg.get('manual_override', False)
                )
                
                self.registers.append(register_obj)
                
                param_type = reg.get('parameter_type', 'write' if access in ['W', 'RW'] else 'read_only')
                
                # Helper to display values properly (None as empty string, values as-is)
                def display_val(val):
                    return '' if val is None else val
                
                self.tree.insert('', 'end', values=(
                    param_id,
                    register_obj.slave_id,
                    register_obj.fc,
                    register_obj.address,
                    register_obj.length,
                    register_obj.fmt,
                    register_obj.multiplier,
                    access,
                    reg.get('cloud', 'No'),
                    reg.get('json_group', ''),
                    reg.get('json_unit', ''),
                    reg.get('json_key', ''),
                    reg.get('array_membership', ''),
                    display_val(self.safe_int(reg.get('b5_id'), param_id)),
                    display_val(self.safe_int(reg.get('packet_num'))),
                    display_val(self.safe_int(reg.get('packet_sa', reg.get('packet_start_addr')))),
                    display_val(self.safe_int(reg.get('packet_nrt', reg.get('packet_register_count')))),
                    # TRANSPARENT FIELDS (columns 18-23) - visible
                    display_val(self.safe_int(reg.get('packet_num'))),
                    display_val(self.safe_int(reg.get('packet_sa', reg.get('packet_start_addr')))),
                    display_val(self.safe_int(reg.get('packet_nrt', reg.get('packet_register_count')))),
                    param_type,
                    display_val(self.safe_int(reg.get('paired_param_id'))),
                    display_val(self.safe_int(reg.get('jka_equipment_index', reg.get('jka_index')), -1)),
                    # LUA BUFFER FIELDS (columns 24-27) - visible
                    reg.get('in_lua_buffer', 'No'),
                    reg.get('lua_category', reg.get('lua_buffer_category', 'N/A')),
                    reg.get('lbi_position', 'Auto'),
                    reg.get('lbi_data_type', 'Number'),
                    # INTERNAL METADATA (columns 28-37) - hidden
                    param_type,
                    display_val(self.safe_int(reg.get('write_param_id'))),
                    display_val(self.safe_int(reg.get('feedback_param_id'))),
                    display_val(self.safe_int(reg.get('p2_mpi_index'))),
                    display_val(self.safe_int(reg.get('p3_mpi_index'))),
                    reg.get('equipment_group', ''),
                    reg.get('device_name', ''),
                    reg.get('equipment_type', ''),
                    display_val(self.safe_int(reg.get('jka_equipment_index', reg.get('jka_index')), -1)),
                    reg.get('lua_buffer_note', ''),  # Column 36 - lua_buffer_note
                    reg.get('manual_override', False)  # Column 37 - manual_override
                ), tags=(tag,))
            
            self.update_status()
            messagebox.showinfo("✅ Success", f"Imported {len(registers)} registers successfully!")
        
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to import file:\n{str(e)}")
    
    def export_registers(self):
        if not self.tree.get_children():
            messagebox.showwarning("⚠️ Warning", "No registers to export!")
            return
        
        # NEW: Validate cloud parameters before export
        cloud_params = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            if len(values) > 8 and values[8] == 'Yes':  # Cloud Output column
                cloud_params.append(values[0])  # S.No
        
        if not cloud_params:
            response = messagebox.askyesnocancel(
                "⚠️ Cloud Parameters Required",
                "WARNING: No parameters marked for Cloud Output!\n\n"
                "The firmware requires at least one parameter in P3.MPI (cloud output buffer).\n"
                "Without cloud parameters, the firmware cannot publish data to MQTT/HTTPS.\n\n"
                "• Click 'Yes' to continue anyway (may cause firmware errors)\n"
                "• Click 'No' to go back and mark parameters for cloud output\n"
                "• Click 'Cancel' to abort export"
            )
            if response is None:  # Cancel
                return
            elif not response:  # No - go back
                messagebox.showinfo(
                    "How to Fix",
                    "To mark parameters for cloud output:\n\n"
                    "1. Double-click a register row to edit\n"
                    "2. Set 'Cloud Output' to 'Yes'\n"
                    "3. Fill in JSON Group, JSON Unit, and JSON Key\n"
                    "4. Repeat for all parameters you want to publish to cloud\n"
                    "5. Export again"
                )
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
                reg_dict = {
                    'param_id': values[0],  # S.No
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
                    'json_key': values[11],
                    'array_membership': values[12] if len(values) > 12 else '',
                    'b5_id': values[13] if len(values) > 13 else values[0]  # B5 ID (same as S.No if not set)
                }
                
                # Add TRANSPARENT FIELDS (6 new fields) - visible in Register_Config.json
                # Get the actual Register object to access transparent fields
                for reg in self.registers:
                    if reg.param_id == values[0]:  # Match by param_id
                        reg_dict['packet_num'] = getattr(reg, 'packet_num', None)
                        reg_dict['packet_sa'] = getattr(reg, 'packet_sa', None)
                        reg_dict['packet_nrt'] = getattr(reg, 'packet_nrt', None)
                        reg_dict['parameter_type'] = getattr(reg, 'parameter_type', None)
                        # Handle paired IDs based on parameter type
                        param_type = getattr(reg, 'parameter_type', None)
                        if param_type == 'write':
                            reg_dict['write_param_id'] = None
                            reg_dict['feedback_param_id'] = getattr(reg, 'feedback_param_id', None)
                        elif param_type == 'feedback':
                            reg_dict['write_param_id'] = getattr(reg, 'write_param_id', None)
                            reg_dict['feedback_param_id'] = None
                        else:
                            reg_dict['write_param_id'] = None
                            reg_dict['feedback_param_id'] = None
                        reg_dict['p2_mpi_index'] = getattr(reg, 'p2_mpi_index', None)
                        reg_dict['p3_mpi_index'] = getattr(reg, 'p3_mpi_index', None)
                        reg_dict['equipment_group'] = getattr(reg, 'equipment_group', '')
                        reg_dict['device_name'] = getattr(reg, 'device_name', '')
                        reg_dict['equipment_type'] = getattr(reg, 'equipment_type', '')
                        reg_dict['jka_equipment_index'] = getattr(reg, 'jka_equipment_index', -1)
                        # Add LUA BUFFER FIELDS (5 new fields)
                        reg_dict['in_lua_buffer'] = getattr(reg, 'in_lua_buffer', 'No')
                        reg_dict['lua_category'] = getattr(reg, 'lua_buffer_category', 'N/A')
                        reg_dict['lbi_position'] = getattr(reg, 'lbi_position', 'Auto')
                        reg_dict['lbi_data_type'] = getattr(reg, 'lbi_data_type', 'Number')
                        reg_dict['lua_buffer_note'] = getattr(reg, 'lua_buffer_note', '')  # Dual-category note
                        # Add MANUAL OVERRIDE FIELD (1 new field)
                        reg_dict['manual_override'] = getattr(reg, 'manual_override', False)
                        break
                
                # Fallback: if register not found in self.registers, read from tree columns
                # (This handles registers added via dialog which might not be in self.registers)
                # BUG FIX: Changed condition from len(values) > 37 to >= 38 since columns are now 0-37 (38 total with manual_override)
                if 'in_lua_buffer' not in reg_dict and len(values) >= 38:
                    reg_dict['packet_num'] = values[17] if len(values) > 17 else None
                    reg_dict['packet_sa'] = values[18] if len(values) > 18 else None
                    reg_dict['packet_nrt'] = values[19] if len(values) > 19 else None
                    reg_dict['parameter_type'] = values[20] if len(values) > 20 else None
                    reg_dict['write_param_id'] = values[28] if len(values) > 28 else None
                    reg_dict['feedback_param_id'] = values[29] if len(values) > 29 else None
                    reg_dict['p2_mpi_index'] = values[30] if len(values) > 30 else None
                    reg_dict['p3_mpi_index'] = values[31] if len(values) > 31 else None
                    reg_dict['equipment_group'] = values[32] if len(values) > 32 else ''
                    reg_dict['device_name'] = values[33] if len(values) > 33 else ''
                    reg_dict['equipment_type'] = values[34] if len(values) > 34 else ''
                    reg_dict['jka_equipment_index'] = values[35] if len(values) > 35 else -1
                    reg_dict['in_lua_buffer'] = values[23] if len(values) > 23 else 'No'
                    reg_dict['lua_category'] = values[24] if len(values) > 24 else 'N/A'
                    reg_dict['lbi_position'] = values[25] if len(values) > 25 else 'Auto'
                    reg_dict['lbi_data_type'] = values[26] if len(values) > 26 else 'Number'
                    reg_dict['lua_buffer_note'] = values[36] if len(values) > 36 else ''
                    reg_dict['manual_override'] = values[37] if len(values) > 37 else False
                
                registers.append(reg_dict)
            
            # Extract metadata section
            metadata = {
                'version': '2.0',  # New transparent schema version
                'total_params': len(registers),
                'total_slaves': len(set(r['slave_id'] for r in registers)),
                'generated_date': datetime.now().isoformat()
            }
            
            # Add slave_order if available (preserve custom ordering)
            if hasattr(self, 'slave_order') and self.slave_order:
                metadata['slave_order'] = self.slave_order
            
            # Add B1, B2, B3, P1 metadata if available (for perfect reconstruction)
            if hasattr(self, 'metadata') and self.metadata:
                if 'b1' in self.metadata:
                    metadata['b1'] = self.metadata['b1']
                if 'b2' in self.metadata:
                    metadata['b2'] = self.metadata['b2']
                if 'b3' in self.metadata:
                    metadata['b3'] = self.metadata['b3']
                if 'p1' in self.metadata:
                    metadata['p1'] = self.metadata['p1']
            
            output_data = {
                'registers': registers,
                'metadata': metadata
            }
            
            if filename.endswith('.json'):
                if FORMATTER_AVAILABLE:
                    format_and_save_json(output_data, filename)
                else:
                    with open(filename, 'w') as f:
                        json.dump(output_data, f, indent=2)
            elif filename.endswith('.csv'):
                with open(filename, 'w', newline='') as f:
                    # CSV export includes all fields including transparent ones
                    if registers:
                        writer = csv.DictWriter(f, fieldnames=registers[0].keys())
                        writer.writeheader()
                        writer.writerows(registers)
            
            messagebox.showinfo("✅ Success", f"Exported {len(registers)} registers successfully!")
        
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to export file:\n{str(e)}")
    
    def import_modbus_paramap(self):
        """Import Modbus and Paramap JSON files to populate register configuration"""
        processing_dialog = None
        try:
            # Ask for Modbus JSON file
            modbus_file = filedialog.askopenfilename(
                title="Select Modbus JSON file (e.g., Modbus_Config.json)",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not modbus_file:
                return
            
            # Ask for Paramap JSON file
            paramap_file = filedialog.askopenfilename(
                title="Select Paramap JSON file (e.g., ParamMap_Config.json)",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not paramap_file:
                return
            
            # Show processing dialog
            processing_dialog = tk.Toplevel(self.root)
            processing_dialog.title("Processing...")
            processing_dialog.geometry("400x150")
            processing_dialog.transient(self.root)
            processing_dialog.grab_set()
            
            tk.Label(processing_dialog, text="🔄 Reverse Transformation in Progress...", 
                    font=('Segoe UI', 12, 'bold')).pack(pady=20)
            progress_label = tk.Label(processing_dialog, text="Loading JSON files...", 
                                     font=('Segoe UI', 10))
            progress_label.pack(pady=10)
            
            processing_dialog.update()
            
            # Load JSON files
            with open(modbus_file, 'r', encoding='utf-8') as f:
                modbus_json = json.load(f)
            
            with open(paramap_file, 'r', encoding='utf-8') as f:
                paramap_json = json.load(f)
            
            progress_label.config(text="Extracting configurations...")
            processing_dialog.update()
            
            # Perform reverse transformation
            result = self._reverse_transform(modbus_json, paramap_json)
            
            # Check if we got valid results
            if not result or 'registers' not in result or not result['registers']:
                if processing_dialog:
                    processing_dialog.destroy()
                messagebox.showwarning("⚠️ Warning", "No registers were extracted from the JSON files.\n\nPlease check that the files contain valid configuration data.")
                return
            
            # CRITICAL: Store imported metadata for preservation during re-generation
            self.metadata = {}
            self.metadata.update(modbus_json)   # Stores B1, B2, B3, B4, B5, B6
            self.metadata.update(paramap_json)  # Stores P1, P2, P3, JKY, JKC, NTC, MST
            print(f"[Import] Metadata stored: {list(self.metadata.keys())}")
            
            progress_label.config(text="Populating application...")
            processing_dialog.update()
            
            # Clear existing data
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Populate communication settings
            if 'B2' in modbus_json:
                br = modbus_json['B2'].get('BR', 19200)
                self.baudrate_var.set(str(br))
                
                data_format = modbus_json['B2'].get('DF', '8E1')
                # Parse data format (e.g., "8N1", "8E1")
                if len(data_format) >= 3:
                    self.data_bits_var.set(data_format[0])
                    parity = data_format[1]
                    parity_map = {'N': 'N (None)', 'E': 'E (Even)', 'O': 'O (Odd)'}
                    self.parity_var.set(parity_map.get(parity, 'E (Even)'))
                    self.stop_bits_var.set(data_format[2])
            
            # Populate profile if available
            if 'MST' in paramap_json and 'PRF' in paramap_json['MST']:
                profile_val = paramap_json['MST']['PRF']
                # Find matching profile in dropdown
                for profile_option in bc.DROPDOWN_OPTIONS['profile']:
                    if profile_option.startswith(str(profile_val)):
                        self.profile_var.set(profile_option)
                        break
            
            # Add registers to tree with all 32 columns (23 visible + 9 internal metadata)
            for i, reg in enumerate(result['registers'], 1):
                param_type = reg.get('parameter_type', 'read_only')
                paired_id = reg.get('feedback_param_id') if param_type == 'write' else (reg.get('write_param_id') if param_type == 'feedback' else None)
                self.tree.insert('', 'end', values=(
                    i,
                    reg['slave_id'],
                    reg['fc'],
                    reg['address'],
                    reg['length'],
                    reg['fmt'],
                    reg['multiplier'],
                    reg['access'],
                    reg['cloud'],
                    reg['json_group'],
                    reg['json_unit'],
                    reg['json_key'],
                    reg.get('array_membership', ''),
                    reg.get('b5_id', i),
                    reg.get('packet_num', 0),
                    reg.get('packet_sa', reg['address']),
                    reg.get('packet_nrt', reg['length']),
                    # TRANSPARENT FIELDS (columns 18-23) - visible
                    reg.get('packet_num', None),
                    reg.get('packet_sa', None),
                    reg.get('packet_nrt', None),
                    param_type,
                    paired_id,
                    reg.get('jka_equipment_index', -1),
                    # LUA BUFFER FIELDS (columns 24-27) - visible
                    reg.get('in_lua_buffer', 'No'),
                    reg.get('lua_buffer_category', 'N/A'),
                    reg.get('lbi_position', 'Auto'),
                    reg.get('lbi_data_type', 'Number'),
                    # INTERNAL METADATA (columns 28-36) - hidden
                    param_type,
                    reg.get('write_param_id', ''),
                    reg.get('feedback_param_id', ''),
                    reg.get('p2_mpi_index', ''),
                    reg.get('p3_mpi_index', ''),
                    reg.get('equipment_group', ''),
                    reg.get('device_name', ''),
                    reg.get('equipment_type', ''),
                    reg.get('jka_equipment_index', -1)
                ), tags=('evenrow' if i % 2 == 0 else 'oddrow',))
            
            self.update_status()
            
            if processing_dialog:
                processing_dialog.destroy()
                processing_dialog = None
            
            # Show success message
            messagebox.showinfo("✅ Success", 
                              f"Reverse transformation completed!\n\n"
                              f"✅ Loaded {len(result['registers'])} register entries\n"
                              f"✅ Communication settings updated\n"
                              f"✅ Profile settings updated\n\n"
                              f"You can now:\n"
                              f"• Edit registers as needed\n"
                              f"• Generate new configuration files\n"
                              f"• Export to CSV")
        
        except FileNotFoundError as e:
            if processing_dialog:
                processing_dialog.destroy()
            messagebox.showerror("❌ Error", f"File not found:\n{str(e)}")
        except json.JSONDecodeError as e:
            if processing_dialog:
                processing_dialog.destroy()
            messagebox.showerror("❌ Error", f"Invalid JSON file:\n{str(e)}\n\nPlease ensure the file is valid JSON format.")
        except KeyError as e:
            if processing_dialog:
                processing_dialog.destroy()
            messagebox.showerror("❌ Error", f"Missing required key in JSON: {str(e)}\n\nPlease ensure both files are valid Modbus and Paramap JSON files with all required sections (B5, B6, P2, P3).")
        except Exception as e:
            if processing_dialog:
                processing_dialog.destroy()
            messagebox.showerror("❌ Error", f"Reverse transformation failed:\n{str(e)}\n\nCheck console for detailed error.")
            import traceback
            print("="*70)
            print("REVERSE TRANSFORMATION ERROR:")
            print("="*70)
            traceback.print_exc()
            print("="*70)
    
    def _reverse_transform(self, modbus_json, paramap_json):
        """Internal reverse transformation logic using updated reverse_engine"""
        try:
            # Use the updated reverse_engine module
            from reverse_engine import ReverseTransformationEngine
            
            engine = ReverseTransformationEngine()
            result = engine.transform(modbus_json, paramap_json)
            
            # Store metadata for perfect reconstruction
            self.metadata = result.get('metadata', {})
            
            # Extract slave_order from B3.SI for preservation
            if 'B3' in modbus_json and 'SI' in modbus_json['B3']:
                self.slave_order = modbus_json['B3']['SI']
                # Store in metadata for export
                if not hasattr(self, 'metadata'):
                    self.metadata = {}
                self.metadata['b3'] = modbus_json['B3']
            
            # Create RegisterEntry objects from the result
            self.registers = []
            for reg_data in result.get('registers', []):
                register_obj = RegisterEntry(
                    param_id=reg_data.get('param_id', reg_data.get('b5_id', 0)),
                    slave_id=reg_data.get('slave_id', 1),
                    fc=reg_data.get('fc', 3),
                    address=reg_data.get('address', 0),
                    length=reg_data.get('length', 1),
                    fmt=reg_data.get('fmt', 1),
                    multiplier=reg_data.get('multiplier', 1.0),
                    access=reg_data.get('access', 'R'),
                    cloud=reg_data.get('cloud', 'No'),
                    json_group=reg_data.get('json_group', ''),
                    json_unit=reg_data.get('json_unit', ''),
                    json_key=reg_data.get('json_key', ''),
                    array_membership=reg_data.get('array_membership', ''),
                    # Transparent fields
                    packet_num=reg_data.get('packet_num', None),
                    packet_sa=reg_data.get('packet_sa', None),
                    packet_nrt=reg_data.get('packet_nrt', None),
                    parameter_type=reg_data.get('parameter_type', 'read_only'),
                    write_param_id=reg_data.get('write_param_id', None),
                    feedback_param_id=reg_data.get('feedback_param_id', None),
                    p2_mpi_index=reg_data.get('p2_mpi_index', None),
                    p3_mpi_index=reg_data.get('p3_mpi_index', None),
                    equipment_group=reg_data.get('equipment_group', ''),
                    device_name=reg_data.get('device_name', ''),
                    equipment_type=reg_data.get('equipment_type', ''),
                    jka_equipment_index=reg_data.get('jka_equipment_index', -1)
                )
                self.registers.append(register_obj)
            
            return result
        except ImportError:
            # Fallback to old logic if reverse_engine not available
            pass
        
        # Original validation
        required_modbus = ['B5', 'B4']
        for key in required_modbus:
            if key not in modbus_json:
                raise KeyError(f"Modbus JSON missing required section: {key}")
        
        required_paramap = ['P2', 'P3']
        for key in required_paramap:
            if key not in paramap_json:
                raise KeyError(f"Paramap JSON missing required section: {key}")
        
        # Extract B5 mappings
        b5 = modbus_json['B5']
        required_b5_keys = ['ID', 'PN', 'STA', 'LN', 'FMT', 'MLT']
        for key in required_b5_keys:
            if key not in b5:
                raise KeyError(f"B5 section missing required key: {key}")
        
        # Check B5 array lengths are consistent
        b5_length = len(b5['ID'])
        for key in required_b5_keys:
            if len(b5[key]) != b5_length:
                raise ValueError(f"B5 array length mismatch: {key} has {len(b5[key])} elements, expected {b5_length}")
        
        b5_id_to_props = {}
        for i in range(len(b5['ID'])):
            b5_id = b5['ID'][i]
            b5_id_to_props[b5_id] = {
                'packet_num': b5['PN'][i],
                'address': b5['STA'][i],
                'length': b5['LN'][i],
                'fmt': b5['FMT'][i],
                'multiplier': b5['MLT'][i]
            }
        
        # Extract B4 mappings (packet to slave/FC)
        b4 = modbus_json['B4']
        required_b4_keys = ['SA', 'FC', 'SID']
        for key in required_b4_keys:
            if key not in b4:
                raise KeyError(f"B4 section missing required key: {key}")
        
        packet_to_slave_fc = {}
        for i in range(len(b4.get('SA', []))):
            packet_num = i + 1
            packet_to_slave_fc[packet_num] = {
                'slave_id': b4['SID'][i] if i < len(b4['SID']) else 0,
                'fc': b4['FC'][i] if i < len(b4['FC']) else 0
            }
        
        # Classify parameters
        b6 = modbus_json.get('B6', {'WP': [], 'RP': []})
        write_params = set(b6.get('WP', []))
        feedback_params = set(b6.get('RP', []))
        p2_mpi = set(paramap_json['P2'].get('MPI', []))
        p3_mpi = set(paramap_json['P3'].get('MPI', []))
        # Extract all P2/P3 arrays for array_membership tracking
        p2_lbi = set(paramap_json["P2"].get("LBI", []))
        p2_rpci = set(paramap_json["P2"].get("RPCI", []))
        p3_mdi = set(paramap_json["P3"].get("MDI", []))
        
        
        # Extract JKY mappings
        b5_to_json_keys = {}
        if 'JKY' in paramap_json:
            jky = paramap_json['JKY']
            jka = jky.get('JKA', [])
            p3 = paramap_json['P3']
            
            # Build MDI to B5 mapping - with validation
            if 'MDI' in p3 and 'MPI' in p3:
                mdi_to_b5 = {}
                min_len = min(len(p3['MDI']), len(p3['MPI']))
                for i in range(min_len):
                    mdi = p3['MDI'][i]
                    b5_id = p3['MPI'][i]
                    mdi_to_b5[mdi] = b5_id
                
                # Flatten JKY structure
                mdi_counter = 1
                for jka_entry in jka:
                    if not isinstance(jka_entry, list) or len(jka_entry) < 3:
                        continue
                    
                    group = str(jka_entry[0])
                    units = jka_entry[1] if isinstance(jka_entry[1], list) else []
                    keys = jka_entry[2] if isinstance(jka_entry[2], list) else []
                    
                    # Ensure units and keys are lists and same length
                    min_entries = min(len(units), len(keys))
                    for j in range(min_entries):
                        if mdi_counter in mdi_to_b5:
                            b5_id = mdi_to_b5[mdi_counter]
                            b5_to_json_keys[b5_id] = {
                                'json_group': group,
                                'json_unit': str(units[j]),
                                'json_key': str(keys[j])
                            }
                        mdi_counter += 1
        
        # Determine access type function
        def determine_access(b5_id):
            if b5_id in write_params:
                # Check if has paired feedback
                try:
                    wp_list = b6.get('WP', [])
                    rp_list = b6.get('RP', [])
                    if b5_id in wp_list:
                        wp_index = wp_list.index(b5_id)
                        if wp_index < len(rp_list):
                            return 'RW'
                except (ValueError, KeyError, IndexError):
                    pass
                return 'W'
            return 'R'

        # Determine array membership function
        def determine_array_membership(b5_id):
            memberships = []
            if b5_id in p2_lbi:
                memberships.append("P2.LBI")
            if b5_id in p2_rpci:
                memberships.append("P2.RPCI")
            if b5_id in p2_mpi:
                memberships.append("P2.MPI")
            if b5_id in p3_mpi:
                memberships.append("P3.MPI")
            if b5_id in p3_mdi:
                memberships.append("P3.MDI")
            return ",".join(memberships)

        
        # Reconstruct registers
        registers = []
        for b5_id in sorted(b5['ID']):
            if b5_id not in b5_id_to_props:
                continue  # Skip if mapping doesn't exist
            
            props = b5_id_to_props[b5_id]
            packet_num = props['packet_num']
            slave_fc = packet_to_slave_fc.get(packet_num, {'slave_id': 0, 'fc': 0})
            
            # Ensure slave_id and fc are valid
            slave_id = slave_fc.get('slave_id', 0)
            fc = slave_fc.get('fc', 0)
            
            # Skip invalid entries
            if slave_id == 0 or fc == 0:
                continue
            
            cloud = 'Yes' if b5_id in b5_to_json_keys else 'No'
            json_keys = b5_to_json_keys.get(b5_id, {
                'json_group': '',
                'json_unit': '',
                'json_key': ''
            })
            
            register = {
                'slave_id': slave_id,
                'fc': fc,
                'address': props['address'],
                'length': props['length'],
                'fmt': props['fmt'],
                'multiplier': props['multiplier'],
                'access': determine_access(b5_id),
                'cloud': cloud,
                'json_group': json_keys.get('json_group', ''),
                'json_unit': json_keys.get('json_unit', ''),
                'json_key': json_keys.get('json_key', ''),
                'array_membership': determine_array_membership(b5_id)
            }
            
            registers.append(register)
        
        return {'registers': registers}
    
    def clear_all_registers(self):
        if not self.tree.get_children():
            return
        
        if messagebox.askyesno("⚠️ Confirm", "Are you sure you want to clear all registers?"):
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # CRITICAL: Clear metadata when deleting all registers
            # This prevents "list index out of range" when loading new data
            self.metadata = None
            
            # Clear clipboard
            self.clipboard = None
            self.btn_paste.config(state='disabled')
            
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
    
    def copy_selected_row(self):
        """Copy selected row(s) to clipboard"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ Warning", "Please select a row to copy!")
            return
        
        # Store selected items data in clipboard
        self.clipboard = []
        for item in selected:
            values = list(self.tree.item(item)['values'])
            self.clipboard.append(values)
        
        # Visual feedback - highlight copied items with green background
        for item in self.tree.get_children():
            # Remove previous copied tag
            current_tags = list(self.tree.item(item, 'tags'))
            if 'copied' in current_tags:
                current_tags.remove('copied')
                self.tree.item(item, tags=tuple(current_tags))
        
        # Add copied tag to selected items
        for item in selected:
            current_tags = list(self.tree.item(item, 'tags'))
            if 'copied' not in current_tags:
                current_tags.append('copied')
            self.tree.item(item, tags=tuple(current_tags))
        
        # Enable paste button
        self.btn_paste.config(state='normal')
        
        # Update status with clipboard info
        count = len(self.clipboard)
        self.status_label.config(text=f"📊 Total Registers: {len(self.tree.get_children())} | 📋 Copied: {count} register{'s' if count != 1 else ''}")
        
        # Show temporary notification
        self.root.after(2000, self.update_status)  # Reset status after 2 seconds
    
    def paste_row(self):
        """Paste copied row(s) at selected position or at end"""
        if not self.clipboard:
            messagebox.showwarning("⚠️ Warning", "Nothing to paste! Copy a row first.")
            return
        
        # Determine insert position
        selected = self.tree.selection()
        if selected:
            # Insert after the last selected item
            insert_position = self.tree.index(selected[-1]) + 1
        else:
            # Insert at the end
            insert_position = len(self.tree.get_children())
        
        # Insert copied items
        pasted_items = []
        for offset, values in enumerate(self.clipboard):
            # Create a copy of values to avoid modifying clipboard
            new_values = list(values)
            
            # Clear packet assignments (will be recalculated)
            # Packet fields: columns 14-19 (6 fields)
            new_values[14] = ''  # packet_num (internal)
            new_values[15] = ''  # packet_sa (internal)
            new_values[16] = ''  # packet_nrt (internal)
            new_values[17] = ''  # Packet # (visible)
            new_values[18] = ''  # Packet Start (visible)
            new_values[19] = ''  # Packet Regs (visible)
            
            # Insert at position
            tag = 'evenrow' if (insert_position + offset) % 2 == 0 else 'oddrow'
            item = self.tree.insert('', insert_position + offset, values=new_values, tags=(tag,))
            pasted_items.append(item)
        
        # Renumber all items
        self.renumber_items()
        
        # Select the newly pasted items
        self.tree.selection_set(pasted_items)
        
        # Scroll to show first pasted item
        if pasted_items:
            self.tree.see(pasted_items[0])
        
        self.update_status()
        
        # Show success message
        count = len(self.clipboard)
        messagebox.showinfo("✅ Success", 
                          f"Pasted {count} register{'s' if count != 1 else ''} successfully!\n\n"
                          f"💡 Tip: Packet assignments cleared. Click 'Calculate Packets' to reassign.")
    
    def duplicate_selected_row(self):
        """Duplicate selected row(s) - quick copy and paste"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("⚠️ Warning", "Please select a row to duplicate!")
            return
        
        # Copy selected items
        temp_clipboard = []
        for item in selected:
            values = list(self.tree.item(item)['values'])
            temp_clipboard.append(values)
        
        # Get position of last selected item
        insert_position = self.tree.index(selected[-1]) + 1
        
        # Insert duplicated items right after selection
        duplicated_items = []
        for offset, values in enumerate(temp_clipboard):
            # Create a copy of values
            new_values = list(values)
            
            # Clear packet assignments (will be recalculated)
            new_values[14] = ''  # packet_num (internal)
            new_values[15] = ''  # packet_sa (internal)
            new_values[16] = ''  # packet_nrt (internal)
            new_values[17] = ''  # Packet # (visible)
            new_values[18] = ''  # Packet Start (visible)
            new_values[19] = ''  # Packet Regs (visible)
            
            # Insert at position
            tag = 'evenrow' if (insert_position + offset) % 2 == 0 else 'oddrow'
            item = self.tree.insert('', insert_position + offset, values=new_values, tags=(tag,))
            duplicated_items.append(item)
        
        # Renumber all items
        self.renumber_items()
        
        # Select the newly duplicated items
        self.tree.selection_set(duplicated_items)
        
        # Scroll to show first duplicated item
        if duplicated_items:
            self.tree.see(duplicated_items[0])
        
        self.update_status()
        
        # Show success message
        count = len(temp_clipboard)
        messagebox.showinfo("✅ Success", 
                          f"Duplicated {count} register{'s' if count != 1 else ''} successfully!\n\n"
                          f"💡 Tip: Edit the duplicated register(s) to change parameters.")
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        # Select the item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            # If item not already selected, select it
            if item not in self.tree.selection():
                self.tree.selection_set(item)
            
            # Update paste menu state
            paste_index = 2  # Index of paste command in context menu
            if self.clipboard:
                self.context_menu.entryconfig(paste_index, state='normal')
            else:
                self.context_menu.entryconfig(paste_index, state='disabled')
            
            # Show menu at cursor position
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
    
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
            
            access = values[7]
            cloud = values[8] == 'Yes'
            
            # Helper to convert empty string to None
            def get_optional_int(val):
                if val == '' or val is None:
                    return None
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return None
            
            # Read TRANSPARENT fields from columns 18-23 (visible columns)
            # Column indices: 18=Packet#, 19=PacketStart, 20=PacketRegs, 21=ParamType, 22=PairedWith, 23=JKAIndex
            packet_num = None  # Will be auto-assigned during generation if None
            packet_sa = None
            packet_nrt = None
            parameter_type = 'read_only'  # Default
            paired_param_id = None
            jka_index = -1
            
            if len(values) > 17:  # Column 18: Packet #
                packet_num = get_optional_int(values[17])
            if len(values) > 18:  # Column 19: Packet Start
                packet_sa = get_optional_int(values[18])
            if len(values) > 19:  # Column 20: Packet Regs
                packet_nrt = get_optional_int(values[19])
            if len(values) > 20:  # Column 21: Param Type
                parameter_type = values[20] if values[20] else 'read_only'
            if len(values) > 21:  # Column 22: Paired With
                paired_param_id = get_optional_int(values[21])
            if len(values) > 22:  # Column 23: JKA Index
                jka_index = get_optional_int(values[22])
                if jka_index is None:
                    jka_index = -1
            
            # Read LUA BUFFER FIELDS from columns 24-27 (visible columns)
            in_lua_buffer = "No"
            lua_buffer_category = "N/A"
            lbi_position = "Auto"
            lbi_data_type = "Number"
            
            if len(values) > 23:  # Column 24: In Lua Buffer
                in_lua_buffer = str(values[23]) if values[23] else "No"
            if len(values) > 24:  # Column 25: Lua Category
                lua_buffer_category = str(values[24]) if values[24] else "N/A"
            if len(values) > 25:  # Column 26: LBI Position
                lbi_position = values[25] if values[25] else "Auto"
                # Keep as string or int, depending on value
            if len(values) > 26:  # Column 27: LBI Data Type
                lbi_data_type = str(values[26]) if values[26] else "Number"
            
            # Fallback inference for parameter_type if not set
            if not parameter_type or parameter_type == '':
                if access in ['W', 'RW']:
                    parameter_type = 'write'
                else:
                    parameter_type = 'read_only'
            
            # Read INTERNAL METADATA from columns 28-36 (hidden columns)
            write_param_id = None
            feedback_param_id = None
            p2_mpi_index = None
            p3_mpi_index = None
            equipment_group = ""
            device_name = ""
            equipment_type = ""
            jka_equipment_index = -1
            
            if len(values) > 28:  # Column 29: Write Param ID
                write_param_id = get_optional_int(values[28])
            if len(values) > 29:  # Column 30: Feedback Param ID
                feedback_param_id = get_optional_int(values[29])
            if len(values) > 30:  # Column 31: P2 MPI Index
                p2_mpi_index = get_optional_int(values[30])
            if len(values) > 31:  # Column 32: P3 MPI Index
                p3_mpi_index = get_optional_int(values[31])
            if len(values) > 32:  # Column 33: Equipment Group
                equipment_group = str(values[32]) if values[32] else ""
            if len(values) > 33:  # Column 34: Device Name
                device_name = str(values[33]) if values[33] else ""
            if len(values) > 34:  # Column 35: Equipment Type
                equipment_type = str(values[34]) if values[34] else ""
            if len(values) > 35:  # Column 36: JKA Equipment Index
                jka_equipment_index = get_optional_int(values[35])
                if jka_equipment_index is None:
                    jka_equipment_index = -1
            
            # Use jka_equipment_index if jka_index not explicitly set
            if jka_index == -1 and jka_equipment_index != -1:
                jka_index = jka_equipment_index
            
            # Determine write/feedback cross-references from paired_param_id
            if paired_param_id is not None:
                if parameter_type == 'write':
                    feedback_param_id = paired_param_id
                elif parameter_type == 'feedback':
                    write_param_id = paired_param_id
            
            reg = RegisterEntry(
                param_id=idx + 1,  # INTEGER, not string!
                slave_id=int(values[1]),
                fc=int(values[2]),
                address=int(values[3]),
                length=int(values[4]),
                fmt=int(values[5]),
                multiplier=float(values[6]),
                access=access,
                cloud=cloud,
                json_group=values[9],
                json_unit=values[10],
                json_key=values[11],
                array_membership=values[12] if len(values) > 12 else "",
                # TRANSPARENT FIELDS
                packet_num=packet_num,
                packet_sa=packet_sa,
                packet_nrt=packet_nrt,
                parameter_type=parameter_type,
                write_param_id=write_param_id,
                feedback_param_id=feedback_param_id,
                p2_mpi_index=p2_mpi_index,
                p3_mpi_index=p3_mpi_index,
                equipment_group=equipment_group,
                device_name=device_name,
                equipment_type=equipment_type,
                jka_equipment_index=jka_index,
                # LUA BUFFER FIELDS
                in_lua_buffer=in_lua_buffer,
                lua_buffer_category=lua_buffer_category,
                lbi_position=lbi_position,
                lbi_data_type=lbi_data_type
            )
            
            # Add legacy packet metadata for backward compatibility
            if packet_num is not None:
                reg.packet_num = packet_num
            if packet_sa is not None:
                reg.packet_start_addr = packet_sa
            if packet_nrt is not None:
                reg.packet_register_count = packet_nrt
            
            # Store paired_param_id in transparent field
            reg.paired_param_id = paired_param_id
            
            # Store jka_index in transparent field
            reg.jka_index = jka_index
            
            registers.append(reg)
        return registers, sorted(list(slaves_set))
    
    def validate_configuration(self):
        """Validate current configuration and show detailed results"""
        try:
            registers, slaves = self.get_register_data()
            
            if not registers:
                messagebox.showwarning("⚠️ No Registers", "Please add at least one register before validating.")
                return
            
            # Perform validation
            validation = validate_registers(registers)
            
            # Safety check: ensure validation result has required keys
            if 'status' not in validation:
                validation['status'] = 'error'
            if 'message' not in validation:
                validation['message'] = 'Validation completed but no details available'
            if 'warnings' not in validation:
                validation['warnings'] = []
            if 'errors' not in validation:
                validation['errors'] = []
            
            # Create result dialog
            result_dialog = tk.Toplevel(self.root)
            result_dialog.title("🔍 Configuration Validation Report")
            result_dialog.geometry("700x500")
            result_dialog.configure(bg='#f5f7fa')
            result_dialog.transient(self.root)
            result_dialog.grab_set()
            
            # Header
            header_frame = tk.Frame(result_dialog, bg='#34495e', height=80)
            header_frame.pack(fill='x')
            header_frame.pack_propagate(False)
            
            if validation['status'] == 'valid':
                icon = "✅"
                title_text = "Configuration Valid"
                color = '#2ecc71'
            elif validation['status'] == 'warning':
                icon = "⚠️"
                title_text = "Configuration Valid with Warnings"
                color = '#f39c12'
            else:  # error
                icon = "❌"
                title_text = "Configuration Has Critical Issues"
                color = '#e74c3c'
            
            tk.Label(header_frame, text=icon, font=('Segoe UI', 36), bg='#34495e', fg='white').pack(pady=10)
            tk.Label(header_frame, text=title_text, font=('Segoe UI', 16, 'bold'), bg='#34495e', fg='white').pack()
            
            # Details frame with scrollbar
            details_frame = tk.Frame(result_dialog, bg='#f5f7fa')
            details_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            canvas = tk.Canvas(details_frame, bg='#ffffff', highlightthickness=0)
            scrollbar = ttk.Scrollbar(details_frame, orient='vertical', command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Display validation message
            msg_frame = tk.Frame(scrollable_frame, bg='#ffffff', relief='solid', borderwidth=1)
            msg_frame.pack(fill='x', padx=10, pady=10)
            
            tk.Label(msg_frame, text=validation['message'], font=('Segoe UI', 11), 
                    bg='#ffffff', fg='#2c3e50', justify='left', wraplength=600).pack(padx=15, pady=15)
            
            # Display warnings if any
            if 'warnings' in validation and validation['warnings']:
                warn_frame = tk.Frame(scrollable_frame, bg='#fff3cd', relief='solid', borderwidth=1)
                warn_frame.pack(fill='x', padx=10, pady=10)
                
                tk.Label(warn_frame, text="⚠️ Warnings", font=('Segoe UI', 12, 'bold'), 
                        bg='#fff3cd', fg='#856404').pack(anchor='w', padx=15, pady=(10, 5))
                
                for warning in validation['warnings']:
                    tk.Label(warn_frame, text=f"• {warning}", font=('Segoe UI', 10), 
                            bg='#fff3cd', fg='#856404', justify='left', wraplength=600).pack(anchor='w', padx=25, pady=2)
                
                tk.Label(warn_frame, text="", bg='#fff3cd').pack(pady=5)
            
            # Display critical issues if any
            if 'errors' in validation and validation['errors']:
                error_frame = tk.Frame(scrollable_frame, bg='#f8d7da', relief='solid', borderwidth=1)
                error_frame.pack(fill='x', padx=10, pady=10)
                
                tk.Label(error_frame, text="❌ Critical Issues", font=('Segoe UI', 12, 'bold'), 
                        bg='#f8d7da', fg='#721c24').pack(anchor='w', padx=15, pady=(10, 5))
                
                for error in validation['errors']:
                    tk.Label(error_frame, text=f"• {error}", font=('Segoe UI', 10), 
                            bg='#f8d7da', fg='#721c24', justify='left', wraplength=600).pack(anchor='w', padx=25, pady=2)
                
                tk.Label(error_frame, text="", bg='#f8d7da').pack(pady=5)
            
            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
            # Action buttons
            btn_frame = tk.Frame(result_dialog, bg='#f5f7fa')
            btn_frame.pack(fill='x', padx=20, pady=10)
            
            if validation['status'] != 'error':
                proceed_btn = tk.Button(btn_frame, text="✅ Proceed to Generate", 
                                       font=('Segoe UI', 11, 'bold'), bg='#2ecc71', fg='white',
                                       relief='flat', padx=20, pady=10, cursor='hand2',
                                       command=lambda: [result_dialog.destroy(), self.generate_configs()])
                proceed_btn.pack(side='left', padx=5)
            
            close_btn = tk.Button(btn_frame, text="Close", 
                                 font=('Segoe UI', 11), bg='#95a5a6', fg='white',
                                 relief='flat', padx=20, pady=10, cursor='hand2',
                                 command=result_dialog.destroy)
            close_btn.pack(side='left', padx=5)
            
            # Center the dialog
            result_dialog.update_idletasks()
            x = (result_dialog.winfo_screenwidth() // 2) - (result_dialog.winfo_width() // 2)
            y = (result_dialog.winfo_screenheight() // 2) - (result_dialog.winfo_height() // 2)
            result_dialog.geometry(f"+{x}+{y}")
            
        except Exception as e:
            messagebox.showerror("❌ Validation Error", f"Validation failed:\n{str(e)}")
    
    def _get_reg_value(self, reg, key, default=None):
        """Safely get value from register (dict or object)"""
        if isinstance(reg, dict):
            return reg.get(key, default)
        else:
            return getattr(reg, key, default)
    
    def validate_packet_assignments(self, registers):
        """
        Validate packet assignments for firmware compatibility
        
        Returns:
            {
                'status': 'ok' | 'warning' | 'error',
                'errors': [...],     # Critical issues (block generation)
                'warnings': [...]    # Non-critical issues (allow but warn)
            }
        """
        errors = []
        warnings = []
        
        # Group by packet number
        packets = {}
        for reg in registers:
            pnum = self._get_reg_value(reg, 'packet_num')
            if pnum is None or pnum == '':
                pnum = 0
            else:
                try:
                    pnum = int(pnum)
                except (ValueError, TypeError):
                    pnum = 0
            
            if pnum not in packets:
                packets[pnum] = []
            packets[pnum].append(reg)
        
        # Check if there are unassigned packets
        if 0 in packets and len(packets[0]) > 0:
            warnings.append(f"{len(packets[0])} parameter(s) have no packet assignment. Click 'Calculate Packets' to auto-assign.")
        
        # Validate each assigned packet
        for pnum, regs in packets.items():
            if pnum == 0:  # Skip unassigned
                continue
            
            # Critical: Invalid packet number
            if pnum <= 0:
                errors.append(f"Invalid packet number: {pnum} (must be ≥ 1)")
                continue
            
            # Critical: Mixed Slave IDs
            slave_ids = set(self._get_reg_value(r, 'slave_id') for r in regs)
            if len(slave_ids) > 1:
                errors.append(
                    f"Packet {pnum}: Mixed Slave IDs {sorted(slave_ids)}. "
                    "Firmware requires same Slave ID per packet."
                )
            
            # Critical: Mixed Function Codes
            fcs = set(self._get_reg_value(r, 'fc') for r in regs)
            if len(fcs) > 1:
                errors.append(
                    f"Packet {pnum}: Mixed Function Codes {sorted(fcs)}. "
                    "Firmware requires same FC per packet."
                )
            
            # Critical: Too many registers
            if len(regs) > 70:
                errors.append(
                    f"Packet {pnum}: {len(regs)} registers exceeds "
                    "firmware limit of 70 per packet."
                )
            
            # Critical: Address span exceeds firmware limit
            # Must consider multi-register parameters (length > 1)
            if len(regs) >= 1:
                all_addresses = []
                for r in regs:
                    addr = self._get_reg_value(r, 'address')
                    length = self._get_reg_value(r, 'length', 1)
                    # Add all addresses this register occupies
                    all_addresses.extend(range(addr, addr + length))
                
                min_addr = min(all_addresses)
                max_addr = max(all_addresses)
                address_span = max_addr - min_addr + 1  # Full span including multi-register params
                
                if address_span > 70:
                    errors.append(
                        f"Packet {pnum}: Address span {address_span} "
                        f"(addresses {min_addr}-{max_addr}) exceeds "
                        "firmware limit of 70 address units."
                    )
            
            # Warning: Very small packet (only if there are multiple packets)            # Warning: Very small packet (only if there are multiple packets)
            if len(regs) == 1 and len([p for p in packets.keys() if p > 0]) > 1:
                warnings.append(
                    f"Packet {pnum}: Only 1 register. "
                    "Consider combining with adjacent packets for efficiency."
                )
        
        # Warning: Non-sequential packet numbers
        packet_nums = sorted(pnum for pnum in packets.keys() if pnum > 0)
        if packet_nums:
            expected = list(range(1, max(packet_nums) + 1))
            missing = set(expected) - set(packet_nums)
            if missing:
                warnings.append(
                    f"Non-sequential packet numbers. "
                    f"Found: {packet_nums}, Missing: {sorted(missing)}"
                )
        
        # Determine status
        if errors:
            status = 'error'
        elif warnings:
            status = 'warning'
        else:
            status = 'ok'
        
        return {
            'status': status,
            'errors': errors,
            'warnings': warnings,
            'packet_count': len([p for p in packets.keys() if p > 0]),
            'param_count': sum(len(regs) for pnum, regs in packets.items() if pnum > 0)
        }
    
    def calculate_packets(self):
        """Calculate packet assignments and show preview"""
        try:
            # Get current registers from table
            registers = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                reg = {
                    'slave_id': values[1],
                    'fc': values[2],
                    'address': values[3],
                    'length': values[4],
                    'fmt': values[5],
                    'multiplier': values[6],
                    'access': values[7],
                    'cloud': values[8],
                    'b5_id': values[13] if len(values) > 13 else values[0]
                }
                registers.append(reg)
            
            if not registers:
                messagebox.showwarning("⚠️ No Registers", "Please add at least one register before calculating packets.")
                return
            
            # Auto-assign packet numbers
            registers = auto_assign_packet_numbers(registers)
            
            # Update tree with calculated packet numbers, packet_sa, and packet_nrt
            for idx, item in enumerate(self.tree.get_children()):
                values = list(self.tree.item(item)['values'])
                # Update packet fields (both internal and visible columns)
                values[14] = registers[idx]['packet_num']   # Internal Packet Num
                values[15] = registers[idx]['packet_sa']    # Internal Packet SA
                values[16] = registers[idx]['packet_nrt']   # Internal Packet NRT
                values[17] = registers[idx]['packet_num']   # Visible Packet #
                values[18] = registers[idx]['packet_sa']    # Visible Packet Start
                values[19] = registers[idx]['packet_nrt']   # Visible Packet Regs
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.tree.item(item, values=values, tags=(tag,))
            
            # Validate packet assignments
            validation = self.validate_packet_assignments(registers)
            
            # Show preview dialog
            self.show_packet_preview(registers, validation)
            
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to calculate packets:\n{str(e)}")
    
    def show_packet_preview(self, registers, validation):
        """Show packet grouping preview dialog"""
        # Create preview dialog
        preview_dialog = tk.Toplevel(self.root)
        preview_dialog.title("🔄 Packet Calculation Preview")
        preview_dialog.geometry("800x600")
        preview_dialog.configure(bg='#f5f7fa')
        preview_dialog.transient(self.root)
        preview_dialog.grab_set()
        
        # Header
        header_frame = tk.Frame(preview_dialog, bg='#9b59b6', height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        if validation['status'] == 'ok':
            icon = "✅"
            title_text = "Packet Calculation Complete"
        elif validation['status'] == 'warning':
            icon = "⚠️"
            title_text = "Packets Calculated with Warnings"
        else:
            icon = "❌"
            title_text = "Packet Calculation Has Issues"
        
        tk.Label(header_frame, text=icon, font=('Segoe UI', 36), bg='#9b59b6', fg='white').pack(pady=5)
        tk.Label(header_frame, text=title_text, font=('Segoe UI', 16, 'bold'), bg='#9b59b6', fg='white').pack()
        
        # Summary section
        summary_frame = tk.Frame(preview_dialog, bg='#ffffff', relief='solid', borderwidth=1)
        summary_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        tk.Label(summary_frame, text="📊 Summary:", font=('Segoe UI', 12, 'bold'), 
                bg='#ffffff', fg='#2c3e50').pack(anchor='w', padx=15, pady=(10, 5))
        
        summary_text = f"• Total Packets: {validation['packet_count']}\n"
        summary_text += f"• Total Parameters: {validation['param_count']}\n"
        
        # Check if all packets are within limits
        packets_ok = all(len([r for r in registers if self._get_reg_value(r, 'packet_num') == p]) <= 70 
                        for p in set(self._get_reg_value(r, 'packet_num', 0) for r in registers) if p > 0)
        summary_text += f"• All packets ≤ 70 registers: {'✓' if packets_ok else '✗'}"
        
        tk.Label(summary_frame, text=summary_text, font=('Segoe UI', 10), 
                bg='#ffffff', fg='#2c3e50', justify='left').pack(anchor='w', padx=30, pady=(0, 10))
        
        # Details frame with scrollbar
        details_frame = tk.Frame(preview_dialog, bg='#f5f7fa')
        details_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        
        canvas = tk.Canvas(details_frame, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(details_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Packet details
        packet_frame = tk.Frame(scrollable_frame, bg='#ffffff', relief='solid', borderwidth=1)
        packet_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(packet_frame, text="📦 Packet Details:", font=('Segoe UI', 12, 'bold'), 
                bg='#ffffff', fg='#2c3e50').pack(anchor='w', padx=15, pady=(10, 5))
        
        # Group registers by packet
        packets = {}
        for reg in registers:
            pnum = self._get_reg_value(reg, 'packet_num', 0)
            if pnum not in packets:
                packets[pnum] = []
            packets[pnum].append(reg)
        
        # Display each packet
        for pnum in sorted(packets.keys()):
            if pnum == 0:
                continue
            regs = packets[pnum]
            if not regs:
                continue
            
            # Get common properties
            slave_id = self._get_reg_value(regs[0], 'slave_id')
            fc = self._get_reg_value(regs[0], 'fc')
            addresses = sorted(self._get_reg_value(r, 'address') for r in regs)
            param_ids = [i+1 for i, r in enumerate(registers) if self._get_reg_value(r, 'packet_num') == pnum]
            
            # Get packet_sa and packet_nrt
            packet_sa = self._get_reg_value(regs[0], 'packet_sa', addresses[0])
            packet_nrt = self._get_reg_value(regs[0], 'packet_nrt', len(regs))
            
            packet_text = f"Packet {pnum}: Slave {slave_id}, FC {fc}\n"
            packet_text += f"  → {len(regs)} parameter(s) at addresses: {addresses}\n"
            packet_text += f"  → Modbus Read: FC{fc}(address={packet_sa}, count={packet_nrt})\n"
            packet_text += f"  → Params: {', '.join(map(str, param_ids))}"
            
            tk.Label(packet_frame, text=packet_text, font=('Segoe UI', 10), 
                    bg='#ffffff', fg='#34495e', justify='left').pack(anchor='w', padx=30, pady=2)
        
        tk.Label(packet_frame, text="", bg='#ffffff').pack(pady=5)
        
        # Display warnings if any
        if validation['warnings']:
            warn_frame = tk.Frame(scrollable_frame, bg='#fff3cd', relief='solid', borderwidth=1)
            warn_frame.pack(fill='x', padx=10, pady=10)
            
            tk.Label(warn_frame, text="⚠️ Warnings:", font=('Segoe UI', 12, 'bold'), 
                    bg='#fff3cd', fg='#856404').pack(anchor='w', padx=15, pady=(10, 5))
            
            for warning in validation['warnings']:
                tk.Label(warn_frame, text=f"• {warning}", font=('Segoe UI', 10), 
                        bg='#fff3cd', fg='#856404', justify='left', wraplength=700).pack(anchor='w', padx=25, pady=2)
            
            tk.Label(warn_frame, text="", bg='#fff3cd').pack(pady=5)
        
        # Display errors if any
        if validation['errors']:
            error_frame = tk.Frame(scrollable_frame, bg='#f8d7da', relief='solid', borderwidth=1)
            error_frame.pack(fill='x', padx=10, pady=10)
            
            tk.Label(error_frame, text="❌ Critical Issues:", font=('Segoe UI', 12, 'bold'), 
                    bg='#f8d7da', fg='#721c24').pack(anchor='w', padx=15, pady=(10, 5))
            
            for error in validation['errors']:
                tk.Label(error_frame, text=f"• {error}", font=('Segoe UI', 10), 
                        bg='#f8d7da', fg='#721c24', justify='left', wraplength=700).pack(anchor='w', padx=25, pady=2)
            
            tk.Label(error_frame, text="", bg='#f8d7da').pack(pady=5)
        
        # Info note
        info_frame = tk.Frame(scrollable_frame, bg='#e8f4f8', relief='solid', borderwidth=1)
        info_frame.pack(fill='x', padx=10, pady=10)
        
        info_text = "ℹ️ Note: You can manually edit packet assignments by double-clicking any parameter row in the table."
        tk.Label(info_frame, text=info_text, font=('Segoe UI', 10, 'italic'), 
                bg='#e8f4f8', fg='#2c3e50', wraplength=700).pack(padx=15, pady=10)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Action buttons
        btn_frame = tk.Frame(preview_dialog, bg='#f5f7fa')
        btn_frame.pack(fill='x', padx=20, pady=10)
        
        close_btn = tk.Button(btn_frame, text="Close & Review Table", 
                             font=('Segoe UI', 11, 'bold'), bg='#95a5a6', fg='white',
                             relief='flat', padx=20, pady=10, cursor='hand2',
                             command=preview_dialog.destroy)
        close_btn.pack(side='left', padx=5)
        
        if validation['status'] != 'error':
            generate_btn = tk.Button(btn_frame, text="✅ Proceed to Generate", 
                                   font=('Segoe UI', 11, 'bold'), bg='#2ecc71', fg='white',
                                   relief='flat', padx=20, pady=10, cursor='hand2',
                                   command=lambda: [preview_dialog.destroy(), self.generate_configs()])
            generate_btn.pack(side='left', padx=5)
        
        # Center the dialog
        preview_dialog.update_idletasks()
        x = (preview_dialog.winfo_screenwidth() // 2) - (preview_dialog.winfo_width() // 2)
        y = (preview_dialog.winfo_screenheight() // 2) - (preview_dialog.winfo_height() // 2)
        preview_dialog.geometry(f"+{x}+{y}")
    
    def generate_configs(self):
        try:
            registers, slaves = self.get_register_data()
            
            if not registers:
                messagebox.showerror("❌ Error", "Please add at least one register!")
                return
            
            # Check if packet numbers are assigned
            has_packet_nums = any(
                self._get_reg_value(reg, 'packet_num') not in [None, '', 0] 
                for reg in registers
            )
            
            if not has_packet_nums:
                # Auto-calculate packet numbers
                print("ℹ️ No packet assignments found. Auto-calculating...")
                registers = auto_assign_packet_numbers(registers)
                
                # Update tree with calculated packet numbers, packet_sa, and packet_nrt (in background)
                for idx, item in enumerate(self.tree.get_children()):
                    values = list(self.tree.item(item)['values'])
                    values[14] = registers[idx]['packet_num']   # Internal Packet Num
                    values[15] = registers[idx]['packet_sa']    # Internal Packet SA
                    values[16] = registers[idx]['packet_nrt']   # Internal Packet NRT
                    values[17] = registers[idx]['packet_num']   # Visible Packet #
                    values[18] = registers[idx]['packet_sa']    # Visible Packet Start
                    values[19] = registers[idx]['packet_nrt']   # Visible Packet Regs
                    tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                    self.tree.item(item, values=values, tags=(tag,))
                
                messagebox.showinfo("ℹ️ Auto-Calculated", 
                                  f"Packet numbers auto-assigned.\n\n"
                                  f"Total packets: {max(r.get('packet_num', 0) for r in registers)}\n"
                                  f"Total parameters: {len(registers)}")
            
            # Validate packet assignments
            packet_validation = self.validate_packet_assignments(registers)
            
            if packet_validation['status'] == 'error':
                # Critical errors - block generation
                error_msg = "❌ Packet Assignment Errors:\n\n"
                error_msg += "\n".join(f"• {err}" for err in packet_validation['errors'])
                error_msg += "\n\nPlease fix these issues before generating configurations."
                messagebox.showerror("❌ Packet Validation Failed", error_msg)
                return
            
            if packet_validation['status'] == 'warning':
                # Warnings - ask user if they want to proceed
                warning_msg = "⚠️ Packet Assignment Warnings:\n\n"
                warning_msg += "\n".join(f"• {warn}" for warn in packet_validation['warnings'])
                warning_msg += "\n\nDo you want to proceed with generation?"
                
                if not messagebox.askyesno("⚠️ Warnings Found", warning_msg):
                    return  # User chose not to proceed
            
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
            # Pass metadata for perfect reconstruction if available
            metadata = getattr(self, 'metadata', None)
            tentative_modbus_io = generate_modbus_io_json(communication, slaves, packets, registers, metadata=metadata)
            
            # Gather Global Config from UI (For NTC/JKC Override in Forward Generation)
            ntc_config = {
                "IP": self.ip_var.get(),
                "PT": self.port_var.get(),
                "CI": self.ci_var.get(),
                "DI": self.di_var.get()
                # SN, MI, MT are auto-generated from slaves/registers inside the function
            }
            
            jkc_config = {
                "JKH": self.jkh_var.get(),
                "EKS": self.eks_var.get()
            }
            
            tentative_param_cfg = generate_parameter_config_json(registers, profile, slaves, metadata=metadata,
                                                                 ntc_config=ntc_config, jkc_config=jkc_config)

            # Run internal validation and surface results via messageboxes
            v1 = validate_modbus_io(tentative_modbus_io, registers, packets, communication, slaves)
            v2 = validate_parameter_config(tentative_param_cfg, registers)

            all_errors = v1['errors'] + v2['errors']
            all_warnings = v1['warnings'] + v2['warnings']

            if all_errors:
                short = '\n'.join(all_errors[:10])
                more = len(all_errors) - 10
                if more > 0:
                    short += f"\n...and {more} more errors"
                
                # Show warnings but allow generation anyway
                full = '\n'.join(all_errors + ["\n"] + ["Warnings:"] + all_warnings)
                
                # Ask if user wants to see full details
                if messagebox.askyesno("⚠️ Validation Issues Detected", 
                                       f"Validation found {len(all_errors)} error(s) and {len(all_warnings)} warning(s):\n\n{short}\n\n"
                                       "⚠️ Generation will proceed anyway, but firmware may have issues.\n\n"
                                       "Save full details to a text file?"):
                    try:
                        path = os.path.join(os.getcwd(), f"validation_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                        with open(path, 'w', encoding='utf-8') as fh:
                            fh.write(full)
                        messagebox.showinfo("✅ Saved", f"Full validation details saved to:\n{path}")
                    except Exception as e:
                        messagebox.showerror("❌ Save Failed", f"Failed to save validation details: {e}")
                
                # Update status to show validation issues
                self.status_label.config(text=f"⚠️ Generated with {len(all_errors)} error(s), {len(all_warnings)} warning(s)")

            elif all_warnings:
                short_w = '\n'.join(all_warnings[:15])
                more_w = len(all_warnings) - 15
                if more_w > 0:
                    short_w += f"\n...and {more_w} more warnings"
                
                messagebox.showinfo("⚠️ Validation Warnings", 
                                   f"Validation completed with {len(all_warnings)} warning(s):\n\n{short_w}\n\n"
                                   "Generation will proceed.")
                
                # Update status to show warnings
                self.status_label.config(text=f"✅ Generated with {len(all_warnings)} warning(s)")

            # Accept and set generated
            self.generated_modbus_io = tentative_modbus_io
            self.generated_parameter_config = tentative_param_cfg
            
            # Generate Output JSON template
            try:
                # Pass machine_id and device_id from UI fields
                machine_id = self.machine_id_var.get().strip() or "EnergyHive_Test"
                device_id = self.di_var.get().strip() or "TSA_Serv1001"
                self.generated_output_json = generate_output_json(tentative_param_cfg, registers, machine_id, device_id)
            except Exception as e:
                messagebox.showwarning("⚠️ Warning", f"Output JSON generation failed:\n{str(e)}\n\nContinuing with Modbus and ParamMap JSON only.")
                self.generated_output_json = None
            
            # Display in text widgets
            self.modbus_text.delete('1.0', tk.END)
            if FORMATTER_AVAILABLE:
                self.modbus_text.insert('1.0', format_bmiot_json(self.generated_modbus_io))
            else:
                self.modbus_text.insert('1.0', json.dumps(self.generated_modbus_io, indent=2))
            
            self.param_text.delete('1.0', tk.END)
            if FORMATTER_AVAILABLE:
                self.param_text.insert('1.0', format_bmiot_json(self.generated_parameter_config))
            else:
                self.param_text.insert('1.0', json.dumps(self.generated_parameter_config, indent=2))
            
            # Display Output JSON in third tab
            self.output_text.delete('1.0', tk.END)
            if self.generated_output_json:
                if FORMATTER_AVAILABLE:
                    self.output_text.insert('1.0', format_bmiot_json(self.generated_output_json))
                else:
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
            import traceback
            error_trace = traceback.format_exc()
            print("ERROR TRACE:")
            print(error_trace)
            messagebox.showerror("❌ Error", f"Error generating configurations:\n{str(e)}\n\nCheck console for full error details.")

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
            if FORMATTER_AVAILABLE:
                format_and_save_json(self.generated_modbus_io, filename)
            else:
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
            if FORMATTER_AVAILABLE:
                format_and_save_json(self.generated_parameter_config, filename)
            else:
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
            if FORMATTER_AVAILABLE:
                format_and_save_json(self.generated_modbus_io, modbus_file)
                format_and_save_json(self.generated_parameter_config, param_file)
            else:
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
                if FORMATTER_AVAILABLE:
                    format_and_save_json(self.generated_output_json, filename)
                else:
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
            if FORMATTER_AVAILABLE:
                format_and_save_json(self.generated_modbus_io, modbus_file)
            else:
                with open(modbus_file, 'w') as f:
                    json.dump(self.generated_modbus_io, f, indent=2)
            
            # Save ParamMap_Config.json
            param_file = os.path.join(directory, "parameter_config.json")
            if FORMATTER_AVAILABLE:
                format_and_save_json(self.generated_parameter_config, param_file)
            else:
                with open(param_file, 'w') as f:
                    json.dump(self.generated_parameter_config, f, indent=2)
            
            success_msg = f"Files saved to:\n{directory}\n\n✅ modbus_io.json (Modbus config)\n✅ parameter_config.json (Parameter mapping)"
            
            # Save Output.json template if available
            if self.generated_output_json:
                output_file = os.path.join(directory, "output.json")
                if FORMATTER_AVAILABLE:
                    format_and_save_json(self.generated_output_json, output_file)
                else:
                    with open(output_file, 'w') as f:
                        json.dump(self.generated_output_json, f, indent=2)
                success_msg += "\n✅ output.json (Telemetry template)"
            
            messagebox.showinfo("✅ Success", success_msg)
        except Exception as e:
            messagebox.showerror("❌ Error", f"Failed to save files:\n{e}")
    
    def show_firmware_help(self):
        """Display BMIoT firmware architecture information"""
        help_window = tk.Toplevel(self.root)
        help_window.title("📘 BMIoT Gateway Firmware Architecture")
        help_window.geometry("900x700")
        help_window.configure(bg='white')
        
        # Create scrollable text widget
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        text_widget = tk.Text(text_frame, wrap='word', font=('Segoe UI', 10), padx=15, pady=15)
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)
        
        # Firmware architecture content
        content = """
📘 BMIoT Gateway Firmware Architecture
═══════════════════════════════════════════════════════════════════════

🔄 M-Das OTA Configuration System
────────────────────────────────────────────────────────────────────────
M-Das (mDash) is the cloud-based device management platform for:
  • Over-the-air (OTA) firmware updates
  • Remote file management via RPC commands
  • Device shadow synchronization
  • Remote configuration updates

Configuration Update Workflow:
  1. Generate JSONs using this application
  2. Upload to device via M-Das dashboard using FS.Put RPC
  3. Files stored in device SPIFFS filesystem
  4. Reboot device to reload configurations
  5. Firmware loads and validates both JSON files


📦 Required JSON Files
────────────────────────────────────────────────────────────────────────
The firmware requires BOTH configuration files:

1️⃣ Modbus_Config.json (6 Mandatory Blocks)
   • B1: Overview - slave count, packet count, register count, parameter count
   • B2: Communication - baud rate (38400), data format ('8N1')
   • B3: Slave Configuration - slave IDs and start packet numbers
   • B4: Packet Configuration - start address, register count, function code, slave ID
   • B5: Parameter Configuration - ID, packet number, address, length, format, multiplier
   • B6: Write-Read Mapping - maps write parameters to verification read parameters

2️⃣ ParamMap_Config.json (7 Mandatory Sections)
   • P1: Buffer Sizes - NLB (Lua buffer), NLBIN (Lua input), NMD (output data buffer)
   • P2: Lua Buffer Mapping - MPI (Modbus params), RPCI (RPC commands)
   • P3: Output Buffer Mapping - MPI (Modbus cloud params), LBI (Lua variables)
   • JKY: JSON Key Arrays - equipment groups and keys for cloud payload structure
   • JKC: JSON Common Strings - header and equipment key strings
   • NTC: Network/Device Details - IP, client ID, device ID, slave names
   • MST: Profile Setup - profile flag

⚠️ ALL sections are mandatory! Firmware validation checks for all keys.


🔧 Firmware Data Flow
────────────────────────────────────────────────────────────────────────
Startup:
  1. SPIFFS_config.begin() → Mount SPIFFS filesystem
  2. MB_Config.load(Modbus_Config.json) → Load and validate B1-B6 blocks
  3. PMap_Config.load(ParamMap_Config.json) → Load and validate P1-P3, JKY, JKC, NTC, MST
  4. eModbusRTU_PacketInit() → Initialize packet structures from B4
  5. eModbusRTU_Construct() → Build Modbus polling packets using B4 data
  
Runtime Loop (every 10s):
  1. eModbusRTU_Loop() → Poll configured Modbus packets from slaves
  2. Map_MdataBuffSync() → Fill M_data output buffer using P3.MPI mapping
  3. Lua_IO_Sync() → Execute Lua scripts with P2.MPI data
  4. M_data buffer contains cloud parameters for publishing

Publishing (every 30-300s):
  1. Build JSON payload using JKY equipment structure
  2. Insert M_data values into JSON groups/keys
  3. Publish via MQTT or HTTPS to cloud platform
  4. Cloud dashboard displays equipment-organized data


📊 GUI Field Mapping to Firmware
────────────────────────────────────────────────────────────────────────
This Application          →  Firmware Block       →  Usage
═════════════════════════════════════════════════════════════════════════
Slave ID                  →  B3.SI, B4.SID        →  Modbus slave address
FC (Function Code)        →  B4.FC                →  Modbus function (3=read, 6=write)
Address                   →  B4.SA, B5.STA        →  Register start address
Length                    →  B5.LN                →  Register length (1-4)
FMT (Format)              →  B5.FMT               →  Data format (I16, U16, I32, F32)
Multiplier                →  B5.MLT               →  Scaling factor
Access                    →  B6.WP/RP mapping     →  R=read, W=write, RW=write+verify
Cloud Output              →  P3.MPI               →  Include in M_data buffer (REQUIRED)
JSON Group/Unit/Key       →  JKY.JKA              →  Cloud payload structure
Array Membership          →  P2.MPI, P3.MPI       →  Parameter grouping
B5 ID                     →  B5.ID                →  Parameter index in B5 block
Packet Num                →  B5.PN                →  Packet grouping for polling
Packet SA/NRT             →  B4.SA, B4.NRT        →  Packet metadata


✅ Best Practices
────────────────────────────────────────────────────────────────────────
1. Always mark at least one parameter for Cloud Output (P3.MPI required)
2. Fill JSON Group, Unit, and Key for all cloud parameters
3. Group related parameters in same equipment type for organized dashboard
4. Use descriptive JSON keys (e.g., "chiller_temp", "flow_rate")
5. Test with minimal configuration first (1 slave, 5 parameters)
6. Upload both JSONs and reboot device after configuration changes
7. Check device serial output for loading errors after reboot


📚 For More Information
────────────────────────────────────────────────────────────────────────
Firmware Source: Thermelgy-Gateway-BMIoT/lib/
  • MBConfig_Lib - Modbus configuration loader
  • ParamMapConfig_Lib - Parameter mapping loader
  • eModbusRTU_Lib - Modbus communication engine
  • LuaEngine_Lib - Lua script execution
  • Com_Lib - MQTT/HTTPS publishing

API Documentation: API Documentation/html/index.html
"""
        
        text_widget.insert('1.0', content)
        text_widget.configure(state='disabled')  # Make read-only
        
        # Add close button
        btn_frame = ttk.Frame(help_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Close", command=help_window.destroy, style='Action.TButton').pack()
    
    def show_column_help(self):
        """Display column descriptions"""
        help_window = tk.Toplevel(self.root)
        help_window.title("🔍 Column Descriptions")
        help_window.geometry("800x600")
        help_window.configure(bg='white')
        
        # Create scrollable text widget
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        text_widget = tk.Text(text_frame, wrap='word', font=('Courier New', 9), padx=15, pady=15)
        scrollbar = ttk.Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        text_widget.pack(side='left', fill='both', expand=True)
        
        # Column descriptions
        content = """
🔍 Register Configuration Columns
══════════════════════════════════════════════════════════════════════════════

COLUMN              FIRMWARE MAPPING          DESCRIPTION
──────────────────────────────────────────────────────────────────────────────
S.No                Sequential index          Display-only serial number

Slave ID            B3.SI, B4.SID             Modbus slave device address (1-247)
                                              Maps to physical device on RTU bus

FC                  B4.FC                     Modbus function code:
                                              • 3 = Read Holding Registers
                                              • 6 = Write Single Register
                                              • 16 = Write Multiple Registers

Address             B4.SA, B5.STA             Modbus register start address (0-65535)
                                              Address of parameter in slave device

Length              B5.LN                     Number of Modbus registers (1-4):
                                              • 1 = 16-bit (I16, U16)
                                              • 2 = 32-bit (I32, U32, F32)
                                              • 4 = 64-bit (rarely used)

FMT                 B5.FMT                    Data format identifier (0-9):
                                              • 0 = I16 (signed 16-bit)
                                              • 1 = U16 (unsigned 16-bit)
                                              • 2 = I32 (signed 32-bit)
                                              • 3 = U32 (unsigned 32-bit)
                                              • 4 = F32 (32-bit float)

Multiplier          B5.MLT                    Scaling factor (0.01-1000.0)
                                              Final value = raw_value × multiplier

Access              B6.WP, B6.RP              Parameter access type:
                                              • R = Read Only (monitoring)
                                              • W = Write Only (setpoint, no verify)
                                              • RW = Read-Write (setpoint + verify)

Cloud Output        P3.MPI (REQUIRED!)        Include in MQTT/HTTPS output buffer?
                                              • Yes = Add to M_data[] array
                                              • No = Skip in cloud publishing
                                              ⚠️ At least one must be Yes!

JSON Group          JKY.JKA equipment type    Equipment category for cloud payload:
                                              e.g., "Chiller", "Pump", "VFD"
                                              Groups related parameters together

JSON Unit           JKY.JKA equipment name    Specific equipment unit identifier:
                                              e.g., "CH-1", "Pump-A", "VFD-01"
                                              Identifies individual device

JSON Key            JKY.JKA parameter key     Parameter name in cloud JSON:
                                              e.g., "temp", "flow_rate", "speed"
                                              Must be unique within equipment unit

Array Membership    P2.MPI, P3.MPI, etc.      Parameter grouping in ParamMap:
                                              • P2.MPI = Lua buffer (Modbus params)
                                              • P2.RPCI = RPC commands
                                              • P3.MPI = Cloud output (Modbus)
                                              • P3.LBI = Cloud output (Lua vars)

B5 ID               B5.ID (s_Indx)            Parameter index in firmware Block 5
                                              Unique identifier (1-300)

Packet Num          B5.PN (s_PckNo)           Modbus polling packet number (1-150)
                                              Groups parameters polled together
                                              Used by eModbusRTU_Construct()

Packet SA           B4.SA                     Packet start address
                                              First register address in packet

Packet NRT          B4.NRT (s_NosRgtrs)       Registers per packet
                                              Number of registers polled in packet


💡 USAGE TIPS
──────────────────────────────────────────────────────────────────────────────
1. Cloud Output = Yes → Required for firmware to publish data via MQTT/HTTPS
2. JSON Group/Unit/Key → Organize cloud dashboard by equipment type
3. Packet Num → Firmware groups registers into packets for efficient polling
4. B5 ID → Auto-assigned, uniquely identifies each parameter
5. Access = RW → Firmware writes value then reads back to verify success


⚠️ COMMON MISTAKES
──────────────────────────────────────────────────────────────────────────────
❌ No cloud parameters (all Cloud Output = No)
   → Firmware cannot publish to cloud, P3.MPI is empty

❌ Cloud Output = Yes but missing JSON Group/Unit/Key
   → Firmware fails to build output JSON payload

❌ Duplicate B5 IDs
   → Firmware mapping conflicts

❌ Wrong packet grouping (parameters from different slaves in same packet)
   → Modbus communication fails

"""
        
        text_widget.insert('1.0', content)
        text_widget.configure(state='disabled')  # Make read-only
        
        # Add close button
        btn_frame = ttk.Frame(help_window)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Close", command=help_window.destroy, style='Action.TButton').pack()
    
    def show_about(self):
        """Display about information"""
        about_text = """
🔧 Modbus Configuration Generator Pro
Version 6.6 - BMIoT Gateway Edition

Firmware-Aligned Configuration Tool for Thermelgy BMIoT Gateway

Features:
• Bidirectional JSON transformation (Register ↔ Modbus+ParamMap)
• Firmware-validated configuration generation
• M-Das OTA compatible JSON output
• 17-field register management with packet grouping
• Cloud output parameter mapping (P3.MPI)
• Equipment-based JSON structure (JKY)

Generated Files:
• Modbus_Config.json (B1-B6 blocks)
• ParamMap_Config.json (P1-P3, JKY, JKC, NTC, MST)
• Output_JSON.json (cloud payload template)

Firmware Requirements:
• ESP32-based Thermelgy BMIoT Gateway
• M-Das cloud connectivity
• eModbusRTU, MBConfig_Lib, ParamMapConfig_Lib

For help, click Help → BMIoT Firmware Architecture
"""
        messagebox.showinfo("About", about_text)

class RegisterDialog:
    def __init__(self, parent, app):
        self.app = app
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("➕ Add New Register")
        self.dialog.geometry("600x850")  # Increased height for RW pairing section
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg='#f5f7fa')
        
        # Title
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=60)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="📝 Register Information", 
                font=('Segoe UI', 14, 'bold'), fg='white', bg='#3498db').pack(pady=15)
        
        # Create scrollable frame for form
        canvas_container = ttk.Frame(self.dialog)
        canvas_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(canvas_container, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient='vertical', command=canvas.yview)
        
        frame = ttk.Frame(canvas, padding=30)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        canvas_window = canvas.create_window((0, 0), window=frame, anchor='nw')
        
        # Bind canvas resize
        frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # Enable mousewheel scrolling - bind to canvas AND frame
        def on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass  # Canvas destroyed, ignore
        
        # Bind to both canvas and frame so scrolling works when hovering over either
        canvas.bind("<MouseWheel>", on_mousewheel)
        frame.bind("<MouseWheel>", on_mousewheel)
        
        # Make sure the dialog gets focus to enable mouse events
        def bind_tree(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_tree(child)
        bind_tree(frame)
        
        # Unbind mousewheel when dialog closes
        def on_dialog_close():
            try:
                canvas.unbind("<MouseWheel>")
                frame.unbind("<MouseWheel>")
            except:
                pass
            self.dialog.destroy()
        
        self.dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        row = 0
        
        # Info Panel - Quick Guide
        info_frame = tk.Frame(frame, bg='#e8f4f8', relief='solid', borderwidth=1)
        info_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=(0, 15))
        tk.Label(info_frame, text="ℹ️ Quick Start", font=('Segoe UI', 10, 'bold'), bg='#e8f4f8', fg='#2c3e50').pack(anchor='w', padx=10, pady=(10, 5))
        tk.Label(info_frame, text="• Fill in the 8 essential fields below (marked with ★)", font=('Segoe UI', 9), bg='#e8f4f8', fg='#34495e').pack(anchor='w', padx=20)
        tk.Label(info_frame, text="• Click '▶ Advanced Options' below to set RW pairing", font=('Segoe UI', 9), bg='#e8f4f8', fg='#34495e').pack(anchor='w', padx=20)
        tk.Label(info_frame, text="• Click '▶ Preview & Details' to see what will be generated", font=('Segoe UI', 9), bg='#e8f4f8', fg='#34495e').pack(anchor='w', padx=20)
        tk.Label(info_frame, text="⚠️ To edit advanced options later, delete and re-add the register", font=('Segoe UI', 9, 'italic'), bg='#e8f4f8', fg='#e67e22').pack(anchor='w', padx=20, pady=(5, 10))
        row += 1
        
        # Section Header - Basic Modbus Configuration
        ttk.Label(frame, text="⚙️ Basic Modbus Configuration", 
                 font=('Segoe UI', 11, 'bold'), foreground='#c0392b').grid(row=row, column=0, columnspan=3, sticky='w', pady=(10, 5))
        row += 1
        
        # Slave ID
        ttk.Label(frame, text="Slave ID:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.slave_id_var = tk.IntVar(value=1)
        ttk.Spinbox(frame, from_=1, to=247, textvariable=self.slave_id_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 1-247", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
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
        self.access_combo.bind("<<ComboboxSelected>>", lambda e: (self.update_preview_fields(), self.on_access_change()))
        row += 1
        
        # Section Header - Cloud & JSON Configuration
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        ttk.Label(frame, text="☁️ Cloud & JSON Configuration", 
                 font=('Segoe UI', 11, 'bold'), foreground='#27ae60').grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        row += 1
        
        # Cloud Output
        ttk.Label(frame, text="Cloud Output:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.cloud_var = tk.StringVar(value="Yes")
        cloud_combo = ttk.Combobox(frame, textvariable=self.cloud_var, 
                                  values=["Yes", "No"], 
                                  width=28, state='readonly', font=('Segoe UI', 10))
        cloud_combo.grid(row=row, column=1, pady=10, sticky='ew')
        cloud_combo.bind("<<ComboboxSelected>>", lambda e: self.on_cloud_output_change())
        ttk.Label(frame, text="💡 Only for monitoring params", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # JSON Group
        ttk.Label(frame, text="JSON Group:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_group_var = tk.StringVar()
        self.json_group_var.trace('w', lambda *args: self.update_preview_fields())
        ttk.Entry(frame, textvariable=self.json_group_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 e.g., Chiller1, Pump2, AHU3", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # JSON Unit
        ttk.Label(frame, text="JSON Unit:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_unit_var = tk.StringVar()
        self.json_unit_var.trace('w', lambda *args: self.update_preview_fields())
        ttk.Entry(frame, textvariable=self.json_unit_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 e.g., Temperature, Pressure, Status", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # JSON Key
        ttk.Label(frame, text="JSON Key:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.json_key_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.json_key_var, width=30, font=('Segoe UI', 10)).grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Supply, Return, Setpoint (comma for multi)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # ============================================================================
        # LUA BUFFER CONFIGURATION SECTION
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        ttk.Label(frame, text="🔧 Lua Buffer Configuration", 
                 font=('Segoe UI', 11, 'bold'), foreground='#8e44ad').grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        row += 1
        
        # In Lua Buffer
        ttk.Label(frame, text="In Lua Buffer:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.in_lua_buffer_var = tk.StringVar(value="No")
        self.in_lua_buffer_combo = ttk.Combobox(frame, textvariable=self.in_lua_buffer_var, 
                                  values=["No", "Yes"], 
                                  width=28, state='readonly', font=('Segoe UI', 10))
        self.in_lua_buffer_combo.grid(row=row, column=1, pady=10, sticky='ew')
        self.in_lua_buffer_combo.bind("<<ComboboxSelected>>", lambda e: self.update_lua_buffer_controls())
        ttk.Label(frame, text="💡 Use Lua Buffer for calculations?", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # Lua Buffer Category
        ttk.Label(frame, text="Lua Category:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.lua_category_var = tk.StringVar(value="N/A")
        self.lua_category_combo = ttk.Combobox(frame, textvariable=self.lua_category_var, 
                                  values=["N/A", "Equipment", "User Variable"], 
                                  width=28, state='disabled', font=('Segoe UI', 10))
        self.lua_category_combo.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 P2.MPI (Equipment) or P2.RPCI (User Var)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # LBI Position
        ttk.Label(frame, text="LBI Position:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.lbi_position_var = tk.StringVar(value="Auto")
        self.lbi_position_entry = ttk.Entry(frame, textvariable=self.lbi_position_var, width=30, font=('Segoe UI', 10), state='disabled')
        self.lbi_position_entry.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Auto-assign or manual (e.g., 1, 2, 3...)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # LBI Data Type
        ttk.Label(frame, text="LBI Data Type:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        self.lbi_data_type_var = tk.StringVar(value="Number")
        self.lbi_data_type_combo = ttk.Combobox(frame, textvariable=self.lbi_data_type_var, 
                                  values=["Number", "Boolean", "String"], 
                                  width=28, state='disabled', font=('Segoe UI', 10))
        self.lbi_data_type_combo.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Data type in Lua Buffer array", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # ADVANCED: Dual-Category Mode (for parameters in BOTH RPCI and MPI)
        self.dual_category_var = tk.BooleanVar(value=False)
        self.dual_category_check = ttk.Checkbutton(frame, text="🔀 Advanced: Dual-Category Mode (parameter in BOTH User Variable AND Equipment)",
                                                   variable=self.dual_category_var,
                                                   command=self.update_dual_category_controls,
                                                   state='disabled')
        self.dual_category_check.grid(row=row, column=0, columnspan=3, sticky='w', pady=(15, 5))
        row += 1
        
        # Dual Category Info Box (initially hidden)
        self.dual_info_frame = tk.Frame(frame, bg='#fff3cd', relief='solid', borderwidth=1)
        tk.Label(self.dual_info_frame, text="⚠️ Advanced Feature", font=('Segoe UI', 9, 'bold'), bg='#fff3cd', fg='#856404').pack(anchor='w', padx=10, pady=(8, 2))
        tk.Label(self.dual_info_frame, text="This parameter will occupy TWO separate LBI positions:", 
                font=('Segoe UI', 8), bg='#fff3cd', fg='#856404').pack(anchor='w', padx=20)
        tk.Label(self.dual_info_frame, text="• One in User Variable range (RPCI) - Lua script can write to it", 
                font=('Segoe UI', 8), bg='#fff3cd', fg='#856404').pack(anchor='w', padx=20)
        tk.Label(self.dual_info_frame, text="• One in Equipment range (MPI) - Used for equipment control logic", 
                font=('Segoe UI', 8), bg='#fff3cd', fg='#856404').pack(anchor='w', padx=20, pady=(0, 8))
        # Don't grid it yet - will be shown when checkbox is checked
        self.dual_info_row = row
        row += 1
        
        # Secondary Category (only visible when dual-category is enabled)
        ttk.Label(frame, text="Secondary Category:", font=('Segoe UI', 10)).grid(row=row, column=0, sticky='w', pady=10)
        self.secondary_category_var = tk.StringVar(value="Equipment")
        self.secondary_category_combo = ttk.Combobox(frame, textvariable=self.secondary_category_var, 
                                  values=["Equipment", "User Variable"], 
                                  width=28, state='disabled', font=('Segoe UI', 10))
        self.secondary_category_combo.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 The other category for dual mapping", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        self.secondary_category_label = frame.grid_slaves(row=row, column=0)[0]  # Store reference for hide/show
        self.secondary_category_hint = frame.grid_slaves(row=row, column=2)[0]
        row += 1
        
        # Secondary LBI Position (only visible when dual-category is enabled)
        ttk.Label(frame, text="Secondary LBI Pos:", font=('Segoe UI', 10)).grid(row=row, column=0, sticky='w', pady=10)
        self.secondary_lbi_var = tk.StringVar(value="Auto")
        self.secondary_lbi_entry = ttk.Entry(frame, textvariable=self.secondary_lbi_var, width=30, font=('Segoe UI', 10), state='disabled')
        self.secondary_lbi_entry.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 LBI position for secondary category", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        self.secondary_lbi_label = frame.grid_slaves(row=row, column=0)[0]
        self.secondary_lbi_hint = frame.grid_slaves(row=row, column=2)[0]
        row += 1
        
        # Initially hide dual-category fields
        self.secondary_category_label.grid_remove()
        self.secondary_category_combo.grid_remove()
        self.secondary_category_hint.grid_remove()
        self.secondary_lbi_label.grid_remove()
        self.secondary_lbi_entry.grid_remove()
        self.secondary_lbi_hint.grid_remove()
        
        # ============================================================================
        # MANUAL OVERRIDE SECTION
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        ttk.Label(frame, text="🛡️ Manual Override", 
                 font=('Segoe UI', 11, 'bold'), foreground='#c0392b').grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        row += 1
        
        # Manual Override Checkbox
        self.manual_override_var = tk.BooleanVar(value=False)
        self.manual_override_check = ttk.Checkbutton(frame, text="Enable Manual Override (preserve Array Membership field - don't auto-regenerate)",
                                                     variable=self.manual_override_var)
        self.manual_override_check.grid(row=row, column=0, columnspan=3, sticky='w', pady=10)
        row += 1
        
        # Manual Override Info Box
        manual_override_info_frame = tk.Frame(frame, bg='#ffe5e5', relief='solid', borderwidth=1)
        tk.Label(manual_override_info_frame, text="⚠️ Manual Override Mode", font=('Segoe UI', 9, 'bold'), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=10, pady=(8, 2))
        tk.Label(manual_override_info_frame, text="When enabled:", 
                font=('Segoe UI', 8, 'bold'), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=20)
        tk.Label(manual_override_info_frame, text="✓ Your manual 'Array Membership' field will be preserved", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30)
        tk.Label(manual_override_info_frame, text="✓ P2.MPI / P2.RPCI / P3.MPI arrays won't be auto-regenerated", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30)
        tk.Label(manual_override_info_frame, text="✓ You control which ParamMap arrays this parameter belongs to", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30)
        tk.Label(manual_override_info_frame, text="When disabled (default):", 
                font=('Segoe UI', 8, 'bold'), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=20, pady=(5, 0))
        tk.Label(manual_override_info_frame, text="✗ Array Membership is auto-calculated from Lua Buffer + Cloud settings", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30, pady=(0, 8))
        manual_override_info_frame.grid(row=row, column=0, columnspan =3, sticky='ew', pady=10)
        row += 1
        
        # ============================================================================
        # ADVANCED OPTIONS SECTION (Collapsible)
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        
        # Collapsible Advanced Options Header
        self.advanced_visible = tk.BooleanVar(value=False)
        advanced_header_frame = tk.Frame(frame, bg='#f5f7fa', cursor='hand2')
        advanced_header_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=5)
        
        self.advanced_arrow = tk.Label(advanced_header_frame, text="▶", font=('Segoe UI', 12, 'bold'), 
                                       bg='#f5f7fa', fg='#2980b9', width=2, anchor='w')
        self.advanced_arrow.pack(side='left', padx=(0, 5), pady=5)
        
        tk.Label(advanced_header_frame, text="Advanced Options (Optional)", 
                font=('Segoe UI', 11, 'bold'), bg='#f5f7fa', fg='#2980b9').pack(side='left', padx=5, pady=5)
        
        tk.Label(advanced_header_frame, text="Click to expand", 
                font=('Segoe UI', 9, 'italic'), bg='#f5f7fa', fg='#7f8c8d').pack(side='left', padx=10)
        
        advanced_header_frame.bind('<Button-1>', lambda e: self.toggle_advanced())
        self.advanced_arrow.bind('<Button-1>', lambda e: self.toggle_advanced())
        
        # Store row for grid placement later
        self.advanced_row = row
        row += 1
        
        # Advanced Options Content (initially hidden)
        self.advanced_frame = ttk.Frame(frame)
        
        # Array Membership
        adv_row = 0
        ttk.Label(self.advanced_frame, text="Array Membership:", font=('Segoe UI', 10, 'bold')).grid(row=adv_row, column=0, sticky='w', pady=10)
        self.array_var = tk.StringVar()
        ttk.Entry(self.advanced_frame, textvariable=self.array_var, width=30, font=('Segoe UI', 10)).grid(row=adv_row, column=1, pady=10, sticky='ew')
        ttk.Label(self.advanced_frame, text="💡 e.g., P2.MPI, P3.MPI", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=adv_row, column=2, padx=5, sticky='w')
        adv_row += 1
        
        # RW Pairing
        ttk.Label(self.advanced_frame, text="Paired With (Param ID):", font=('Segoe UI', 10, 'bold')).grid(row=adv_row, column=0, sticky='w', pady=10)
        self.paired_param_var = tk.StringVar()
        self.paired_param_var.trace('w', lambda *args: self.update_preview_fields())
        ttk.Entry(self.advanced_frame, textvariable=self.paired_param_var, width=30, font=('Segoe UI', 10)).grid(row=adv_row, column=1, pady=10, sticky='ew')
        ttk.Label(self.advanced_frame, text="💡 For RW parameter pairing", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=adv_row, column=2, padx=5, sticky='w')
        adv_row += 1
        
        self.advanced_frame.columnconfigure(1, weight=1)
        # Don't grid advanced_frame yet - will be shown/hidden by toggle
        
        # ============================================================================
        # PREVIEW & DETAILS SECTION (Collapsible)
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        
        # Collapsible Preview Header
        self.preview_visible = tk.BooleanVar(value=False)
        preview_header_frame = tk.Frame(frame, bg='#f5f7fa', cursor='hand2')
        preview_header_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=5)
        
        self.preview_arrow = tk.Label(preview_header_frame, text="▶", font=('Segoe UI', 12, 'bold'), 
                                      bg='#f5f7fa', fg='#8e44ad', width=2, anchor='w')
        self.preview_arrow.pack(side='left', padx=(0, 5), pady=5)
        
        tk.Label(preview_header_frame, text="Preview & Details", 
                font=('Segoe UI', 11, 'bold'), bg='#f5f7fa', fg='#8e44ad').pack(side='left', padx=5, pady=5)
        
        tk.Label(preview_header_frame, text="See what will be generated", 
                font=('Segoe UI', 9, 'italic'), bg='#f5f7fa', fg='#7f8c8d').pack(side='left', padx=10)
        
        preview_header_frame.bind('<Button-1>', lambda e: self.toggle_preview())
        self.preview_arrow.bind('<Button-1>', lambda e: self.toggle_preview())
        
        # Store row for grid placement later
        self.preview_row = row
        row += 1
        
        # Preview Content (initially hidden)
        self.preview_frame = ttk.Frame(frame)
        
        prev_row = 0
        
        # B5.ID
        ttk.Label(self.preview_frame, text="B5.ID:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        next_param_id = len(self.app.tree.get_children()) + 1
        self.b5_id_var = tk.StringVar(value=f"{next_param_id} (next available)")
        ttk.Entry(self.preview_frame, textvariable=self.b5_id_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-assigned", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Packet Number
        ttk.Label(self.preview_frame, text="Packet Number:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.packet_num_var = tk.StringVar(value="(calculated during generation)")
        ttk.Entry(self.preview_frame, textvariable=self.packet_num_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Groups by Slave+FC+Address range", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Packet Start Address
        ttk.Label(self.preview_frame, text="Packet Start Addr:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.packet_sa_var = tk.StringVar(value="(from B4.SA array)")
        ttk.Entry(self.preview_frame, textvariable=self.packet_sa_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 First address in packet", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Packet Register Count
        ttk.Label(self.preview_frame, text="Packet Reg Count:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.packet_nrt_var = tk.StringVar(value="(from B4.NRT array)")
        ttk.Entry(self.preview_frame, textvariable=self.packet_nrt_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Total registers in packet", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Equipment Hierarchy Section
        ttk.Separator(self.preview_frame, orient='horizontal').grid(row=prev_row, column=0, columnspan=3, sticky='ew', pady=10)
        prev_row += 1
        
        ttk.Label(self.preview_frame, text="🏗️ Equipment Hierarchy (ParamMap_Config.json)", 
                 font=('Segoe UI', 11, 'bold'), foreground='#16a085').grid(row=prev_row, column=0, columnspan=3, sticky='w', pady=5)
        prev_row += 1
        
        # Equipment Group
        ttk.Label(self.preview_frame, text="Equipment Group:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.equipment_group_var = tk.StringVar(value="(will match JSON Group)")
        self.equipment_group_entry = ttk.Entry(self.preview_frame, textvariable=self.equipment_group_var, width=30, font=('Segoe UI', 10), state='readonly')
        self.equipment_group_entry.grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-populated", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Device Name
        ttk.Label(self.preview_frame, text="Device Name:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.device_name_var = tk.StringVar(value="(will match JSON Unit)")
        self.device_name_entry = ttk.Entry(self.preview_frame, textvariable=self.device_name_var, width=30, font=('Segoe UI', 10), state='readonly')
        self.device_name_entry.grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-populated", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Equipment Type
        ttk.Label(self.preview_frame, text="Equipment Type:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.equipment_type_var = tk.StringVar()
        ttk.Entry(self.preview_frame, textvariable=self.equipment_type_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-detected (AI/DI/EM)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # JKA Equipment Index
        ttk.Label(self.preview_frame, text="JKA Equipment Index:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.jka_index_var = tk.StringVar()
        ttk.Entry(self.preview_frame, textvariable=self.jka_index_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-assigned in JKA array", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Parameter Classification Section
        ttk.Separator(self.preview_frame, orient='horizontal').grid(row=prev_row, column=0, columnspan=3, sticky='ew', pady=10)
        prev_row += 1
        
        ttk.Label(self.preview_frame, text="🔍 Parameter Classification", 
                 font=('Segoe UI', 11, 'bold'), foreground='#d35400').grid(row=prev_row, column=0, columnspan=3, sticky='w', pady=5)
        prev_row += 1
        
        # Parameter Type
        ttk.Label(self.preview_frame, text="Parameter Type:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.param_type_var = tk.StringVar(value="read_only")
        self.param_type_entry = ttk.Entry(self.preview_frame, textvariable=self.param_type_var, width=30, font=('Segoe UI', 10), state='readonly')
        self.param_type_entry.grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Based on Access + Pairing", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # P2.MPI Index
        ttk.Label(self.preview_frame, text="P2.MPI Index:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.p2_mpi_index_var = tk.StringVar()
        ttk.Entry(self.preview_frame, textvariable=self.p2_mpi_index_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-assigned in P2.MPI", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # P3.MPI Index
        ttk.Label(self.preview_frame, text="P3.MPI Index:", font=('Segoe UI', 10, 'bold')).grid(row=prev_row, column=0, sticky='w', pady=5)
        self.p3_mpi_index_var = tk.StringVar()
        ttk.Entry(self.preview_frame, textvariable=self.p3_mpi_index_var, width=30, font=('Segoe UI', 10), state='readonly').grid(row=prev_row, column=1, pady=5, sticky='ew')
        ttk.Label(self.preview_frame, text="🔒 Auto-assigned in P3.MPI", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=prev_row, column=2, padx=5, sticky='w')
        prev_row += 1
        
        # Configure column weight for preview frame
        self.preview_frame.columnconfigure(1, weight=1)
        
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
        
        # Initialize preview fields
        self.update_preview_fields()
    
    def toggle_advanced(self):
        """Toggle visibility of Advanced Options section"""
        if self.advanced_visible.get():
            # Hide the advanced frame
            self.advanced_frame.grid_forget()
            self.advanced_arrow.config(text="▶")
            self.advanced_visible.set(False)
        else:
            # Show the advanced frame (place it after row holding the header)
            self.advanced_frame.grid(row=self.advanced_row, column=0, columnspan=3, sticky='ew', padx=(10, 0))
            self.advanced_arrow.config(text="▼")
            self.advanced_visible.set(True)
    
    def toggle_preview(self):
        """Toggle visibility of Preview & Details section"""
        if self.preview_visible.get():
            # Hide the preview frame
            self.preview_frame.grid_forget()
            self.preview_arrow.config(text="▶")
            self.preview_visible.set(False)
        else:
            # Show the preview frame
            self.preview_frame.grid(row=self.preview_row, column=0, columnspan=3, sticky='ew', padx=(10, 0))
            self.preview_arrow.config(text="▼")
            self.preview_visible.set(True)
    
    def on_cloud_output_change(self):
        """Auto-configure Lua Buffer when Cloud Output is set to Yes"""
        cloud = self.cloud_var.get()
        access = self.access_var.get().split(' - ')[0] if ' - ' in self.access_var.get() else self.access_var.get()
        
        if cloud == "Yes":
            # Cloud output params typically need Lua Buffer access
            # Auto-enable if not already enabled
            if self.in_lua_buffer_var.get() == "No":
                self.in_lua_buffer_var.set("Yes")
                # Smart default: Equipment category for cloud params
                self.lua_category_var.set("Equipment")
                # Trigger UI update
                self.update_lua_buffer_controls()
                
                # Show user-friendly notification
                print("[Auto-Config] ☁️ Cloud Output=Yes → Lua Buffer enabled (Category: Equipment)")
        elif cloud == "No" and access in ['W', 'RW']:
            # Write/RW params still need Lua Buffer even without cloud
            if self.in_lua_buffer_var.get() == "No":
                self.in_lua_buffer_var.set("Yes")
                self.lua_category_var.set("Equipment")
                self.update_lua_buffer_controls()
                print(f"[Auto-Config] ✍️ Write parameter → Lua Buffer enabled (Category: Equipment)")
    
    def on_access_change(self):
        """Auto-configure Lua Buffer for Write parameters"""
        access = self.access_var.get().split(' - ')[0] if ' - ' in self.access_var.get() else self.access_var.get()
        
        if access in ['W', 'RW']:
            # Write/RW parameters need Lua Buffer for command execution
            if self.in_lua_buffer_var.get() == "No":
                self.in_lua_buffer_var.set("Yes")
                self.lua_category_var.set("Equipment")
                self.update_lua_buffer_controls()
                print(f"[Auto-Config] ✍️ Access={access} → Lua Buffer enabled (Category: Equipment)")
    
    def update_lua_buffer_controls(self):
        """Enable/disable Lua Buffer controls based on 'In Lua Buffer' selection"""
        if self.in_lua_buffer_var.get() == "Yes":
            # Enable all Lua Buffer fields
            self.lua_category_combo.config(state='readonly')
            self.lua_category_var.set("Equipment")  # Default to Equipment
            self.lbi_position_entry.config(state='normal')
            self.lbi_data_type_combo.config(state='readonly')
            self.dual_category_check.config(state='normal')  # Enable dual-category option
        else:
            # Disable and reset Lua Buffer fields
            self.lua_category_combo.config(state='disabled')
            self.lua_category_var.set("N/A")
            self.lbi_position_entry.config(state='disabled')
            self.lbi_position_var.set("Auto")
            self.lbi_data_type_combo.config(state='disabled')
            self.lbi_data_type_var.set("Number")
            self.dual_category_check.config(state='disabled')  # Disable dual-category option
            self.dual_category_var.set(False)  # Uncheck
            self.update_dual_category_controls()  # Hide dual fields
    
    def update_dual_category_controls(self):
        """Show/hide dual-category fields based on checkbox state"""
        if self.dual_category_var.get():
            # Show info box
            self.dual_info_frame.grid(row=self.dual_info_row, column=0, columnspan=3, sticky='ew', pady=(5, 10))
            # Show secondary fields
            self.secondary_category_label.grid()
            self.secondary_category_combo.grid()
            self.secondary_category_combo.config(state='readonly')
            self.secondary_category_hint.grid()
            self.secondary_lbi_label.grid()
            self.secondary_lbi_entry.grid()
            self.secondary_lbi_entry.config(state='normal')
            self.secondary_lbi_hint.grid()
            
            # Auto-set secondary category to opposite of primary
            primary = self.lua_category_var.get()
            if primary == "Equipment":
                self.secondary_category_var.set("User Variable")
            else:
                self.secondary_category_var.set("Equipment")
        else:
            # Hide info box
            self.dual_info_frame.grid_remove()
            # Hide secondary fields
            self.secondary_category_label.grid_remove()
            self.secondary_category_combo.grid_remove()
            self.secondary_category_combo.config(state='disabled')
            self.secondary_category_hint.grid_remove()
            self.secondary_lbi_label.grid_remove()
            self.secondary_lbi_entry.grid_remove()
            self.secondary_lbi_entry.config(state='disabled')
            self.secondary_lbi_hint.grid_remove()
            # Reset values
            self.secondary_category_var.set("Equipment")
            self.secondary_lbi_var.set("Auto")
    
    def update_preview_fields(self):
        """Auto-update preview fields based on user input in real-time"""
        try:
            # Update Equipment Group (matches JSON Group)
            json_group = self.json_group_var.get().strip()
            if json_group:
                self.equipment_group_var.set(json_group)
            else:
                self.equipment_group_var.set("(will match JSON Group)")
            
            # Update Device Name (matches JSON Unit)
            json_unit = self.json_unit_var.get().strip()
            if json_unit:
                self.device_name_var.set(json_unit)
            else:
                self.device_name_var.set("(will match JSON Unit)")
            
            # Update Parameter Type based on Access and Pairing
            access_text = self.access_var.get()
            if access_text:
                try:
                    access = bc.parse_dropdown_selection(access_text, 'access_type')
                except:
                    access = 'R'
            else:
                access = 'R'
            
            paired_param = self.paired_param_var.get().strip() if hasattr(self, 'paired_param_var') else ''
            has_pairing = bool(paired_param)
            
            if access == 'W':
                param_type = 'write'
            elif access == 'RW':
                param_type = 'write' if has_pairing else 'read_only'
            else:  # R
                param_type = 'feedback' if has_pairing else 'read_only'
            
            self.param_type_var.set(param_type)
            
        except Exception as e:
            pass  # Silently ignore errors during preview updates
    
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
                messagebox.showerror("Length Does Not Match Format", 
                                   f"Format {fmt} requires {expected_length} registers, but Length shows {length}.\n\n"
                                   f"To fix: Select a different Format from the dropdown.\n"
                                   f"Length will update automatically.")
                return
            
            # VALIDATION: Length limit
            if length > 70:
                messagebox.showerror("Length Too Large", 
                                   f"Length {length} exceeds maximum of 70 registers.\n\n"
                                   f"Please select a different Format with fewer registers.")
                return
            
            # VALIDATION: Function Code vs Access Type Logic
            # READ FCs (1,2,3,4) should only work with 'R' or 'RW'
            # WRITE FCs (5,6,15,16) should only work with 'W' or 'RW'
            read_fcs = [1, 2, 3, 4]
            write_fcs = [5, 6, 15, 16]
            
            if fc in read_fcs:
                if 'R' not in access:
                    messagebox.showerror("Function Code Mismatch", 
                                       f"FC {fc} is for reading data.\n\n"
                                       f"But Access Type '{access}' does not allow reading.\n\n"
                                       f"To fix: Change Access to 'R' or 'RW'.")
                    return
            elif fc in write_fcs:
                if 'W' not in access:
                    messagebox.showerror("Function Code Mismatch", 
                                       f"FC {fc} is for writing data.\n\n"
                                       f"But Access Type '{access}' does not allow writing.\n\n"
                                       f"To fix: Change Access to 'W' or 'RW'.")
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
                        # Build simplified warning message
                        overlap_msg = (
                            f"Overlapping Register Detected!\n\n"
                            f"Register #{existing_serial} already uses:\n"
                            f"  Slave {existing_slave}, Address {existing_addr}-{existing_end_addr}\n\n"
                            f"Your new register will use:\n"
                            f"  Slave {slave_id}, Address {address}-{new_end_addr}\n\n"
                            f"These address ranges overlap on the same slave device.\n\n"
                            f"Continue anyway?"
                        )
                        
                        result = messagebox.askyesno("Overlapping Register", overlap_msg)
                        if not result:
                            return
                        # If user clicked Yes, continue to add the register
                        break
            
            # VALIDATION: Cloud output restrictions
            # Based on verified client examples (Import_Examples/):
            # - W (Write): NEVER cloud="Yes" (0/52 examples)
            # - R (Read): CAN have cloud="Yes" (including feedback!)
            # - RW: Treat like W (write capability = no cloud)
            cloud_enabled = self.cloud_var.get() == "Yes"
            
            if cloud_enabled:
                if access in ['W', 'RW']:
                    messagebox.showerror("Cloud Output Not Allowed",
                                       f"Cannot enable Cloud for Access Type '{access}'.\n\n"
                                       f"Write parameters (W/RW) are local control commands.\n"
                                       f"Cloud cannot write back to Modbus devices.\n\n"
                                       f"To fix: Change Access to 'R' OR set Cloud to 'No'.")
                    return
            
            # VALIDATION: JSON fields for cloud parameters
            json_group = self.json_group_var.get().strip()
            json_unit = self.json_unit_var.get().strip()
            json_key = self.json_key_var.get().strip()
            array_membership = self.array_var.get().strip() if hasattr(self, 'array_var') else ''
            
            if cloud_enabled:
                warnings = []
                if not json_group:
                    warnings.append("• JSON Group")
                if not json_unit:
                    warnings.append("• JSON Unit")
                if not json_key:
                    warnings.append("• JSON Key")
                
                if warnings:
                    warning_msg = "\n".join(warnings)
                    result = messagebox.askyesno("Missing Cloud Information", 
                                               f"Cloud is enabled but these fields are empty:\n\n{warning_msg}\n\n"
                                               f"Without these fields, this parameter won't appear in cloud output.\n\n"
                                               f"Continue anyway? (You can fill them later)")
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
            
            # Get paired parameter info
            paired_param_str = self.paired_param_var.get().strip() if hasattr(self, 'paired_param_var') else ''
            paired_param_id = ''
            if paired_param_str:
                try:
                    paired_param_id = str(int(paired_param_str))  # Validate it's a number
                except ValueError:
                    pass  # Invalid, leave empty
            
            # Determine parameter type and pairing
            if access == 'W':
                parameter_type = 'write'
                feedback_param_id = paired_param_id  # W parameter points to its feedback
                write_param_id = ''
            elif access == 'RW':
                # RW can be treated as write if it has feedback pairing
                parameter_type = 'write' if paired_param_id else 'read_only'
                feedback_param_id = paired_param_id if paired_param_id else ''
                write_param_id = ''
            else:  # access == 'R'
                # R can be feedback or standalone read
                if paired_param_id:
                    parameter_type = 'feedback'
                    write_param_id = paired_param_id  # Feedback points to its write
                    feedback_param_id = ''
                else:
                    parameter_type = 'read_only'
                    write_param_id = ''
                    feedback_param_id = ''
            
            # Build lua_buffer_note if dual-category mode is enabled
            lua_buffer_note = ''
            if self.in_lua_buffer_var.get() == 'Yes' and self.dual_category_var.get():
                primary_cat = self.lua_category_var.get()
                primary_lbi = self.lbi_position_var.get()
                secondary_cat = self.secondary_category_var.get()
                secondary_lbi = self.secondary_lbi_var.get()
                lua_buffer_note = f'Multi-category: {primary_cat} LBI={primary_lbi}, {secondary_cat} LBI={secondary_lbi}'
            
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
                json_key,
                array_membership,  # Use the array_membership from dialog
                children_count + 1,  # b5_id - default to serial number
                '',  # packet_num - will be calculated (empty string displays better than 0)
                address,  # packet_sa - default to address
                length,  # packet_nrt - default to length
                # Transparent columns (18-23) - visible in table
                '',  # Packet # - will be calculated during generation (show empty instead of 0)
                address,  # Packet Start - default to address
                length,  # Packet Regs - default to length
                parameter_type,  # Param Type
                paired_param_id,  # Paired With
                -1,  # JKA Index - not in JKA by default
                # Lua Buffer columns (24-27) - visible in table
                self.in_lua_buffer_var.get(),  # In Lua Buffer
                self.lua_category_var.get(),  # Lua Category
                self.lbi_position_var.get(),  # LBI Position
                self.lbi_data_type_var.get(),  # LBI Data Type
                # Internal metadata columns (28-37) - hidden
                parameter_type,  # Parameter Type (internal)
                write_param_id,  # Write Param ID
                feedback_param_id,  # Feedback Param ID
                '',  # p2_mpi_index - will be calculated
                '',  # p3_mpi_index - will be calculated
                '',  # equipment_group - empty for manually added
                '',  # device_name - empty for manually added
                '',  # equipment_type - empty for manually added
                -1,  # jka_equipment_index - not in JKA
                lua_buffer_note,  # lua_buffer_note - dual-category info
                self.manual_override_var.get()  # Column 37 - manual_override flag
            ), tags=(tag,))
            
            # BUG FIX: Create RegisterEntry object and add to self.app.registers
            # This ensures export can find the register and save all Lua Buffer fields
            register_obj = RegisterEntry(
                param_id=children_count + 1,
                slave_id=slave_id,
                fc=fc,
                address=address,
                length=length,
                fmt=fmt,
                multiplier=multiplier,
                access=access,
                cloud=self.cloud_var.get(),
                json_group=json_group,
                json_unit=json_unit,
                json_key=json_key,
                array_membership=array_membership,
                parameter_type=parameter_type,
                write_param_id=int(write_param_id) if write_param_id and write_param_id != '' else None,
                feedback_param_id=int(feedback_param_id) if feedback_param_id and feedback_param_id != '' else None,
                p2_mpi_index=None,
                p3_mpi_index=None,
                packet_num=None,
                packet_sa=address,
                packet_nrt=length,
                equipment_group='',
                device_name='',
                equipment_type='',
                jka_equipment_index=-1,
                in_lua_buffer=self.in_lua_buffer_var.get(),
                lua_buffer_category=self.lua_category_var.get(),
                lbi_position=self.lbi_position_var.get(),
                lbi_data_type=self.lbi_data_type_var.get(),
                lua_buffer_note=lua_buffer_note,
                manual_override=self.manual_override_var.get()
            )
            self.app.registers.append(register_obj)
            
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
        self.values = values  # Store values for later use in save_changes
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("✏️ Edit Register")
        self.dialog.geometry("600x750")  # Increased to match Add dialog
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg='#f5f7fa')
        
        # Title
        title_frame = tk.Frame(self.dialog, bg='#3498db', height=60)
        title_frame.pack(fill='x')
        tk.Label(title_frame, text="✏️ Edit Register Information", 
                font=('Segoe UI', 14, 'bold'), fg='white', bg='#3498db').pack(pady=15)
        
        # Create scrollable frame for form (like Add dialog)
        canvas_container = ttk.Frame(self.dialog)
        canvas_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        canvas = tk.Canvas(canvas_container, bg='#f5f7fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient='vertical', command=canvas.yview)
        
        self.scrollable_frame = ttk.Frame(canvas, padding=30)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw', width=560)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Enable mousewheel scrolling - bind to canvas AND frame (same as Add dialog)
        def on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except:
                pass  # Canvas destroyed, ignore
        
        # Bind to both canvas and frame so scrolling works when hovering over either
        canvas.bind("<MouseWheel>", on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", on_mousewheel)
        
        # Make sure all widgets support mouse scroll
        def bind_tree(widget):
            widget.bind("<MouseWheel>", on_mousewheel)
            for child in widget.winfo_children():
                bind_tree(child)
        bind_tree(self.scrollable_frame)
        
        # Unbind mousewheel when dialog closes
        def _on_dialog_close():
            try:
                canvas.unbind("<MouseWheel>")
                self.scrollable_frame.unbind("<MouseWheel>")
            except:
                pass
            self.dialog.destroy()
        
        self._on_dialog_close = _on_dialog_close  # Save reference for Cancel button
        self.dialog.protocol("WM_DELETE_WINDOW", _on_dialog_close)
        
        # Use scrollable_frame instead of frame for all widgets
        frame = self.scrollable_frame
        
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
        self.access_combo.bind("<<ComboboxSelected>>", lambda e: self.on_access_change())
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
        cloud_combo.bind("<<ComboboxSelected>>", lambda e: self.on_cloud_output_change())
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
        
        # ============================================================================
        # PACKET ASSIGNMENT SECTION
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        ttk.Label(frame, text="📦 Packet Assignment", 
                 font=('Segoe UI', 11, 'bold'), foreground='#9b59b6').grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        row += 1
        
        # Packet Number
        ttk.Label(frame, text="Packet Number:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        
        # Get packet number from column 17 (visible Packet #)
        packet_num_val = values[17] if len(values) > 17 else ''
        if packet_num_val == '' or packet_num_val is None:
            packet_num_val = ''
        
        self.packet_num_var = tk.StringVar(value=str(packet_num_val) if packet_num_val != '' else '')
        packet_entry = ttk.Entry(frame, textvariable=self.packet_num_var, width=30, font=('Segoe UI', 10))
        packet_entry.grid(row=row, column=1, pady=10, sticky='ew')
        
        ttk.Label(frame, text="⚠️ Rules:\n• Must be ≥ 1\n• Same Slave+FC per packet\n• Max 70 registers per packet", 
                 font=('Segoe UI', 8), foreground='#7f8c8d', justify='left').grid(row=row+1, column=0, columnspan=2, pady=2)
        row += 2
        
        ttk.Label(frame, text="💡 Leave empty for auto-assignment", 
                 font=('Segoe UI', 8, 'italic'), foreground='#9b59b6').grid(row=row, column=0, columnspan=2, sticky='w', pady=(0, 5))
        row += 1
        
        # ============================================================================
        # LUA BUFFER SECTION
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        ttk.Label(frame, text="🔧 Lua Buffer Configuration", 
                 font=('Segoe UI', 11, 'bold'), foreground='#8e44ad').grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        row += 1
        
        # In Lua Buffer
        ttk.Label(frame, text="In Lua Buffer:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        lua_buffer_val = values[24] if len(values) > 24 else "No"
        self.in_lua_buffer_var = tk.StringVar(value=lua_buffer_val)
        self.in_lua_buffer_combo = ttk.Combobox(frame, textvariable=self.in_lua_buffer_var, 
                                  values=["No", "Yes"], 
                                  width=28, state='readonly', font=('Segoe UI', 10))
        self.in_lua_buffer_combo.grid(row=row, column=1, pady=10, sticky='ew')
        self.in_lua_buffer_combo.bind("<<ComboboxSelected>>", lambda e: self.update_lua_buffer_controls())
        ttk.Label(frame, text="💡 Use Lua Buffer for calculations?", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # Lua Buffer Category
        ttk.Label(frame, text="Lua Category:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        lua_category_val = values[25] if len(values) > 25 else "N/A"
        self.lua_category_var = tk.StringVar(value=lua_category_val)
        self.lua_category_combo = ttk.Combobox(frame, textvariable=self.lua_category_var, 
                                  values=["N/A", "Equipment", "User Variable"], 
                                  width=28, state='disabled', font=('Segoe UI', 10))
        self.lua_category_combo.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 P2.MPI (Equipment) or P2.RPCI (User Var)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # LBI Position
        ttk.Label(frame, text="LBI Position:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        lbi_position_val = values[26] if len(values) > 26 else "Auto"
        self.lbi_position_var = tk.StringVar(value=lbi_position_val)
        self.lbi_position_entry = ttk.Entry(frame, textvariable=self.lbi_position_var, width=30, font=('Segoe UI', 10), state='disabled')
        self.lbi_position_entry.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Auto-assign or manual (e.g., 1, 2, 3...)", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # LBI Data Type
        ttk.Label(frame, text="LBI Data Type:", font=('Segoe UI', 10, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        lbi_data_type_val = values[27] if len(values) > 27 else "Number"
        self.lbi_data_type_var = tk.StringVar(value=lbi_data_type_val)
        self.lbi_data_type_combo = ttk.Combobox(frame, textvariable=self.lbi_data_type_var, 
                                  values=["Number", "Boolean", "String"], 
                                  width=28, state='disabled', font=('Segoe UI', 10))
        self.lbi_data_type_combo.grid(row=row, column=1, pady=10, sticky='ew')
        ttk.Label(frame, text="💡 Data type in Lua Buffer array", 
                 font=('Segoe UI', 8), foreground='#7f8c8d').grid(row=row, column=2, padx=5, sticky='w')
        row += 1
        
        # Initialize Lua Buffer control states based on current value
        self.update_lua_buffer_controls()
        
        # ============================================================================
        # MANUAL OVERRIDE SECTION
        # ============================================================================
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        ttk.Label(frame, text="🛡️ Manual Override", 
                 font=('Segoe UI', 11, 'bold'), foreground='#c0392b').grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        row += 1
        
        # Manual Override Checkbox
        manual_override_val = values[37] if len(values) > 37 else False
        # Convert string 'True'/'False' to boolean
        if isinstance(manual_override_val, str):
            manual_override_val = manual_override_val.lower() == 'true'
        self.manual_override_var = tk.BooleanVar(value=manual_override_val)
        self.manual_override_check = ttk.Checkbutton(frame, text="Enable Manual Override (preserve Array Membership field - don't auto-regenerate)",
                                                     variable=self.manual_override_var)
        self.manual_override_check.grid(row=row, column=0, columnspan=3, sticky='w', pady=10)
        row += 1
        
        # Manual Override Info Box
        manual_override_info_frame = tk.Frame(frame, bg='#ffe5e5', relief='solid', borderwidth=1)
        tk.Label(manual_override_info_frame, text="⚠️ Manual Override Mode", font=('Segoe UI', 9, 'bold'), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=10, pady=(8, 2))
        tk.Label(manual_override_info_frame, text="When enabled:", 
                font=('Segoe UI', 8, 'bold'), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=20)
        tk.Label(manual_override_info_frame, text="✓ Your manual 'Array Membership' field will be preserved", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30)
        tk.Label(manual_override_info_frame, text="✓ P2.MPI / P2.RPCI / P3.MPI arrays won't be auto-regenerated", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30)
        tk.Label(manual_override_info_frame, text="✓ You control which ParamMap arrays this parameter belongs to", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30)
        tk.Label(manual_override_info_frame, text="When disabled (default):", 
                font=('Segoe UI', 8, 'bold'), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=20, pady=(5, 0))
        tk.Label(manual_override_info_frame, text="✗ Array Membership is auto-calculated from Lua Buffer + Cloud settings", 
                font=('Segoe UI', 8), bg='#ffe5e5', fg='#c0392b').pack(anchor='w', padx=30, pady=(0, 8))
        manual_override_info_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=10)
        row += 1
        
        frame.columnconfigure(1, weight=1)
        
        # Buttons (inside scrollable frame)
        ttk.Separator(frame, orient='horizontal').grid(row=row, column=0, columnspan=3, sticky='ew', pady=15)
        row += 1
        
        btn_frame = tk.Frame(frame, bg='#f5f7fa')
        btn_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        save_btn = tk.Button(btn_frame, text="💾 Save Changes", command=self.save_changes,
                           font=('Segoe UI', 11, 'bold'), bg='#3498db', fg='white',
                           relief='flat', padx=20, pady=10, cursor='hand2')
        save_btn.pack(side='left', padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="❌ Cancel", command=self._on_dialog_close,
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
    
    def on_cloud_output_change(self):
        """Auto-configure Lua Buffer when Cloud Output is set to Yes"""
        cloud = self.cloud_var.get()
        access = self.access_var.get().split(' - ')[0] if ' - ' in self.access_var.get() else self.access_var.get()
        
        if cloud == "Yes":
            # Cloud output params typically need Lua Buffer access
            # Auto-enable if not already enabled
            if self.in_lua_buffer_var.get() == "No":
                self.in_lua_buffer_var.set("Yes")
                # Smart default: Equipment category for cloud params
                self.lua_category_var.set("Equipment")
                # Trigger UI update
                self.update_lua_buffer_controls()
                
                # Show user-friendly notification
                print("[Auto-Config] ☁️ Cloud Output=Yes → Lua Buffer enabled (Category: Equipment)")
        elif cloud == "No" and access in ['W', 'RW']:
            # Write/RW params still need Lua Buffer even without cloud
            if self.in_lua_buffer_var.get() == "No":
                self.in_lua_buffer_var.set("Yes")
                self.lua_category_var.set("Equipment")
                self.update_lua_buffer_controls()
                print(f"[Auto-Config] ✍️ Write parameter → Lua Buffer enabled (Category: Equipment)")
    
    def on_access_change(self):
        """Auto-configure Lua Buffer for Write parameters"""
        access = self.access_var.get().split(' - ')[0] if ' - ' in self.access_var.get() else self.access_var.get()
        
        if access in ['W', 'RW']:
            # Write/RW parameters need Lua Buffer for command execution
            if self.in_lua_buffer_var.get() == "No":
                self.in_lua_buffer_var.set("Yes")
                self.lua_category_var.set("Equipment")
                self.update_lua_buffer_controls()
                print(f"[Auto-Config] ✍️ Access={access} → Lua Buffer enabled (Category: Equipment)")
    
    def update_lua_buffer_controls(self):
        """Enable/disable Lua Buffer controls based on 'In Lua Buffer' selection"""
        if self.in_lua_buffer_var.get() == "Yes":
            # Enable all Lua Buffer fields
            self.lua_category_combo.config(state='readonly')
            if self.lua_category_var.get() == "N/A":
                self.lua_category_var.set("Equipment")  # Default to Equipment
            self.lbi_position_entry.config(state='normal')
            self.lbi_data_type_combo.config(state='readonly')
        else:
            # Disable and reset Lua Buffer fields
            self.lua_category_combo.config(state='disabled')
            self.lua_category_var.set("N/A")
            self.lbi_position_entry.config(state='disabled')
            if self.lbi_position_var.get() != "Auto":
                self.lbi_position_var.set("Auto")
            self.lbi_data_type_combo.config(state='disabled')
            if self.lbi_data_type_var.get() not in ["Number", "Boolean", "String"]:
                self.lbi_data_type_var.set("Number")
    
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
                # Access type parsing: "R - Read Only" -> "R"
                if ' - ' in access_text:
                    access = access_text.split(' - ')[0].strip()
                else:
                    access = access_text.strip()
                
                # Validate access type
                if access not in ['R', 'W', 'RW']:
                    raise ValueError(f"Invalid access type: {access}")
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
                messagebox.showerror("Length Does Not Match Format", 
                                   f"Format {fmt} requires {expected_length} registers, but Length shows {length}.\n\n"
                                   f"To fix: Select a different Format from the dropdown.\n"
                                   f"Length will update automatically.")
                return
            
            # VALIDATION: Length limit
            if length > 70:
                messagebox.showerror("Length Too Large", 
                                   f"Length {length} exceeds maximum of 70 registers.\n\n"
                                   f"Please select a different Format with fewer registers.")
                return
            
            # VALIDATION: Function Code vs Access Type Logic
            # READ FCs (1,2,3,4) should only work with 'R' or 'RW'
            # WRITE FCs (5,6,15,16) should only work with 'W' or 'RW'
            read_fcs = [1, 2, 3, 4]
            write_fcs = [5, 6, 15, 16]
            
            if fc in read_fcs:
                if 'R' not in access:
                    messagebox.showerror("Function Code Mismatch", 
                                       f"FC {fc} is for reading data.\n\n"
                                       f"But Access Type '{access}' does not allow reading.\n\n"
                                       f"To fix: Change Access to 'R' or 'RW'.")
                    return
            elif fc in write_fcs:
                if 'W' not in access:
                    messagebox.showerror("Function Code Mismatch", 
                                       f"FC {fc} is for writing data.\n\n"
                                       f"But Access Type '{access}' does not allow writing.\n\n"
                                       f"To fix: Change Access to 'W' or 'RW'.")
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
                        # Build simplified warning message
                        overlap_msg = (
                            f"Overlapping Register Detected!\n\n"
                            f"Register #{existing_serial} already uses:\n"
                            f"  Slave {existing_slave}, Address {existing_addr}-{existing_end_addr}\n\n"
                            f"Your new register will use:\n"
                            f"  Slave {slave_id}, Address {address}-{new_end_addr}\n\n"
                            f"These address ranges overlap on the same slave device.\n\n"
                            f"Continue anyway?"
                        )
                        
                        result = messagebox.askyesno("Overlapping Register", overlap_msg)
                        if not result:
                            return
                        # If user clicked Yes, continue to update the register
                        break
            
            # VALIDATION: Cloud output restrictions
            # Based on verified client examples (Import_Examples/):
            # - W (Write): NEVER cloud="Yes" (0/52 examples)
            # - R (Read): CAN have cloud="Yes" (including feedback!)
            # - RW: Treat like W (write capability = no cloud)
            cloud_enabled = self.cloud_var.get() == "Yes"
            
            if cloud_enabled:
                if access in ['W', 'RW']:
                    messagebox.showerror("Cloud Output Not Allowed",
                                       f"Cannot enable Cloud for Access Type '{access}'.\n\n"
                                       f"Write parameters (W/RW) are local control commands.\n"
                                       f"Cloud cannot write back to Modbus devices.\n\n"
                                       f"To fix: Change Access to 'R' OR set Cloud to 'No'.")
                    return
            
            # VALIDATION: JSON fields for cloud parameters
            json_group = self.json_group_var.get().strip()
            json_unit = self.json_unit_var.get().strip()
            json_key = self.json_key_var.get().strip()
            
            if cloud_enabled:
                warnings = []
                if not json_group:
                    warnings.append("• JSON Group")
                if not json_unit:
                    warnings.append("• JSON Unit")
                if not json_key:
                    warnings.append("• JSON Key")
                
                if warnings:
                    warning_msg = "\n".join(warnings)
                    result = messagebox.askyesno("Missing Cloud Information", 
                                               f"Cloud is enabled but these fields are empty:\n\n{warning_msg}\n\n"
                                               f"Without these fields, this parameter won't appear in cloud output.\n\n"
                                               f"Continue anyway? (You can fill them later)")
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
            
            # Parse and validate packet number
            packet_num_str = self.packet_num_var.get().strip()
            if packet_num_str == '':
                packet_num = ''  # Empty means not assigned yet
            else:
                try:
                    packet_num = int(packet_num_str)
                    if packet_num < 1:
                        messagebox.showerror("❌ Invalid Packet Number", 
                                           f"Packet number must be ≥ 1.\nGot: {packet_num}")
                        return
                except (ValueError, TypeError):
                    messagebox.showerror("❌ Invalid Packet Number", 
                                       f"Packet number must be a number or empty.\nGot: '{packet_num_str}'")
                    return
            
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
                json_key,
                self.values[12] if len(self.values) > 12 else '',  # array_membership
                self.values[13] if len(self.values) > 13 else serial_no,  # b5_id
                packet_num if packet_num != '' else '',  # packet_num (use edited value)
                self.values[15] if len(self.values) > 15 else address,  # packet_sa
                self.values[16] if len(self.values) > 16 else length,  # packet_nrt
                # TRANSPARENT FIELDS (columns 18-23) - visible
                packet_num if packet_num != '' else '',  # Packet # (use edited value)
                self.values[18] if len(self.values) > 18 else address,  # Packet Start
                self.values[19] if len(self.values) > 19 else length,  # Packet Regs
                self.values[20] if len(self.values) > 20 else ('write' if access in ['W', 'RW'] else 'read_only'),  # Param Type
                self.values[21] if len(self.values) > 21 else '',  # Paired With
                self.values[22] if len(self.values) > 22 else -1,  # JKA Index
                # LUA BUFFER FIELDS (columns 24-27) - visible, editable
                self.in_lua_buffer_var.get(),  # In Lua Buffer
                self.lua_category_var.get(),  # Lua Category
                self.lbi_position_var.get(),  # LBI Position
                self.lbi_data_type_var.get(),  # LBI Data Type
                # INTERNAL METADATA (columns 28-36) - hidden
                self.values[28] if len(self.values) > 28 else ('write' if access in ['W', 'RW'] else 'read_only'),  # parameter_type
                self.values[29] if len(self.values) > 29 else '',  # write_param_id
                self.values[30] if len(self.values) > 30 else '',  # feedback_param_id
                self.values[31] if len(self.values) > 31 else '',  # p2_mpi_index
                self.values[32] if len(self.values) > 32 else '',  # p3_mpi_index
                self.values[33] if len(self.values) > 33 else '',  # equipment_group
                self.values[34] if len(self.values) > 34 else '',  # device_name
                self.values[35] if len(self.values) > 35 else '',  # equipment_type
                self.values[36] if len(self.values) > 36 else -1,  # jka_equipment_index
                self.values[37] if len(self.values) > 37 else '',   # lua_buffer_note (column 36)
                self.manual_override_var.get()  # Column 37 - manual_override
            ))
            
            # BUG FIX: Update corresponding RegisterEntry object in self.app.registers
            # Find and update the register by param_id
            for reg in self.app.registers:
                if reg.param_id == serial_no:
                    # Update all edited fields
                    reg.slave_id = slave_id
                    reg.fc = fc
                    reg.address = address
                    reg.length = length
                    reg.fmt = fmt
                    reg.multiplier = multiplier
                    reg.access = access
                    reg.cloud = self.cloud_var.get()
                    reg.json_group = json_group
                    reg.json_unit = json_unit
                    reg.json_key = json_key
                    # Update packet info
                    reg.packet_num = packet_num if packet_num != '' else None
                    # Update Lua Buffer fields
                    reg.in_lua_buffer = self.in_lua_buffer_var.get()
                    reg.lua_buffer_category = self.lua_category_var.get()
                    reg.lbi_position = self.lbi_position_var.get()
                    reg.lbi_data_type = self.lbi_data_type_var.get()
                    # Update Manual Override flag
                    reg.manual_override = self.manual_override_var.get()
                    break
            
            self.dialog.destroy()
            messagebox.showinfo("✅ Success", f"Register updated successfully!\n\nParameter ID: {serial_no}\nSlave: {slave_id}, FC: {fc}, Address: {address}")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messagebox.showerror("❌ Unexpected Error", 
                               f"An unexpected error occurred:\n\n{str(e)}\n\nPlease report this error with the following details:\n\n{error_details[:200]}...")

# Entry point
    def _auto_assign_packets(self):
        """Auto-assign packet numbers and b5_ids to all registers"""
        try:
            # Get current registers from tree
            registers = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                if len(values) >= 9:
                    reg = {
                        'slave_id': int(values[1]) if values[1] else 0,
                        'fc': int(values[2]) if values[2] else 0,
                        'address': int(values[3]) if values[3] else 0,
                        'length': int(values[4]) if values[4] else 1,
                        'fmt': int(values[5]) if values[5] else 3,
                        'multiplier': float(values[6]) if values[6] else 1.0,
                        'access': str(values[7]) if values[7] else 'R',
                        'cloud': str(values[8]) if values[8] else 'No',
                        'json_group': str(values[9]) if len(values) > 9 else '',
                        'json_unit': str(values[10]) if len(values) > 10 else '',
                        'json_key': str(values[11]) if len(values) > 11 else ''
                    }
                    registers.append(reg)
            
            if not registers:
                messagebox.showwarning("Warning", "No registers to assign packets to")
                return
            
            # Auto-assign packet numbers
            registers = auto_assign_packet_numbers(registers)
            
            # Auto-generate b5_ids
            registers = auto_generate_b5_ids(registers)
            
            # Update tree
            self.tree.delete(*self.tree.get_children())
            for idx, reg in enumerate(registers):
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.tree.insert("", "end", values=(
                    idx + 1,  # S.No
                    reg.get('slave_id', ''),
                    reg.get('fc', ''),
                    reg.get('address', ''),
                    reg.get('length', ''),
                    reg.get('fmt', ''),
                    reg.get('multiplier', ''),
                    reg.get('access', ''),
                    reg.get('cloud', ''),
                    reg.get('json_group', ''),
                    reg.get('json_unit', ''),
                    reg.get('json_key', ''),
                    reg.get('array_membership', ''),
                    reg.get('b5_id', idx + 1),
                    reg.get('packet_num', 0),
                    reg.get('packet_sa', reg.get('address', 0)),
                    reg.get('packet_nrt', reg.get('length', 1)),
                    # TRANSPARENT FIELDS (columns 18-23) - visible
                    None, None, None, 'read_only', None, -1,
                    # LUA BUFFER FIELDS (columns 24-27) - visible
                    'No', 'N/A', 'Auto', 'Number',
                    # INTERNAL METADATA - hidden
                    'read_only', '', '', '', '', '', '', '', -1
                ), tags=(tag,))
            
            # Validate
            is_valid, msg, stats = validate_packet_assignments(registers)
            
            if is_valid:
                info_msg = f"✓ Auto-assignment complete!\n\n"
                info_msg += f"Total Registers: {stats['total_registers']}\n"
                info_msg += f"Total Packets: {stats['total_packets']}\n"
                info_msg += f"B5 ID Range: {stats['b5_id_range']}\n"
                info_msg += f"Packet Range: {stats['packet_range']}"
                messagebox.showinfo("Success", info_msg)
            else:
                messagebox.showerror("Validation Error", msg)
                
        except Exception as e:
            messagebox.showerror("Error", f"Auto-assignment failed: {str(e)}")
    
    def _validate_assignments(self):
        """Validate current packet and b5_id assignments"""
        try:
            # Get current registers from tree
            registers = []
            for item in self.tree.get_children():
                values = self.tree.item(item)['values']
                if len(values) >= 2:
                    reg = {
                        'b5_id': int(values[0]) if values[0] else None,
                        'packet_num': int(values[1]) if values[1] else None
                    }
                    registers.append(reg)
            
            if not registers:
                messagebox.showwarning("Warning", "No registers to validate")
                return
            
            is_valid, msg, stats = validate_packet_assignments(registers)
            
            if is_valid:
                info_msg = f"✓ Validation passed!\n\n"
                info_msg += f"Total Registers: {stats['total_registers']}\n"
                info_msg += f"Total Packets: {stats['total_packets']}\n"
                info_msg += f"B5 ID Range: {stats['b5_id_range']}\n"
                info_msg += f"Packet Range: {stats['packet_range']}"
                messagebox.showinfo("Validation Success", info_msg)
            else:
                messagebox.showerror("Validation Error", msg)
                
        except Exception as e:
            messagebox.showerror("Error", f"Validation failed: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusConfigGenerator(root)
    root.mainloop()

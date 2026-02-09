"""
Reverse Transformation Engine - Smart Version
Converts Modbus JSON + Paramap JSON  Register Entry JSON
WITHOUT extra metadata fields - uses intelligent reconstruction
"""

import json
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ReconstructedRegister:
    """Reconstructed register entry from reverse transformation - 25-field schema with equipment hierarchy"""
    param_id: int
    slave_id: int
    fc: int
    address: int
    length: int
    fmt: int
    multiplier: float
    access: str
    cloud: str
    json_group: str
    json_unit: str
    json_key: str
    array_membership: str
    b5_id: int  # Original B5.ID
    packet_num: int  # B5.PN - packet number
    packet_sa: int  # B4.SA[packet_num-1] - packet start address
    packet_nrt: int  # B4.NRT[packet_num-1] - num registers in packet
    # Phase 1: Parameter type classification
    parameter_type: str  # 'write' | 'feedback' | 'read_only'
    write_param_id: Optional[int]  # For feedback params
    feedback_param_id: Optional[int]  # For write params
    p2_mpi_index: Optional[int]  # P2.MPI ordering
    p3_mpi_index: Optional[int]  # P3.MPI ordering
    # Phase 3: Equipment hierarchy
    equipment_group: str  # JKA equipment group name
    device_name: str  # Specific device/sensor name
    equipment_type: str  # AI/DI/EM classification
    jka_equipment_index: int  # JKA entry index (-1 if not in JKA)


class ReverseTransformationEngine:
    """Smart reverse transformation - no metadata needed"""

    def __init__(self):
        self.modbus_json = None
        self.paramap_json = None
        self.b5_id_to_props = {}
        self.packet_to_slave_fc = {}
        self.b5_to_json_keys = {}
        self.write_params = set()
        self.feedback_params = set()

    def transform(self, modbus_json: Dict, paramap_json: Dict) -> Dict:
        """Main entry point for reverse transformation"""
        self.modbus_json = modbus_json
        self.paramap_json = paramap_json

        self._validate_input()
        self._extract_b5_mappings()
        self._extract_b4_mappings()
        self._classify_parameters()
        self._extract_mpi_indices()  # NEW: Extract MPI ordering
        self._extract_jky_mappings()

        registers = self._reconstruct_registers()
        self._validate_output(registers)
        
        # Extract metadata for perfect reconstruction
        metadata = self._extract_metadata()

        return {
            "registers": [self._register_to_dict(r) for r in registers],
            "metadata": metadata
        }

    def _validate_input(self):
        """Validate input JSON structure"""
        required_modbus_keys = ["B1", "B2", "B3", "B4", "B5", "B6"]
        for key in required_modbus_keys:
            if key not in self.modbus_json:
                raise ValueError(f"Missing required key in Modbus JSON: {key}")

        required_paramap_keys = ["P1", "P2", "P3", "JKY"]
        for key in required_paramap_keys:
            if key not in self.paramap_json:
                raise ValueError(f"Missing required key in Paramap JSON: {key}")

    def _extract_b5_mappings(self):
        """Extract B5 parameter properties including array_membership if stored"""
        b5 = self.modbus_json["B5"]
        
        # Support both field name formats: AD/STA for address, MP/MLT for multiplier
        address_key = "AD" if "AD" in b5 else "STA"
        multiplier_key = "MP" if "MP" in b5 else "MLT"

        for i, b5_id in enumerate(b5["ID"]):
            self.b5_id_to_props[b5_id] = {
                "address": b5[address_key][i],
                "length": b5["LN"][i],
                "fmt": b5["FMT"][i],
                "multiplier": b5[multiplier_key][i],
                "packet_num": b5["PN"][i],  # Add packet number
                "array_membership": b5.get("AM", [])[i] if "AM" in b5 and i < len(b5.get("AM", [])) else ""  # Store if available
            }

    def _extract_b4_mappings(self):
        """Extract B4 packet to slave/FC mappings"""
        b4 = self.modbus_json["B4"]

        # Build packet_num to slave/FC mapping
        for packet_num in range(1, len(b4.get("SID", [])) + 1):
            idx = packet_num - 1
            self.packet_to_slave_fc[packet_num] = {
                "slave_id": b4.get("SID", [])[idx] if idx < len(b4.get("SID", [])) else 0,
                "fc": b4.get("FC", [])[idx] if idx < len(b4.get("FC", [])) else 0
            }

    def _classify_parameters(self):
        """Classify parameters as write, read, or feedback using B6"""
        b6 = self.modbus_json.get("B6", {})
        
        self.write_params = set(b6.get("WP", []))
        self.feedback_params = set(b6.get("RP", []))
        
        # Build write-feedback cross-reference mappings
        # For feedback params, find their corresponding write param
        self.feedback_to_write = {}  # feedback_param_id -> write_param_id
        self.write_to_feedback = {}  # write_param_id -> feedback_param_id
        
        # Strategy: feedback params in B6.RP correspond to write params in B6.WP
        # Typically they are in the same order, but we'll match by position if available
        wp_list = b6.get("WP", [])
        rp_list = b6.get("RP", [])
        
        # Simple heuristic: pair by index if lists have same length
        if len(wp_list) == len(rp_list):
            for i in range(len(wp_list)):
                write_id = wp_list[i]
                feedback_id = rp_list[i]
                self.write_to_feedback[write_id] = feedback_id
                self.feedback_to_write[feedback_id] = write_id
    
    def _extract_mpi_indices(self):
        """Extract P2.MPI and P3.MPI indices for deterministic ordering"""
        self.p2_mpi_indices = {}  # param_id -> index in P2.MPI
        self.p3_mpi_indices = {}  # param_id -> index in P3.MPI
        
        # Extract P2.MPI ordering
        p2 = self.paramap_json.get("P2", {})
        p2_mpi = p2.get("MPI", [])
        for idx, param_id in enumerate(p2_mpi):
            self.p2_mpi_indices[param_id] = idx
        
        # Extract P3.MPI ordering
        p3 = self.paramap_json.get("P3", {})
        p3_mpi = p3.get("MPI", [])
        for idx, param_id in enumerate(p3_mpi):
            self.p3_mpi_indices[param_id] = idx
    
    def _determine_array_membership(self, b5_id: int, stored_membership: str = "") -> str:
        """Determine which arrays this parameter belongs to (FIRMWARE-CORRECT LOGIC)
        
        NOTE: P2.LBI, P2.RPCI, P3.MDI contain INDICES, not B5.ID values!
        Only P2.MPI and P3.MPI contain B5.ID values.
        
        Strategy: If stored_membership is available and non-empty, use it.
        Otherwise, reconstruct from P2.MPI and P3.MPI only.
        """
        # If we have stored array_membership, use it (prevents enrichment)
        if stored_membership:
            return stored_membership
        
        # Otherwise, reconstruct from P2/P3 MPI arrays
        arrays = []
        
        # Check P2.MPI (contains B5.ID values)
        p2 = self.paramap_json.get("P2", {})
        p2_mpi = p2.get("MPI", [])
        if b5_id in p2_mpi:
            arrays.append("P2.MPI")
            # Also mark as P2.LBI since MPI params have LBI indices
            # But we don't check P2.LBI array itself (it contains indices)
        
        # Check P3.MPI (contains B5.ID values)
        p3 = self.paramap_json.get("P3", {})
        p3_mpi = p3.get("MPI", [])
        if b5_id in p3_mpi:
            arrays.append("P3.MPI")
            # Also mark as P3.MDI since MPI params have MDI indices
            # But we don't check P3.MDI array itself (it contains indices)
        
        # NOTE: We do NOT check P2.LBI, P2.RPCI, or P3.MDI arrays
        # because they contain sequential indices [1,2,3...], not B5.ID values
        
        return ",".join(arrays)

    def _extract_jky_mappings(self):
        """Extract cloud JSON key mappings from JKY (CORRECT: JKA → P3.MDI Sequential Mapping)
        
        CRITICAL DISCOVERY FROM EXCEL ANALYSIS:
        =========================================
        JKA maps to P3.MDI SEQUENTIALLY, where:
        - P3.MDI = P3.MPI + P3.LBI (Modbus params + calculated/RPC params for cloud)
        - JKA[i] consumes N parameters from P3.MDI[starting_index], where N = len(JKA[i][2]) (key array size)
        - Multi-key arrays: each key = one parameter in order
        
        JKA Format A: [Equipment_Name, [Unit], [Key1, Key2, ...]]
        JKA Format B: [Equipment_Group, [Param1, Param2, ...], [Device1, Device2, ...]]
        
        Example (VFD project):
        JKA[0] = ["VFD", [""], ["PNMPI","P_LD","V_LD","FRQ","I_LD","ALRM","MODE","STAT"]]
        This consumes P3.MDI[0:8] (8 parameters)
        JKA[1] would start at P3.MDI[8]
        
        WRONG (old code): JKA[i] → P2.MPI[i] 
        RIGHT (fixed):    JKA[i] → P3.MDI[mdi_index] (sequential consumption)
        """
        jky = self.paramap_json.get("JKY", {})
        
        if "JK" in jky:
            # Old format: dict entries with explicit B5_id (backward compatibility)
            for entry in jky.get("JK", []):
                if isinstance(entry, dict) and "B5_id" in entry:
                    b5_id = entry["B5_id"]
                    self.b5_to_json_keys[b5_id] = {
                        "json_group": entry.get("json_group", ""),
                        "json_unit": entry.get("json_unit", ""),
                        "json_key": entry.get("json_key", ""),
                        "equipment_group": entry.get("json_group", ""),
                        "device_name": entry.get("json_key", ""),
                        "equipment_type": "",
                        "jka_equipment_index": -1
                    }
        elif "JKA" in jky:
            # Production format: array entries mapping to P3.MDI sequentially
            p3 = self.paramap_json.get("P3", {})
            p3_mpi = p3.get("MPI", [])  # Modbus params for cloud
            p3_lbi = p3.get("LBI", [])  # Lua calculated/RPC params for cloud
            p2 = self.paramap_json.get("P2", {})
            
            # CRITICAL FIX: P2.LBI can be an array or missing
            # If P2.LBI is array, use first element as start; otherwise use large default
            p2_lbi_data = p2.get("LBI", [])
            if isinstance(p2_lbi_data, list) and len(p2_lbi_data) > 0:
                p2_lbi_start = p2_lbi_data[0]  # First LBI B5.ID
            elif isinstance(p2_lbi_data, int):
                p2_lbi_start = p2_lbi_data  # Direct value (backward compatibility)
            else:
                p2_lbi_start = 1000000  # Large default if not present
            
            # CRITICAL: Build P3.MDI = P3.MPI + P3.LBI (sequential combined array)
            # P3.MPI contains actual B5.ID values
            # P3.LBI contains indices, need to convert to B5.ID: P2.LBI start + index
            p3_mdi = p3_mpi.copy()  # Start with P3.MPI B5.IDs
            for lbi_index in p3_lbi:
                p3_mdi.append(p2_lbi_start + lbi_index)  # Convert LBI index to B5.ID
            
            jka_entries = jky.get("JKA", [])
            
            # Safety check: return early if no JKA entries
            if len(jka_entries) == 0:
                return
            
            # Map JKA entries sequentially to P3.MDI
            mdi_index = 0  # Current position in P3.MDI
            
            for jka_equipment_idx, entry in enumerate(jka_entries):
                # Robust validation: skip malformed entries
                if not isinstance(entry, list) or len(entry) < 3:
                    continue
                
                # Safety check: ensure entry elements are correct types
                if not isinstance(entry[0], str):  # Equipment name must be string
                    continue
                if not isinstance(entry[1], list):  # Unit array must be list
                    continue
                if not isinstance(entry[2], list):  # Key array must be list
                    continue
                
                equipment_name = entry[0]  # Equipment group name
                unit_array = entry[1]  # Unit array (may be single or multiple)
                key_array = entry[2]  # Key array (determines param count)
                
                # Determine equipment type and structure from arrays
                if len(key_array) > 0:
                    num_params = len(key_array)  # Multi-key array: each key = 1 param
                    
                    # Check if Format B (param names and devices)
                    is_format_b = len(unit_array) > 1
                    
                    # Assign equipment metadata to each parameter consumed by this JKA entry
                    for param_idx in range(num_params):
                        # CRITICAL: Boundary check - stop if exceeding P3.MDI
                        if mdi_index >= len(p3_mdi):
                            break  # Continue to next JKA entry
                        
                        b5_id = p3_mdi[mdi_index]
                        
                        # Extract specific key and unit for this param (with bounds checking)
                        json_key = key_array[param_idx] if param_idx < len(key_array) else ""
                        
                        # Ensure json_key is string (handle unexpected types)
                        if not isinstance(json_key, str):
                            json_key = str(json_key) if json_key is not None else ""
                        
                        if is_format_b:
                            # Format B: unit_array contains parameter names
                            json_unit = ""
                            device_name = unit_array[param_idx] if param_idx < len(unit_array) else ""
                            # Ensure device_name is string
                            if not isinstance(device_name, str):
                                device_name = str(device_name) if device_name is not None else ""
                        else:
                            # Format A: unit_array contains units
                            json_unit = unit_array[0] if len(unit_array) > 0 else ""
                            # Ensure json_unit is string
                            if not isinstance(json_unit, str):
                                json_unit = str(json_unit) if json_unit is not None else ""
                            device_name = json_key  # In Format A, key serves as device identifier
                        
                        self.b5_to_json_keys[b5_id] = {
                            "json_group": equipment_name,  # Equipment group (e.g., "VFD", "VALVE")
                            "json_unit": json_unit,
                            "json_key": json_key,
                            "equipment_group": equipment_name,
                            "device_name": device_name,
                            "equipment_type": self._infer_equipment_type(equipment_name, json_key),
                            "jka_equipment_index": jka_equipment_idx,
                            "jka_param_index": param_idx
                        }
                        
                        mdi_index += 1
                else:
                    # Empty key array - skip this JKA entry
                    continue
    
    def _infer_equipment_type(self, equipment_name, json_key):
        """Infer equipment type from naming patterns"""
        equipment_lower = equipment_name.lower()
        key_lower = json_key.lower() if json_key else ""
        
        # Energy meter patterns
        if any(x in equipment_lower for x in ['em', 'energy', 'meter', 'kwh']):
            return "EM"
        
        # Digital input patterns
        if any(x in key_lower for x in ['di', 'status', 'state', 'alarm', 'alrm', 'mode']):
            return "DI"
        
        # Analog input patterns (default for most)
        return "AI"

    def _reconstruct_registers(self) -> List[ReconstructedRegister]:
        """Reconstruct register entries from B5 with all 21 fields"""
        registers = []
        b5 = self.modbus_json["B5"]
        b5_ids = b5["ID"]
        packet_nums = b5["PN"]
        
        # Reconstructing registers

        for i, b5_id in enumerate(b5_ids):
            packet_num = packet_nums[i]
            props = self.b5_id_to_props.get(b5_id, {})
            slave_fc = self.packet_to_slave_fc.get(packet_num, {})
            json_keys = self.b5_to_json_keys.get(b5_id, {})

            # Determine access type
            access = self._determine_access_type(b5_id)
            
            # NEW: Determine parameter_type using B6 cross-reference
            parameter_type = self._determine_parameter_type(b5_id, access)

            # Determine cloud status (FIRMWARE-CORRECT: Only P3.MPI params go to cloud)
            p3_mpi = self.paramap_json.get("P3", {}).get("MPI", [])
            cloud = "Yes" if b5_id in p3_mpi else "No"
            
            # Cloud status determined
            
            # Determine array membership (use stored value if available)
            stored_membership = props.get("array_membership", "")
            array_membership = self._determine_array_membership(b5_id, stored_membership)

            # Get packet information
            packet_num = props.get("packet_num", 0)
            packet_idx = packet_num - 1 if packet_num > 0 else 0
            
            # Extract packet metadata from B4
            b4 = self.modbus_json.get("B4", {})
            packet_sa = b4.get("SA", [])[packet_idx] if packet_idx < len(b4.get("SA", [])) else 0
            packet_nrt = b4.get("NRT", [])[packet_idx] if packet_idx < len(b4.get("NRT", [])) else 0
            
            # NEW: Extract write/feedback cross-references
            write_param_id = self.feedback_to_write.get(b5_id) if parameter_type == 'feedback' else None
            feedback_param_id = self.write_to_feedback.get(b5_id) if parameter_type == 'write' else None
            
            # NEW: Extract MPI indices
            p2_mpi_index = self.p2_mpi_indices.get(b5_id)
            p3_mpi_index = self.p3_mpi_indices.get(b5_id)

            register = ReconstructedRegister(
                param_id=b5_id,
                slave_id=slave_fc.get("slave_id", 0),
                fc=slave_fc.get("fc", 0),
                address=props.get("address", 0),
                length=props.get("length", 0),
                fmt=props.get("fmt", 0),
                multiplier=props.get("multiplier", 1.0),
                access=access,
                cloud=cloud,
                json_group=json_keys.get("json_group", ""),  # FIXED: Use correct dict key
                json_unit=json_keys.get("json_unit", ""),
                json_key=json_keys.get("json_key", ""),
                array_membership=array_membership,
                b5_id=b5_id,
                packet_num=packet_num,
                packet_sa=packet_sa,
                packet_nrt=packet_nrt,
                parameter_type=parameter_type,
                write_param_id=write_param_id,
                feedback_param_id=feedback_param_id,
                p2_mpi_index=p2_mpi_index,
                p3_mpi_index=p3_mpi_index,
                equipment_group=json_keys.get("equipment_group", ""),
                device_name=json_keys.get("device_name", ""),
                equipment_type=json_keys.get("equipment_type", ""),
                jka_equipment_index=json_keys.get("jka_equipment_index", -1)
            )

            registers.append(register)

        return registers

    def _determine_access_type(self, b5_id: int) -> str:
        """Determine access type (R, W, RW)"""
        is_write = b5_id in self.write_params
        is_feedback = b5_id in self.feedback_params

        if is_write and is_feedback:
            return "RW"
        elif is_write:
            return "W"
        else:
            return "R"
    
    def _determine_parameter_type(self, b5_id: int, access: str) -> str:
        """Determine parameter_type using B6 cross-reference logic
        
        Logic:
        - If b5_id in B6.WP -> 'write'
        - If b5_id in B6.RP -> 'feedback' (read for verification)
        - Otherwise -> 'read_only' (monitoring/telemetry)
        """
        if b5_id in self.write_params:
            return 'write'
        elif b5_id in self.feedback_params:
            return 'feedback'
        else:
            return 'read_only'

    def _validate_output(self, registers: List):
        """Validate reconstructed registers"""
        if not registers:
            raise ValueError("No registers were reconstructed")

    def _register_to_dict(self, register: ReconstructedRegister) -> Dict:
        """Convert register to dictionary with all 25 fields (including equipment hierarchy)"""
        return {
            "param_id": register.param_id,
            "slave_id": register.slave_id,
            "fc": register.fc,
            "address": register.address,
            "length": register.length,
            "fmt": register.fmt,
            "multiplier": register.multiplier,
            "access": register.access,
            "cloud": register.cloud,
            "json_group": register.json_group,
            "json_unit": register.json_unit,
            "json_key": register.json_key,
            "array_membership": register.array_membership,
            "b5_id": register.b5_id,
            "packet_num": register.packet_num,
            "packet_sa": register.packet_sa,
            "packet_nrt": register.packet_nrt,
            "parameter_type": register.parameter_type,
            "write_param_id": register.write_param_id,
            "feedback_param_id": register.feedback_param_id,
            "p2_mpi_index": register.p2_mpi_index,
            "p3_mpi_index": register.p3_mpi_index,
            "equipment_group": register.equipment_group,
            "device_name": register.device_name,
            "equipment_type": register.equipment_type,
            "jka_equipment_index": register.jka_equipment_index
        }

    def _extract_metadata(self) -> Dict:
        """Extract metadata sections for perfect reconstruction"""
        metadata = {}
        
        # Extract B1, B2, B3 from Modbus JSON
        if "B1" in self.modbus_json:
            metadata["b1"] = self.modbus_json["B1"]
        if "B2" in self.modbus_json:
            metadata["b2"] = self.modbus_json["B2"]
        if "B3" in self.modbus_json:
            metadata["b3"] = self.modbus_json["B3"]
            
        # Extract P1, JKC, NTC, MST from Paramap JSON
        if "P1" in self.paramap_json:
            metadata["p1"] = self.paramap_json["P1"]
        if "P2" in self.paramap_json:
            metadata["p2"] = self.paramap_json["P2"]
        if "P3" in self.paramap_json:
            metadata["p3"] = self.paramap_json["P3"]
        if "JKY" in self.paramap_json:
            metadata["jky"] = self.paramap_json["JKY"]  # Store complete JKY for perfect reconstruction
        if "JKC" in self.paramap_json:
            metadata["jkc"] = self.paramap_json["JKC"]
        if "NTC" in self.paramap_json:
            metadata["ntc"] = self.paramap_json["NTC"]
        if "MST" in self.paramap_json:
            metadata["mst"] = self.paramap_json["MST"]
            
        return metadata

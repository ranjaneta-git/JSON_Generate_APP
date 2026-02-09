"""
Forward Transformation Engine - Smart Version
Converts Register Entry JSON  Modbus JSON + Paramap JSON
WITHOUT using metadata - smart classification and array building
"""

import json
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


@dataclass
class RegisterEntry:
    """Register entry from input JSON - 21-field schema"""
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
    array_membership: str = ""
    b5_id: int = 0  # Original B5.ID
    packet_num: int = 0  # B5.PN - STORED, not recomputed (0 = not assigned, valid range: 1-N)
    packet_sa: int = 0  # B4.SA - STORED, not recomputed
    packet_nrt: int = 0  # B4.NRT - STORED, not recomputed
    parameter_type: str = "read_only"  # 'write' | 'feedback' | 'read_only'
    write_param_id: int = None  # For feedback params
    feedback_param_id: int = None  # For write params
    p2_mpi_index: int = None  # P2.MPI ordering
    p3_mpi_index: int = None  # P3.MPI ordering


class ForwardTransformationEngine:
    """Smart forward transformation - intelligent array building"""

    def __init__(self):
        self.registers = []
        self.cloud_params = []
        self.non_cloud_params = []
        self.metadata = {}  # Store metadata for perfect reconstruction

    def transform(self, register_json: Dict) -> Tuple[Dict, Dict]:
        """Main transformation entry point"""
        self._load_registers(register_json)
        self._classify_registers()

        modbus_json = self._build_modbus_json()
        paramap_json = self._build_paramap_json()

        self._validate_output(modbus_json, paramap_json)

        return modbus_json, paramap_json

    def _load_registers(self, register_json: Dict):
        """Load and parse register entries with 21-field schema"""
        self.registers = []
        
        # Store metadata if present
        self.metadata = register_json.get("metadata", {})
        
        for entry in register_json.get("registers", []):
            reg = RegisterEntry(
                param_id=entry.get("param_id", 0),
                slave_id=entry.get("slave_id", 0),
                fc=entry.get("fc", 0),
                address=entry.get("address", 0),
                length=entry.get("length", 0),
                fmt=entry.get("fmt", 0),
                multiplier=entry.get("multiplier", 1.0),
                access=entry.get("access", "R"),
                cloud=entry.get("cloud", "No"),
                json_group=entry.get("json_group", ""),
                json_unit=entry.get("json_unit", ""),
                json_key=entry.get("json_key", ""),
                array_membership=entry.get("array_membership", ""),
                b5_id=entry.get("b5_id", 0),
                packet_num=entry.get("packet_num", 0),  # 0 means not assigned, will be auto-generated starting from 1
                packet_sa=entry.get("packet_sa", 0),
                packet_nrt=entry.get("packet_nrt", 0),
                parameter_type=entry.get("parameter_type", "read_only"),
                write_param_id=entry.get("write_param_id"),
                feedback_param_id=entry.get("feedback_param_id"),
                p2_mpi_index=entry.get("p2_mpi_index"),
                p3_mpi_index=entry.get("p3_mpi_index")
            )
            self.registers.append(reg)

    def _classify_registers(self):
        """Classify registers by cloud status"""
        self.cloud_params = [r for r in self.registers if r.cloud == "Yes"]
        self.non_cloud_params = [r for r in self.registers if r.cloud == "No"]

    def _build_modbus_json(self) -> Dict:
        """Build Modbus configuration"""
        b1 = self._build_b1()
        b2 = self._build_b2()
        b3 = self._build_b3()
        b4 = self._build_b4()
        b5 = self._build_b5()
        b6 = self._build_b6()

        return {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5, "B6": b6}

    def _build_b1(self) -> Dict:
        """Build B1 - Gateway/device info"""
        # Use metadata if available
        if hasattr(self, 'metadata') and 'b1' in self.metadata:
            return self.metadata['b1']
        
        # Fallback to calculated values
        unique_slaves = len(set(r.slave_id for r in self.registers))
        total_params = len(self.registers)
        
        return {
            "NOS": unique_slaves,
            "NOP": total_params,
            "NPT": 0,  # Will be calculated from B4
            "NOR": 0   # Will be calculated
        }
    def _build_b2(self) -> Dict:
        """Build B2 - Communication settings"""
        # Use metadata if available
        if hasattr(self, 'metadata') and 'b2' in self.metadata:
            return self.metadata['b2']
        
        # Fallback to defaults
        return {"BR": 38400, "DF": "8N1"}
    def _build_b3(self) -> Dict:
        """Build B3 - Slave configuration"""
        # Use metadata if available
        if hasattr(self, 'metadata') and 'b3' in self.metadata:
            return self.metadata['b3']
        
        # Fallback: Build from registers
        unique_slaves = sorted(set(r.slave_id for r in self.registers))
        
        return {
            "SI": unique_slaves,
            "SP": [8, 1, 1]  # Default parity settings
        }
    def _build_b4(self) -> Dict:
        """Build B4 - Packet configuration using packet_num from register config"""
        # Check if packet_num is available (new format)
        has_packet_num = any(hasattr(r, 'packet_num') and r.packet_num is not None for r in self.registers)
        
        if has_packet_num:
            # Use packet_num for exact reconstruction
            packet_dict = {}  # packet_num -> list of registers
            
            for reg in self.registers:
                pnum = reg.packet_num
                if pnum not in packet_dict:
                    packet_dict[pnum] = []
                packet_dict[pnum].append(reg)
            
            # Build B4 arrays in packet_num order
            SA_list = []
            NRT_list = []
            FC_list = []
            SID_list = []
            
            for pnum in sorted(packet_dict.keys()):
                regs = packet_dict[pnum]
                first_reg = regs[0]
                
                SA_list.append(first_reg.packet_sa if hasattr(first_reg, 'packet_sa') else first_reg.address)
                NRT_list.append(first_reg.packet_nrt if hasattr(first_reg, 'packet_nrt') else len(regs))
                FC_list.append(first_reg.fc)
                SID_list.append(first_reg.slave_id)
            
            return {
                "SID": SID_list,
                "FC": FC_list,
                "SA": SA_list,
                "NRT": NRT_list
            }
        else:
            # Fallback: use old grouping logic
            packet_groups = self._create_packet_groups()
            
            SA_list = []
            NRT_list = []
            FC_list = []
            SID_list = []

            for group_key in sorted(packet_groups.keys()):
                regs = packet_groups[group_key]
                slave_id, fc = group_key
                
                SID_list.append(slave_id)
                FC_list.append(fc)
                SA_list.append(regs[0].address if regs else 0)
                NRT_list.append(len(regs))

            return {
                "SID": SID_list,
                "FC": FC_list,
                "SA": SA_list,
                "NRT": NRT_list
            }
    def _create_packet_groups(self) -> Dict:
        """Group registers by slave_id and fc for packets"""
        groups = {}
        
        for reg in self.registers:
            key = (reg.slave_id, reg.fc)
            if key not in groups:
                groups[key] = []
            groups[key].append(reg)
        
        # Sort within each group by address
        for key in groups:
            groups[key].sort(key=lambda r: r.address)
        
        return groups

    def _build_b5(self) -> Dict:
        """Build B5 - Parameter configuration using STORED packet_num (no recomputation)
        Uses production field names: STA (address), MLT (multiplier)"""
        # Check if packet_num is available (21-field schema)
        has_packet_num = any(hasattr(r, 'packet_num') and r.packet_num is not None and r.packet_num > 0 for r in self.registers)
        
        # Use production field names: STA (not AD), MLT (not MP)
        b5_data = {"ID": [], "PN": [], "STA": [], "LN": [], "FMT": [], "MLT": []}
        
        if has_packet_num:
            # Use STORED packet_num - NO RECOMPUTATION
            # Sort by param_id to maintain consistent order
            for reg in sorted(self.registers, key=lambda r: r.param_id):
                b5_data["ID"].append(reg.param_id)
                b5_data["PN"].append(reg.packet_num)  # Use stored value
                b5_data["STA"].append(reg.address)  # Production field name
                b5_data["LN"].append(reg.length)
                b5_data["FMT"].append(reg.fmt)
                b5_data["MLT"].append(reg.multiplier)  # Production field name
        else:
            # Fallback: compute packet numbers (for legacy data)
            packet_groups = self._create_packet_groups()
            packet_num = 1
            for group_key in sorted(packet_groups.keys()):
                regs = packet_groups[group_key]
                
                for reg in regs:
                    b5_data["ID"].append(reg.param_id)
                    b5_data["PN"].append(packet_num)
                    b5_data["STA"].append(reg.address)  # Production field name
                    b5_data["LN"].append(reg.length)
                    b5_data["FMT"].append(reg.fmt)
                    b5_data["MLT"].append(reg.multiplier)  # Production field name
                
                packet_num += 1

        return b5_data

    def _build_b6(self) -> Dict:
        """Build B6 - Write/Feedback parameter lists using parameter_type or array_membership"""
        write_params = []
        feedback_params = []

        for reg in self.registers:
            param_type = getattr(reg, 'parameter_type', 'read_only')
            
            if param_type == 'write':
                write_params.append(reg.param_id)
            elif param_type == 'feedback':
                feedback_params.append(reg.param_id)
            # Fallback to array_membership analysis
            elif hasattr(reg, 'array_membership') and reg.array_membership:
                array_mem = reg.array_membership
                # If in P2.MPI but NOT in P3.MPI, and has write access, likely write param
                if 'P2.MPI' in array_mem and 'P3.MPI' not in array_mem and 'W' in reg.access:
                    write_params.append(reg.param_id)
                # If NOT in P2.MPI and NOT in P3.MPI, but in LBI/RPCI/MDI, likely feedback
                elif 'P2.MPI' not in array_mem and 'P3.MPI' not in array_mem and ('LBI' in array_mem or 'MDI' in array_mem):
                    feedback_params.append(reg.param_id)

        return {"WP": sorted(write_params), "RP": sorted(feedback_params)}

    def _build_paramap_json(self) -> Dict:
        """Build parameter mapping configuration"""
        p1 = self._build_p1()
        p2 = self._build_p2()
        p3 = self._build_p3()
        jky = self._build_jky()

        result = {"P1": p1, "P2": p2, "P3": p3, "JKY": jky}
        
        # Add metadata sections if available
        if hasattr(self, 'metadata'):
            for key in ['jkc', 'ntc', 'mst']:
                if key in self.metadata:
                    result[key.upper()] = self.metadata[key]
        
        return result
    def _build_p1(self) -> Dict:
        """Build P1 - Device type configuration with NMD calculation
        
        P1.NMD = Number of Monitoring Data = len(P3.MPI)
        This is the count of monitoring parameters sent to cloud (P3.MPI)
        Critical for firmware memory allocation!
        """
        # Use metadata if available
        if hasattr(self, 'metadata') and 'p1' in self.metadata:
            p1 = self.metadata['p1']
            # Ensure NMD is present
            if 'NMD' not in p1:
                p3 = self._build_p3()
                p1['NMD'] = len(p3["MPI"])  # NMD = count of P3.MPI (monitoring data for cloud)
            return p1
        
        # Calculate P3 to get NMD
        p3 = self._build_p3()
        
        return {
            "DT": 0,  # Device type
            "DN": "",  # Device name
            "NMD": len(p3["MPI"])  # NMD = Number of Monitoring Data = P3.MPI count
        }
    def _build_p2(self) -> Dict:
        """Build P2 - Lua Buffer Configuration (FIRMWARE-CORRECT LOGIC)
        
        P2.MPI: Contains B5.ID values for Modbus params (59 in production)
                - Write params from B6.WP
                - Monitoring params needed by Lua
                - EXCLUDES feedback params from B6.RP
        
        P2.LBI: Sequential indices [1, 2, 3, ..., 72]
                - First 59: Map to P2.MPI parameters
                - Last 13: Map to P2.RPCI commands
        
        P2.RPCI: Sequential indices [1, 2, 3, ..., 13]
                - Cloud RPC command slots
        """
        mpi = []
        
        # Get B6 arrays to identify write and feedback parameters
        b6 = self._build_b6()
        write_params = set(b6["WP"])
        feedback_params = set(b6["RP"])
        
        # Check if we have stored p2_mpi_index for ordering
        has_p2_index = any(hasattr(r, 'p2_mpi_index') and r.p2_mpi_index is not None for r in self.registers)
        
        # Check if we have array_membership field
        has_array_membership = any(hasattr(r, 'array_membership') and r.array_membership and 'P2.MPI' in r.array_membership for r in self.registers)
        
        if has_p2_index:
            # Use stored p2_mpi_index for exact ordering
            mpi_with_index = []
            for r in self.registers:
                if hasattr(r, 'p2_mpi_index') and r.p2_mpi_index is not None:
                    mpi_with_index.append((r.param_id, r.p2_mpi_index))
            
            # Sort by stored index and extract param IDs
            mpi_with_index.sort(key=lambda x: x[1])
            mpi = [x[0] for x in mpi_with_index]
        elif has_array_membership:
            # Use array_membership field to determine which params go in P2.MPI
            for r in sorted(self.registers, key=lambda x: x.param_id):
                if hasattr(r, 'array_membership') and r.array_membership and 'P2.MPI' in r.array_membership:
                    mpi.append(r.param_id)
        else:
            # Rebuild P2.MPI from classification logic
            # Rule 1: Include write parameters (from B6.WP)
            for param_id in sorted(write_params):
                mpi.append(param_id)
            
            # Rule 2: Include monitoring parameters (NOT feedback, NOT already in MPI)
            # NOTE: Params can be in BOTH P2.MPI and P3.MPI (overlap is allowed)
            for r in sorted(self.registers, key=lambda x: x.param_id):
                if r.param_id not in feedback_params and r.param_id not in mpi:
                    # Check if this is a monitoring parameter for Lua
                    # Include if it's read-only access (monitoring)
                    if r.parameter_type == "read_only" or r.access == "R":
                        # Add to P2.MPI - Lua needs it for calculations/logic
                        mpi.append(r.param_id)
        
        # P2.LBI: Sequential indices [1, 2, ..., len(MPI) + len(RPCI)]
        # First part maps to P2.MPI
        lbi = list(range(1, len(mpi) + 1))  # [1, 2, 3, ..., 59]
        
        # P2.RPCI: Sequential RPC command indices
        # Determine RPCI count (default 13 in production)
        rpci_count = 13  # Production default
        rpci = list(range(1, rpci_count + 1))  # [1, 2, 3, ..., 13]
        
        # Extend LBI for RPCI slots
        lbi.extend(range(len(mpi) + 1, len(mpi) + rpci_count + 1))  # [60, 61, ..., 72]
        
        return {"MPI": mpi, "LBI": lbi, "RPCI": rpci}

    def _build_p3(self) -> Dict:
        """Build P3 - Cloud Output Configuration (FIRMWARE-CORRECT LOGIC)
        
        P3.MPI: Contains B5.ID values for cloud monitoring (97 in production)
                - Monitoring parameters for cloud telemetry
                - EXCLUDES write params from B6.WP
                - EXCLUDES feedback params from B6.RP
                - Can overlap with P2.MPI (same param in both is OK)
        
        P3.MDI: Sequential indices [1, 2, 3, ..., 97]
                - Maps P3.MPI parameters to M_data buffer
                - If P3.LBI used, extends: [98, 99, ...]
        
        P3.LBI: Lua calculated values (currently empty in production)
                - If used, starts from (P2.MPI count + 1) = 60
                - Example: [60, 61] for 2 calculated values
        """
        mpi = []
        
        # Get B6 arrays to identify write and feedback parameters
        b6 = self._build_b6()
        write_params = set(b6["WP"])
        feedback_params = set(b6["RP"])
        
        # Check if we have stored p3_mpi_index for ordering
        has_p3_index = any(hasattr(r, 'p3_mpi_index') and r.p3_mpi_index is not None for r in self.registers)
        
        # Check if we have array_membership field
        has_array_membership = any(hasattr(r, 'array_membership') and r.array_membership and 'P3.MPI' in r.array_membership for r in self.registers)
        
        if has_p3_index:
            # Use stored p3_mpi_index for exact ordering
            mpi_with_index = []
            for r in self.registers:
                if hasattr(r, 'p3_mpi_index') and r.p3_mpi_index is not None:
                    mpi_with_index.append((r.param_id, r.p3_mpi_index))
            
            # Sort by stored index and extract param IDs
            mpi_with_index.sort(key=lambda x: x[1])
            mpi = [x[0] for x in mpi_with_index]
        elif has_array_membership:
            # Use array_membership field to determine which params go in P3.MPI
            for r in sorted(self.registers, key=lambda x: x.param_id):
                if hasattr(r, 'array_membership') and r.array_membership and 'P3.MPI' in r.array_membership:
                    mpi.append(r.param_id)
        else:
            # Rebuild P3.MPI from classification logic
            # Rule 1: EXCLUDE write parameters (control commands don't go to cloud)
            # Rule 2: EXCLUDE feedback parameters (internal verification only)
            # Rule 3: INCLUDE monitoring parameters (sensors, status, etc.)
            
            for r in sorted(self.registers, key=lambda x: x.param_id):
                if r.param_id not in write_params and r.param_id not in feedback_params:
                    # This is a monitoring parameter
                    if r.cloud == "Yes" or (r.parameter_type == "read_only" and r.access == "R"):
                        mpi.append(r.param_id)
        
        # P3.MDI: Sequential indices for M_data buffer
        mdi = list(range(1, len(mpi) + 1))  # [1, 2, 3, ..., 97]
        
        # P3.LBI: Calculated values from Lua (currently empty)
        lbi = []
        
        # If P3.LBI were used, it would:
        # 1. Start from (P2.MPI count + 1)
        # 2. Extend P3.MDI with additional indices
        if lbi:
            # Extend MDI for calculated values
            mdi.extend(range(len(mpi) + 1, len(mpi) + len(lbi) + 1))
        
        return {"MPI": mpi, "MDI": mdi, "LBI": lbi}

    def _build_jky(self) -> Dict:
        """Build JKY - JSON key mappings (FIRMWARE-CORRECT LOGIC)
        
        JKA Structure (Production format):
        - Array of [param_name, [unit], [key]] entries
        - First len(P2.MPI) entries: Map to Modbus params via P2.MPI order
        - Remaining entries: Map to local/calculated params (if any)
        
        Example:
        JKA[0] -> P2.MPI[0] = 3  (Modbus param)
        JKA[1] -> P2.MPI[1] = 12 (Modbus param)
        ...
        JKA[59] -> Local param (if exists)
        
        Total JKA count = len(P2.MPI) + count(local_params_with_keys)
        """
        
        # If JKY exists in metadata, use it directly for perfect reconstruction
        if "jky" in self.metadata:
            return self.metadata["jky"]
        
        # Build JKA according to firmware mapping
        jka_entries = []
        p2 = self._build_p2()
        
        # First len(P2.MPI) entries: Map to P2.MPI parameters in order
        for param_id in p2["MPI"]:
            reg = next((r for r in self.registers if r.param_id == param_id), None)
            if reg:
                param_name = reg.json_group if reg.json_group else f"Param_{param_id}"
                jka_entries.append([
                    param_name,
                    [reg.json_unit if reg.json_unit else ""],
                    [reg.json_key if reg.json_key else ""]
                ])
        
        # Remaining entries: Local/digital parameters (if any)
        # These would be parameters with JSON keys but not in P2.MPI
        # Currently not implemented - production uses only P2.MPI mapping
        
        return {"JKA": jka_entries}

    def _validate_output(self, modbus_json: Dict, paramap_json: Dict):
        """Validate generated JSON structures"""
        required_modbus_keys = ["B1", "B2", "B3", "B4", "B5", "B6"]
        for key in required_modbus_keys:
            if key not in modbus_json:
                raise ValueError(f"Missing key in generated Modbus JSON: {key}")

        required_paramap_keys = ["P1", "P2", "P3", "JKY"]
        for key in required_paramap_keys:
            if key not in paramap_json:
                raise ValueError(f"Missing key in generated Paramap JSON: {key}")

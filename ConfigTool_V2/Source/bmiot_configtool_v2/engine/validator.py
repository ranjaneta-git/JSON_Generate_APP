"""Validation engine for BMIoT configuration.

Two passes:
  - Pre-generation: validates engineer input (V1-V16)
  - Post-generation: cross-validates output JSON (W1-W18)
"""

from __future__ import annotations

from typing import Any

from .constants import (
    ALL_FCS,
    MAX_NOP,
    MAX_NOR,
    MAX_NOS,
    MAX_NPT,
    MAX_NRT,
    MAX_NVS_KEY_LEN,
    MAX_SLAVE_ID,
    MIN_SLAVE_ID,
    READ_FCS,
    VALID_BAUD_RATES,
    VALID_DATA_FORMATS,
    VALID_FMTS,
    WRITE_FCS,
)
from .models import Project


class ValidationResult:
    """Collection of validation messages."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def __repr__(self) -> str:
        return f"ValidationResult(errors={len(self.errors)}, warnings={len(self.warnings)})"


# --------------------------------------------------------------------------
# Pre-generation validation (input checks)
# --------------------------------------------------------------------------

def validate_project(project: Project) -> ValidationResult:
    """Validate engineer input before generation (V1-V16)."""
    result = ValidationResult()

    # V1: at least 1 register
    all_regs = project.all_registers()
    if not all_regs:
        result.error("V1: No registers defined — need at least 1 device with 1 slave and 1 register")
        return result  # nothing else to check

    # V2: slave IDs in range
    for device in project.devices:
        for slave in device.slaves:
            if not (MIN_SLAVE_ID <= slave.modbus_id <= MAX_SLAVE_ID):
                result.error(
                    f"V2: Slave ID {slave.modbus_id} in device '{device.name}' "
                    f"out of range [{MIN_SLAVE_ID}-{MAX_SLAVE_ID}]"
                )

    # V3: no duplicate registers (same slave + FC + address)
    seen: set[tuple[int, int, int]] = set()
    for reg in all_regs:
        key = (reg.slave_id, reg.fc, reg.address)
        if key in seen:
            result.error(
                f"V3: Duplicate register at slave {reg.slave_id} "
                f"FC{reg.fc} address {reg.address}"
            )
        seen.add(key)

    # V4: FMT codes valid
    for reg in all_regs:
        if reg.fmt not in VALID_FMTS:
            result.error(f"V4: Invalid FMT code {reg.fmt} for register '{reg.name}'")

    # V5: FC codes valid
    for reg in all_regs:
        if reg.fc not in ALL_FCS:
            result.error(f"V5: Invalid FC {reg.fc} for register '{reg.name}'")

    # V6: baud rate
    if project.baud_rate not in VALID_BAUD_RATES:
        result.error(f"V6: Invalid baud rate {project.baud_rate}")

    # V7: data format
    if project.data_format not in VALID_DATA_FORMATS:
        result.error(f"V7: Invalid data format '{project.data_format}'")

    # V9/V10: Link B must be read-FC on same device
    for device in project.devices:
        device_slave_ids = {s.modbus_id for s in device.slaves}
        for slave in device.slaves:
            for reg in slave.registers:
                if reg.link_b_register is not None:
                    fb = reg.link_b_register
                    if not fb.is_read:
                        result.error(
                            f"V9: Link B for write register '{reg.name}' "
                            f"points to non-read register '{fb.name}' (FC={fb.fc})"
                        )
                    if fb.slave_id not in device_slave_ids:
                        result.error(
                            f"V9: Link B for '{reg.name}' points to register "
                            f"on slave {fb.slave_id} which is not in device '{device.name}'"
                        )

    # V11: NVS key length
    for nvs in project.nvs_slots:
        if len(nvs.key_name) > MAX_NVS_KEY_LEN:
            result.error(
                f"V11: NVS key '{nvs.key_name}' exceeds {MAX_NVS_KEY_LEN} chars"
            )

    # V12: NVS key uniqueness
    nvs_keys = [n.key_name for n in project.nvs_slots]
    if len(nvs_keys) != len(set(nvs_keys)):
        seen_keys: set[str] = set()
        for k in nvs_keys:
            if k in seen_keys:
                result.error(f"V12: Duplicate NVS key '{k}'")
            seen_keys.add(k)

    # V13: CloudGroup assignment count = keys × names
    for cg in project.cloud_groups:
        expected = cg.slot_count
        if cg.source_type == "modbus":
            actual = len(cg.registers)
        else:
            actual = len(cg.nvs_slots)
        if actual != expected:
            result.error(
                f"V13: CloudGroup '{cg.cluster_name}' has {actual} assignments "
                f"but needs {expected} (keys={len(cg.keys)} × names={len(cg.equipment_names)})"
            )
        # V13b: Check for None (unassigned) slots
        if cg.source_type == "modbus":
            none_count = sum(1 for r in cg.registers if r is None)
            if none_count:
                result.error(
                    f"V13: CloudGroup '{cg.cluster_name}' has {none_count} unassigned register slot(s). "
                    "Go to Step 6 and assign a register to every slot."
                )
        else:
            none_count = sum(1 for n in cg.nvs_slots if n is None)
            if none_count:
                result.error(
                    f"V13: CloudGroup '{cg.cluster_name}' has {none_count} unassigned NVS slot(s). "
                    "Go to Step 6 and assign an NVS slot to every slot."
                )

    # V14: Modbus cloud groups before NVS cloud groups
    seen_nvs = False
    for cg in project.cloud_groups:
        if cg.source_type == "nvs":
            seen_nvs = True
        elif cg.source_type == "modbus" and seen_nvs:
            result.error(
                f"V14: Modbus cloud group '{cg.cluster_name}' appears after NVS groups — "
                "all Modbus groups must come before NVS groups in JKA"
            )

    # V15: NTC array lengths
    if project.network is not None:
        net = project.network
        sn_len = len(net.slave_numbers)
        mi_len = len(net.machine_ids)
        mt_len = len(net.machine_types)
        if not (sn_len == mi_len == mt_len):
            result.error(
                f"V15: NTC array length mismatch — SN={sn_len}, MI={mi_len}, MT={mt_len}"
            )

    # V16: MLT > 0
    for reg in all_regs:
        if reg.mlt <= 0:
            result.error(
                f"V16: Multiplier must be positive for register '{reg.name}' "
                f"(got {reg.mlt})"
            )

    return result


# --------------------------------------------------------------------------
# Post-generation cross-validation (output checks)
# --------------------------------------------------------------------------

def validate_output(
    modbus: dict[str, Any],
    parammap: dict[str, Any],
) -> ValidationResult:
    """Cross-validate generated JSON output (W1-W18)."""
    result = ValidationResult()

    b1 = modbus.get("B1", {})
    b3 = modbus.get("B3", {})
    b4 = modbus.get("B4", {})
    b5 = modbus.get("B5", {})
    b6 = modbus.get("B6", {})

    p1 = parammap.get("P1", {})
    p2 = parammap.get("P2", {})
    p3 = parammap.get("P3", {})
    jky = parammap.get("JKY", {})
    jka = jky.get("JKA", [])

    nos = b1.get("NOS", 0)
    nop = b1.get("NOP", 0)
    npt = b1.get("NPT", 0)
    nor_val = b1.get("NOR", 0)

    b4_sa = b4.get("SA", [])
    b4_nrt = b4.get("NRT", [])
    b4_fc = b4.get("FC", [])
    b4_sid = b4.get("SID", [])

    b5_id = b5.get("ID", [])
    b5_pn = b5.get("PN", [])
    b5_sta = b5.get("STA", [])
    b5_ln = b5.get("LN", [])
    b5_fmt = b5.get("FMT", [])
    b5_mlt = b5.get("MLT", [])

    b6_wp = b6.get("WP", [])
    b6_rp = b6.get("RP", [])

    nlb = p1.get("NLB", 0)
    nmd = p1.get("NMD", 0)

    p2_lbi = p2.get("LBI", [])
    p2_mpi = p2.get("MPI", [])
    p2_rpci = p2.get("RPCI", [])

    p3_mdi = p3.get("MDI", [])
    p3_mpi = p3.get("MPI", [])
    p3_lbi = p3.get("LBI", [])

    # W1: NOR == sum(NRT)
    if nor_val != sum(b4_nrt):
        result.error(f"W1: B1.NOR={nor_val} != sum(B4.NRT)={sum(b4_nrt)}")

    # W2: NOP == len(B5.*) for all B5 arrays
    for name, arr in [("ID", b5_id), ("PN", b5_pn), ("STA", b5_sta),
                      ("LN", b5_ln), ("FMT", b5_fmt), ("MLT", b5_mlt)]:
        if nop != len(arr):
            result.error(f"W2: B1.NOP={nop} != len(B5.{name})={len(arr)}")

    # W3: NPT == len(B4.*) for all B4 arrays
    for name, arr in [("SA", b4_sa), ("NRT", b4_nrt), ("FC", b4_fc), ("SID", b4_sid)]:
        if npt != len(arr):
            result.error(f"W3: B1.NPT={npt} != len(B4.{name})={len(arr)}")

    # W4: NOS == len(B3.*) for all B3 arrays
    for name, arr in [("SI", b3.get("SI", [])), ("SP", b3.get("SP", []))]:
        if nos != len(arr):
            result.error(f"W4: B1.NOS={nos} != len(B3.{name})={len(arr)}")

    # W5: B5.STA within packet address range
    for i in range(len(b5_sta)):
        pn = b5_pn[i] - 1  # 0-based
        if 0 <= pn < len(b4_sa):
            pkt_start = b4_sa[pn]
            pkt_end = pkt_start + b4_nrt[pn]
            if not (b5_sta[i] >= pkt_start and b5_sta[i] + b5_ln[i] <= pkt_end):
                result.error(
                    f"W5: Param {i+1} (addr={b5_sta[i]}, LN={b5_ln[i]}) outside "
                    f"packet {b5_pn[i]} range [{pkt_start}, {pkt_end})"
                )

    # W6: B5.LN matches FMT→LN rule
    from .constants import FMT_TABLE
    for i in range(len(b5_fmt)):
        expected_ln = FMT_TABLE.get(b5_fmt[i], (None, None))[1]
        if expected_ln is not None and b5_ln[i] != expected_ln:
            result.error(
                f"W6: Param {i+1} FMT={b5_fmt[i]} requires LN={expected_ln} but got LN={b5_ln[i]}"
            )

    # W7: NLB == len(P2.MPI) + len(P2.RPCI)
    if nlb != len(p2_mpi) + len(p2_rpci):
        result.error(
            f"W7: P1.NLB={nlb} != len(P2.MPI)+len(P2.RPCI)="
            f"{len(p2_mpi)}+{len(p2_rpci)}"
        )

    # W8: NMD == len(P3.MPI) + len(P3.LBI)
    if nmd != len(p3_mpi) + len(p3_lbi):
        result.error(
            f"W8: P1.NMD={nmd} != len(P3.MPI)+len(P3.LBI)="
            f"{len(p3_mpi)}+{len(p3_lbi)}"
        )

    # W9: NMD == sum(keys × names for JKA) — FIRMWARE REFUSES TO BOOT
    jka_slots = sum(len(entry[1]) * len(entry[2]) for entry in jka) if jka else 0
    if nmd != jka_slots:
        result.error(
            f"W9: P1.NMD={nmd} != JKA total slots={jka_slots} — "
            "FIRMWARE WILL REFUSE TO BOOT"
        )

    # W10: P2.LBI == [1..NLB]
    expected_lbi = list(range(1, nlb + 1))
    if p2_lbi != expected_lbi:
        result.error(f"W10: P2.LBI is not sequential [1..{nlb}]")

    # W11: P3.MDI == [1..NMD]
    expected_mdi = list(range(1, nmd + 1))
    if p3_mdi != expected_mdi:
        result.error(f"W11: P3.MDI is not sequential [1..{nmd}]")

    # W12: len(WP) == len(RP)
    if len(b6_wp) != len(b6_rp):
        result.error(f"W12: len(B6.WP)={len(b6_wp)} != len(B6.RP)={len(b6_rp)}")

    # W13: All P2.MPI param IDs in range [1..NOP]
    for pid in p2_mpi:
        if pid < 1 or pid > nop:
            result.error(f"W13: P2.MPI contains invalid param ID {pid} (NOP={nop})")

    # W14: All P3.MPI param IDs in range [1..NOP]
    for pid in p3_mpi:
        if pid < 1 or pid > nop:
            result.error(f"W14: P3.MPI contains invalid param ID {pid} (NOP={nop})")

    # W15: All B6.WP entries must appear in P2.MPI
    p2_mpi_set = set(p2_mpi)
    for wp in b6_wp:
        if wp not in p2_mpi_set:
            result.error(
                f"W15: Write param {wp} in B6.WP but not in P2.MPI — "
                "firmware write will return READ_PARAM_NOT_FOUND"
            )

    # W16: Read packets before write packets per slave in B4
    if b4_sid:
        # Track per slave: once we see a write FC, no more read FCs allowed
        slave_seen_write: dict[int, bool] = {}
        for i in range(len(b4_fc)):
            sid = b4_sid[i]
            fc = b4_fc[i]
            if fc in WRITE_FCS:
                slave_seen_write[sid] = True
            elif fc in READ_FCS and slave_seen_write.get(sid, False):
                result.error(
                    f"W16: Read packet (FC={fc}) at index {i} appears after "
                    f"write packet for slave {sid} — will corrupt Reg[] offsets"
                )

    # W17: NRT ≤ MAX_NRT
    for i, nrt in enumerate(b4_nrt):
        if nrt > MAX_NRT:
            result.error(f"W17: B4.NRT[{i}]={nrt} exceeds MAX_NRT={MAX_NRT}")

    # W18: Firmware limits
    if nos > MAX_NOS:
        result.error(f"W18: NOS={nos} exceeds firmware limit {MAX_NOS}")
    if npt > MAX_NPT:
        result.error(f"W18: NPT={npt} exceeds firmware limit {MAX_NPT}")
    if nop > MAX_NOP:
        result.error(f"W18: NOP={nop} exceeds firmware limit {MAX_NOP}")
    if nor_val > MAX_NOR:
        result.error(f"W18: NOR={nor_val} exceeds firmware limit {MAX_NOR}")

    return result

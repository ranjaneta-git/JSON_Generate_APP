"""Import existing Modbus_Config.json + ParamMap_Config.json into internal model.

Limitation: device grouping cannot be reconstructed from JSON (devices are UI-only).
Imported configs have one device per slave by default.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import READ_FCS, WRITE_FCS
from .models import (
    CloudGroup,
    Device,
    NetworkConfig,
    NvsSlot,
    Project,
    Register,
    Slave,
)


class ImportError_(Exception):
    """Raised when JSON import fails."""


def import_json(
    modbus_path: str | Path,
    parammap_path: str | Path,
    project_name: str = "Imported",
) -> Project:
    """Import a Modbus_Config.json + ParamMap_Config.json pair into a Project."""
    modbus_path = Path(modbus_path)
    parammap_path = Path(parammap_path)

    with open(modbus_path, "r", encoding="utf-8-sig") as f:
        modbus = json.load(f)
    with open(parammap_path, "r", encoding="utf-8-sig") as f:
        parammap = json.load(f)

    return import_from_dicts(modbus, parammap, project_name)


def import_from_dicts(
    modbus: dict[str, Any],
    parammap: dict[str, Any],
    project_name: str = "Imported",
) -> Project:
    """Import from already-parsed dicts."""
    b1 = modbus["B1"]
    b2 = modbus["B2"]
    b3 = modbus["B3"]
    b4 = modbus["B4"]
    b5 = modbus["B5"]
    b6 = modbus["B6"]

    p1 = parammap["P1"]
    p2 = parammap["P2"]
    p3 = parammap["P3"]
    jky = parammap.get("JKY", {})
    jka_raw = jky.get("JKA", [])
    jkc = parammap.get("JKC", {})
    ntc = parammap.get("NTC", {})
    mst = parammap.get("MST", {})

    nop = b1["NOP"]

    # --- Build registers from B5 ---
    registers: list[Register] = []
    for i in range(nop):
        pn = b5["PN"][i]
        fc = b4["FC"][pn - 1]  # FC from the packet this param belongs to
        sid = b4["SID"][pn - 1]

        reg = Register(
            name=f"Param_{i + 1}",
            address=b5["STA"][i],
            fc=fc,
            fmt=b5["FMT"][i],
            mlt=b5["MLT"][i],
            slave_id=sid,
        )
        reg.param_id = i + 1
        reg.packet_number = pn
        registers.append(reg)

    # Map param_id → Register for quick lookup
    reg_by_id: dict[int, Register] = {r.param_id: r for r in registers}

    # --- Build slaves (one device per slave) ---
    devices: list[Device] = []
    slave_ids = b3["SI"]
    slave_regs_map: dict[int, list[Register]] = {sid: [] for sid in slave_ids}

    for reg in registers:
        if reg.slave_id in slave_regs_map:
            slave_regs_map[reg.slave_id].append(reg)

    for sid in slave_ids:
        slave = Slave(modbus_id=sid, registers=slave_regs_map.get(sid, []))
        device = Device(name=f"Device_S{sid}", slaves=[slave])
        devices.append(device)

    # --- Reconstruct LBI slot assignments from P2 ---
    p2_mpi = p2.get("MPI", [])
    p2_rpci = p2.get("RPCI", [])

    for lbi_idx, pid in enumerate(p2_mpi):
        if pid in reg_by_id:
            reg_by_id[pid].lbi_slot = lbi_idx + 1
            if reg_by_id[pid].is_read:
                reg_by_id[pid].needs_lbi_slot = True

    # --- Reconstruct Link B feedback pairs from P2.MPI interleaving ---
    # In the generator, Phase 1 lists each write param optionally followed
    # by its Link B hardware-feedback read param (e.g. valve command on
    # slave A → valve position sensor on slave B).  The feedback may be
    # on a different slave when separate I/O modules share a physical
    # connection.  A write immediately followed by a read in P2.MPI
    # therefore indicates a Link B pair.
    i = 0
    while i < len(p2_mpi):
        pid = p2_mpi[i]
        reg = reg_by_id.get(pid)
        if reg is not None and reg.is_write and i + 1 < len(p2_mpi):
            next_pid = p2_mpi[i + 1]
            next_reg = reg_by_id.get(next_pid)
            if next_reg is not None and next_reg.is_read:
                reg.link_b_register = next_reg
                i += 2
                continue
        i += 1

    # --- NVS slots from P2.RPCI ---
    nvs_slots: list[NvsSlot] = []
    for rpci_idx, rpci_val in enumerate(p2_rpci):
        nvs = NvsSlot(
            key_name=f"nvs_key_{rpci_val}",
            rpci_index=rpci_val,
            lbi_slot=len(p2_mpi) + rpci_idx + 1,
        )
        nvs_slots.append(nvs)

    # --- Cloud groups from JKA ---
    cloud_groups: list[CloudGroup] = []

    # Determine which params are Modbus-backed M_data (P3.MPI) vs LBI-backed (P3.LBI)
    p3_mpi = p3.get("MPI", [])
    p3_lbi_arr = p3.get("LBI", [])

    # Walk JKA and consume M_data slots sequentially
    md_ptr = 0
    for entry in jka_raw:
        cluster_name = entry[0]
        keys = entry[1]
        names = entry[2]
        slot_count = len(keys) * len(names)

        # Determine source type by checking if slots fall in P3.MPI or P3.LBI range
        modbus_count = len(p3_mpi)
        group_regs: list[Register] = []
        group_nvs: list[NvsSlot] = []
        source_type = "modbus"

        for _ in range(slot_count):
            if md_ptr < modbus_count:
                # Modbus-backed
                pid = p3_mpi[md_ptr]
                if pid in reg_by_id:
                    group_regs.append(reg_by_id[pid])
            else:
                # LBI-backed
                lbi_idx = md_ptr - modbus_count
                if lbi_idx < len(p3_lbi_arr):
                    lbi_val = p3_lbi_arr[lbi_idx]
                    # Find corresponding NVS slot
                    for nvs in nvs_slots:
                        if nvs.lbi_slot == lbi_val:
                            group_nvs.append(nvs)
                            break
                source_type = "nvs"
            md_ptr += 1

        cg = CloudGroup(
            cluster_name=cluster_name,
            keys=keys,
            equipment_names=names,
            source_type=source_type,
            registers=group_regs,
            nvs_slots=group_nvs,
        )
        cloud_groups.append(cg)

    # --- Network config ---
    network = NetworkConfig(
        ip=ntc.get("IP", ""),
        port=ntc.get("PT", ""),
        client_id=ntc.get("CI", ""),
        slave_numbers=ntc.get("SN", []),
        machine_ids=ntc.get("MI", []),
        machine_types=ntc.get("MT", []),
        device_id=ntc.get("DI", ""),
    )

    project = Project(
        name=project_name,
        baud_rate=b2.get("BR", 9600),
        data_format=b2.get("DF", "8N1"),
        devices=devices,
        cloud_groups=cloud_groups,
        nvs_slots=nvs_slots,
        network=network,
        profile=mst.get("PRF", 0),
    )

    return project

"""Project file save / load  (.bmiot_project JSON format)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..engine.models import (
    CloudGroup,
    Device,
    NetworkConfig,
    NvsSlot,
    Project,
    Register,
    Slave,
)

PROJECT_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_project(project: Project, path: str | Path) -> None:
    """Serialize the Project to a .bmiot_project JSON file."""
    flat_regs = project.all_registers()
    reg_to_idx: dict[int, int] = {id(r): i for i, r in enumerate(flat_regs)}

    def _reg_list(regs):
        """Convert register refs to indices, preserving None as -1."""
        return [reg_to_idx[id(r)] if r is not None and id(r) in reg_to_idx else -1
                for r in regs]

    def _nvs_list(slots):
        """Convert NVS slot refs to indices, preserving None as -1."""
        return [project.nvs_slots.index(n) if n is not None and n in project.nvs_slots else -1
                for n in slots]

    data: dict[str, Any] = {
        "version": PROJECT_VERSION,
        "project": {
            "name": project.name,
            "baud_rate": project.baud_rate,
            "data_format": project.data_format,
            "profile": project.profile,
            "devices": [
                {
                    "name": dev.name,
                    "slaves": [
                        {
                            "modbus_id": sl.modbus_id,
                            "registers": [
                                {
                                    "name": r.name,
                                    "address": r.address,
                                    "fc": r.fc,
                                    "fmt": r.fmt,
                                    "mlt": r.mlt,
                                    "needs_lbi_slot": r.needs_lbi_slot,
                                    "link_b_reg_idx": (
                                        reg_to_idx[id(r.link_b_register)]
                                        if r.link_b_register is not None
                                        and id(r.link_b_register) in reg_to_idx
                                        else None
                                    ),
                                }
                                for r in sl.registers
                            ],
                        }
                        for sl in dev.slaves
                    ],
                }
                for dev in project.devices
            ],
            "cloud_groups": [
                {
                    "cluster_name": cg.cluster_name,
                    "keys": cg.keys,
                    "equipment_names": cg.equipment_names,
                    "source_type": cg.source_type,
                    "reg_indices": _reg_list(cg.registers),
                    "nvs_slot_indices": _nvs_list(cg.nvs_slots),
                }
                for cg in project.cloud_groups
            ],
            "nvs_slots": [{"key_name": n.key_name} for n in project.nvs_slots],
            "network": (
                {
                    "ip": project.network.ip,
                    "port": project.network.port,
                    "client_id": project.network.client_id,
                    "slave_numbers": project.network.slave_numbers,
                    "machine_ids": project.network.machine_ids,
                    "machine_types": project.network.machine_types,
                    "device_id": project.network.device_id,
                }
                if project.network is not None
                else None
            ),
        },
    }

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_project(path: str | Path) -> Project:
    """Deserialize a Project from a .bmiot_project JSON file."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pd = data["project"]

    # --- Build devices / slaves / registers ---
    all_regs: list[Register] = []
    devices: list[Device] = []
    reg_idx = 0
    link_b_todo: list[tuple[int, int]] = []  # (reg_flat_idx, target_flat_idx)

    for dev_d in pd.get("devices", []):
        slaves: list[Slave] = []
        for sl_d in dev_d["slaves"]:
            sid = sl_d["modbus_id"]
            regs: list[Register] = []
            for r_d in sl_d["registers"]:
                reg = Register(
                    name=r_d["name"],
                    address=r_d["address"],
                    fc=r_d["fc"],
                    fmt=r_d["fmt"],
                    mlt=r_d.get("mlt", 1.0),
                    slave_id=sid,
                    needs_lbi_slot=r_d.get("needs_lbi_slot", False),
                )
                lb_idx = r_d.get("link_b_reg_idx")
                if lb_idx is not None:
                    link_b_todo.append((reg_idx, lb_idx))
                regs.append(reg)
                all_regs.append(reg)
                reg_idx += 1
            slaves.append(Slave(modbus_id=sid, registers=regs))
        devices.append(Device(name=dev_d["name"], slaves=slaves))

    # Restore Link B references
    for src_idx, tgt_idx in link_b_todo:
        if 0 <= tgt_idx < len(all_regs):
            all_regs[src_idx].link_b_register = all_regs[tgt_idx]

    # --- NVS slots ---
    nvs_slots: list[NvsSlot] = [
        NvsSlot(key_name=n["key_name"]) for n in pd.get("nvs_slots", [])
    ]

    # --- Cloud groups ---
    cloud_groups: list[CloudGroup] = []
    for cg_d in pd.get("cloud_groups", []):
        reg_refs = [
            all_regs[i] if 0 <= i < len(all_regs) else None
            for i in cg_d.get("reg_indices", [])
        ]
        nvs_refs = [
            nvs_slots[i] if 0 <= i < len(nvs_slots) else None
            for i in cg_d.get("nvs_slot_indices", [])
        ]
        cloud_groups.append(
            CloudGroup(
                cluster_name=cg_d["cluster_name"],
                keys=cg_d.get("keys", []),
                equipment_names=cg_d.get("equipment_names", []),
                source_type=cg_d.get("source_type", "modbus"),
                registers=reg_refs,
                nvs_slots=nvs_refs,
            )
        )

    # --- Network ---
    net_d = pd.get("network")
    network = (
        NetworkConfig(
            ip=net_d.get("ip", ""),
            port=net_d.get("port", ""),
            client_id=net_d.get("client_id", ""),
            slave_numbers=net_d.get("slave_numbers", []),
            machine_ids=net_d.get("machine_ids", []),
            machine_types=net_d.get("machine_types", []),
            device_id=net_d.get("device_id", ""),
        )
        if net_d is not None
        else None
    )

    return Project(
        name=pd.get("name", "Untitled"),
        baud_rate=pd.get("baud_rate", 9600),
        data_format=pd.get("data_format", "8N1"),
        devices=devices,
        cloud_groups=cloud_groups,
        nvs_slots=nvs_slots,
        network=network,
        profile=pd.get("profile", 0),
    )

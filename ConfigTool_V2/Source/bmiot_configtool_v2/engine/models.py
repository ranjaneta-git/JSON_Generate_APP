"""Data model classes for BMIoT gateway configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .constants import FMT_TABLE, READ_FCS, WRITE_FCS


@dataclass
class Register:
    """A single Modbus register/coil parameter."""

    name: str
    address: int          # Modbus register/coil address (0-65535)
    fc: int               # Function code (1-6)
    fmt: int              # Data format code (1-8)
    mlt: float = 1.0      # Multiplier applied after read
    slave_id: int = 0     # Modbus slave address this register belongs to

    # Engineer-assigned Link B feedback (optional, write regs only)
    link_b_register: Optional[Register] = field(default=None, repr=False)

    # Engineer marks True if Lua needs runtime access to this read register
    needs_lbi_slot: bool = False

    # --- Computed during generation (not engineer input) ---
    param_id: int = 0         # 1-based position in B5 arrays
    packet_number: int = 0    # 1-based B4 packet index
    lbi_slot: int = 0         # LBI slot number (0 = not assigned)

    @property
    def is_write(self) -> bool:
        return self.fc in WRITE_FCS

    @property
    def is_read(self) -> bool:
        return self.fc in READ_FCS

    @property
    def ln(self) -> int:
        """Register length: 1 for 16-bit, 2 for 32-bit."""
        return FMT_TABLE[self.fmt][1]

    def reset_computed(self) -> None:
        """Clear all computed fields (call before re-generation)."""
        self.param_id = 0
        self.packet_number = 0
        self.lbi_slot = 0


@dataclass
class Slave:
    """A Modbus slave device on the RS485 bus."""

    modbus_id: int                                       # Modbus address (1-247)
    registers: list[Register] = field(default_factory=list)


@dataclass
class Device:
    """Logical grouping of one or more slaves (UI-only concept, not in output JSON)."""

    name: str
    slaves: list[Slave] = field(default_factory=list)


@dataclass
class CloudGroup:
    """One JKA entry — maps to one cluster in the MQTT JSON hierarchy.

    For Modbus-backed groups: `registers` holds Register refs in JKA consumption order.
      Consumption order: for each equipment_name → for each key → one Register.
    For NVS-backed groups: `nvs_slots` holds NvsSlot refs in consumption order.
    """

    cluster_name: str                                     # e.g. "HP_Status"
    keys: list[str] = field(default_factory=list)         # e.g. ["St"]
    equipment_names: list[str] = field(default_factory=list)  # e.g. ["HP_Run", "Circ_Run"]
    source_type: str = "modbus"                           # "modbus" or "nvs"

    # Ordered assignments matching JKA consumption
    registers: list[Register] = field(default_factory=list, repr=False)
    nvs_slots: list[NvsSlot] = field(default_factory=list, repr=False)

    @property
    def slot_count(self) -> int:
        """Number of M_data slots this JKA entry consumes."""
        return len(self.keys) * len(self.equipment_names)


@dataclass
class NvsSlot:
    """An NVS/RAM-backed LBI slot for cloud RPC setpoints."""

    key_name: str             # NVS key name (≤15 chars, engineer-typed)
    rpci_index: int = 0       # 1-based RPCI index (computed)
    lbi_slot: int = 0         # LBI slot number (computed)

    def reset_computed(self) -> None:
        self.rpci_index = 0
        self.lbi_slot = 0


@dataclass
class NetworkConfig:
    """MQTT broker and cloud identity settings (NTC section)."""

    ip: str = "0.0.0.0"
    port: str = "1883"
    client_id: str = ""
    slave_numbers: list[int] = field(default_factory=list)
    machine_ids: list[str] = field(default_factory=list)
    machine_types: list[str] = field(default_factory=list)
    device_id: str = ""


@dataclass
class Project:
    """Top-level container for all engineer input."""

    name: str = "Untitled"
    baud_rate: int = 9600
    data_format: str = "8N1"
    devices: list[Device] = field(default_factory=list)
    cloud_groups: list[CloudGroup] = field(default_factory=list)
    nvs_slots: list[NvsSlot] = field(default_factory=list)
    network: Optional[NetworkConfig] = None
    profile: int = 0

    def all_registers(self) -> list[Register]:
        """Return flat list of all registers across all devices/slaves."""
        regs = []
        for device in self.devices:
            for slave in device.slaves:
                regs.extend(slave.registers)
        return regs

    def all_slaves(self) -> list[Slave]:
        """Return flat list of all slaves in device order → slave order."""
        slaves = []
        for device in self.devices:
            slaves.extend(device.slaves)
        return slaves

    def find_device_for_slave(self, slave_id: int) -> Optional[Device]:
        """Return the Device that owns the given slave modbus_id, or None."""
        for dev in self.devices:
            for sl in dev.slaves:
                if sl.modbus_id == slave_id:
                    return dev
        return None

    def find_slave(self, slave_id: int) -> Optional[Slave]:
        """Return the Slave with the given modbus_id, or None."""
        for dev in self.devices:
            for sl in dev.slaves:
                if sl.modbus_id == slave_id:
                    return sl
        return None

    def slave_display_items(self) -> list[tuple[str, Slave]]:
        """Return [(label, Slave), ...] for populating device/slave selectors."""
        items = []
        for dev in self.devices:
            for sl in dev.slaves:
                items.append((f"{dev.name}  /  Slave {sl.modbus_id}", sl))
        return items

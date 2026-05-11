"""JSON generation pipeline for Modbus_Config.json and ParamMap_Config.json.

Implements the 11-step generation algorithm:
  1. Build slave ordering, flatten & sort registers
  2. Group into packets (B4)
  3. Assign param IDs (B5)
  4. Build slave map (B3)
  5. Compute counts (B1)
  6. Build write pairs (B6)
  7. Build LBI mapping (P2) — 3-phase algorithm
  8. Build cloud mapping (P3) — JKA-order algorithm
  9. Build JKA, JKC
  10. Compute P1 counts
  11. Build NTC, MST
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .constants import LINK_A_FC_MAP, MAX_NRT, READ_FCS, WRITE_FCS
from .models import (
    CloudGroup,
    Device,
    NvsSlot,
    Project,
    Register,
    Slave,
)


class GenerationError(Exception):
    """Raised when the generation pipeline encounters an unrecoverable error."""


def generate(project: Project) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the full generation pipeline.

    Returns (modbus_config, parammap_config) as JSON-serialisable dicts.
    """
    ctx = _GenerationContext(project)
    ctx.run()
    return ctx.modbus_config, ctx.parammap_config


class _GenerationContext:
    """Mutable state for a single generation run."""

    def __init__(self, project: Project) -> None:
        self.project = project

        # Ordered slaves (device order → slave order)
        self.ordered_slaves: list[Slave] = []
        # slave modbus_id → index in ordered_slaves
        self.slave_index: dict[int, int] = {}

        # Flat sorted register list (determines B5 param IDs)
        self.sorted_regs: list[Register] = []

        # B4 packet arrays
        self.b4_sa: list[int] = []
        self.b4_nrt: list[int] = []
        self.b4_fc: list[int] = []
        self.b4_sid: list[int] = []

        # B3 arrays
        self.b3_si: list[int] = []
        self.b3_sp: list[int] = []

        # B5 arrays
        self.b5_id: list[int] = []
        self.b5_pn: list[int] = []
        self.b5_sta: list[int] = []
        self.b5_ln: list[int] = []
        self.b5_fmt: list[int] = []
        self.b5_mlt: list[float] = []

        # B6 arrays
        self.b6_wp: list[int] = []
        self.b6_rp: list[int] = []

        # P2 arrays
        self.p2_lbi: list[int] = []
        self.p2_mpi: list[int] = []
        self.p2_rpci: list[int] = []

        # P3 arrays
        self.p3_mdi: list[int] = []
        self.p3_mpi: list[int] = []
        self.p3_lbi: list[int] = []

        # Final output
        self.modbus_config: dict[str, Any] = {}
        self.parammap_config: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._reset_computed_fields()
        self._step1_build_slave_ordering()
        self._step2_group_packets()
        self._step3_assign_param_ids()
        # step4 (B3) is done inside step2
        self._step5_compute_b1()
        self._step6_build_write_pairs()
        self._step7_build_p2()
        self._step8_build_p3()
        self._step9_build_jka_jkc()
        self._step10_compute_p1()
        self._step11_build_ntc_mst()
        self._assemble_output()

    # ------------------------------------------------------------------
    # Step 1 — Build slave ordering, flatten & sort registers
    # ------------------------------------------------------------------

    def _reset_computed_fields(self) -> None:
        for reg in self.project.all_registers():
            reg.reset_computed()
        for nvs in self.project.nvs_slots:
            nvs.reset_computed()

    def _step1_build_slave_ordering(self) -> None:
        self.ordered_slaves = self.project.all_slaves()
        self.slave_index = {
            s.modbus_id: i for i, s in enumerate(self.ordered_slaves)
        }

        # Build flat sorted register list
        all_regs: list[Register] = []
        for slave in self.ordered_slaves:
            all_regs.extend(slave.registers)

        def sort_key(r: Register) -> tuple[int, int, int, int]:
            slave_order = self.slave_index[r.slave_id]
            fc_category = 0 if r.fc in READ_FCS else 1
            return (slave_order, fc_category, r.fc, r.address)

        all_regs.sort(key=sort_key)
        self.sorted_regs = all_regs

    # ------------------------------------------------------------------
    # Step 2 — Packet Grouping (B4 generation) + B3
    # ------------------------------------------------------------------

    def _step2_group_packets(self) -> None:
        self.b3_si = [s.modbus_id for s in self.ordered_slaves]

        for s_idx, slave in enumerate(self.ordered_slaves):
            # Record start packet for this slave (1-based)
            self.b3_sp.append(len(self.b4_sa) + 1)

            # Get this slave's registers in sorted order
            slave_regs = [
                r for r in self.sorted_regs if r.slave_id == slave.modbus_id
            ]
            if not slave_regs:
                continue

            # Group by FC, preserving sort order (reads before writes)
            seen_fcs: list[int] = []
            for r in slave_regs:
                if r.fc not in seen_fcs:
                    seen_fcs.append(r.fc)

            for fc in seen_fcs:
                fc_regs = [r for r in slave_regs if r.fc == fc]

                if fc in WRITE_FCS:
                    # Each write register = 1 packet
                    for reg in fc_regs:
                        self.b4_sa.append(reg.address)
                        self.b4_nrt.append(1)
                        self.b4_fc.append(fc)
                        self.b4_sid.append(slave.modbus_id)
                else:
                    # Read FC: greedy packing
                    self._pack_read_packets(fc_regs, fc, slave.modbus_id)

    def _pack_read_packets(
        self, regs: list[Register], fc: int, slave_id: int
    ) -> None:
        pkt_sa = regs[0].address
        pkt_end = regs[0].address + regs[0].ln

        for reg in regs[1:]:
            candidate_end = reg.address + reg.ln
            span = candidate_end - pkt_sa
            if span <= MAX_NRT:
                pkt_end = candidate_end
            else:
                # Emit current packet
                self.b4_sa.append(pkt_sa)
                self.b4_nrt.append(pkt_end - pkt_sa)
                self.b4_fc.append(fc)
                self.b4_sid.append(slave_id)
                # Start new packet
                pkt_sa = reg.address
                pkt_end = reg.address + reg.ln

        # Emit final packet
        self.b4_sa.append(pkt_sa)
        self.b4_nrt.append(pkt_end - pkt_sa)
        self.b4_fc.append(fc)
        self.b4_sid.append(slave_id)

    # ------------------------------------------------------------------
    # Step 3 — Assign param IDs (B5)
    # ------------------------------------------------------------------

    def _step3_assign_param_ids(self) -> None:
        for i, reg in enumerate(self.sorted_regs):
            pid = i + 1  # 1-based
            reg.param_id = pid

            pkt_num = self._find_packet(reg)
            reg.packet_number = pkt_num

            self.b5_id.append(pid)
            self.b5_pn.append(pkt_num)
            self.b5_sta.append(reg.address)
            self.b5_ln.append(reg.ln)
            self.b5_fmt.append(reg.fmt)
            self.b5_mlt.append(reg.mlt)

    def _find_packet(self, reg: Register) -> int:
        """Find the 1-based B4 packet containing this register."""
        for p in range(len(self.b4_sa)):
            if (
                self.b4_sid[p] == reg.slave_id
                and self.b4_fc[p] == reg.fc
                and reg.address >= self.b4_sa[p]
                and reg.address + reg.ln <= self.b4_sa[p] + self.b4_nrt[p]
            ):
                return p + 1
        raise GenerationError(
            f"No packet found for register '{reg.name}' "
            f"(slave={reg.slave_id}, FC={reg.fc}, addr={reg.address})"
        )

    # ------------------------------------------------------------------
    # Step 5 — Compute B1 counts
    # ------------------------------------------------------------------

    def _step5_compute_b1(self) -> None:
        # Stored directly in output assembly
        pass  # counts computed in _assemble_output

    # ------------------------------------------------------------------
    # Step 6 — Write pair generation (B6)
    # ------------------------------------------------------------------

    def _step6_build_write_pairs(self) -> None:
        write_regs = sorted(
            (r for r in self.sorted_regs if r.is_write),
            key=lambda r: r.param_id,
        )

        for wreg in write_regs:
            self.b6_wp.append(wreg.param_id)

            # Find Link A: read register at same address, same slave, complementary FC
            target_fc = LINK_A_FC_MAP.get(wreg.fc)
            link_a = None
            if target_fc is not None:
                link_a = self._find_register(
                    wreg.slave_id, wreg.address, target_fc
                )

            if link_a is not None:
                self.b6_rp.append(link_a.param_id)
            else:
                self.b6_rp.append(wreg.param_id)  # self-reference

    def _find_register(
        self, slave_id: int, address: int, fc: int
    ) -> Register | None:
        """Find a register by slave, address, and FC."""
        for r in self.sorted_regs:
            if r.slave_id == slave_id and r.address == address and r.fc == fc:
                return r
        return None

    # ------------------------------------------------------------------
    # Step 7 — P2 LBI Slot Assignment (3-Phase Algorithm)
    # ------------------------------------------------------------------

    def _step7_build_p2(self) -> None:
        lbi_counter = 1

        for device in self.project.devices:
            # === PHASE 1: Write registers + Link B feedbacks ===
            device_write_regs = []
            for slave in device.slaves:
                device_write_regs.extend(
                    r for r in slave.registers if r.is_write
                )
            device_write_regs.sort(key=lambda r: r.param_id)

            for wreg in device_write_regs:
                wreg.lbi_slot = lbi_counter
                self.p2_mpi.append(wreg.param_id)
                lbi_counter += 1

                if wreg.link_b_register is not None:
                    fb_reg = wreg.link_b_register
                    fb_reg.lbi_slot = lbi_counter
                    fb_reg.needs_lbi_slot = True
                    self.p2_mpi.append(fb_reg.param_id)
                    lbi_counter += 1

            # === PHASE 2: Engineer-marked read registers needing LBI ===
            device_read_regs = []
            for slave in device.slaves:
                device_read_regs.extend(
                    r
                    for r in slave.registers
                    if r.is_read and r.needs_lbi_slot and r.lbi_slot == 0
                )
            device_read_regs.sort(key=lambda r: r.param_id)

            for rreg in device_read_regs:
                rreg.lbi_slot = lbi_counter
                self.p2_mpi.append(rreg.param_id)
                lbi_counter += 1

        # === PHASE 3: NVS/RPCI slots ===
        rpci_counter = 1
        for nvs in self.project.nvs_slots:
            nvs.rpci_index = rpci_counter
            nvs.lbi_slot = lbi_counter
            self.p2_rpci.append(rpci_counter)
            lbi_counter += 1
            rpci_counter += 1

        # Assembly
        nlb = lbi_counter - 1
        self.p2_lbi = list(range(1, nlb + 1))

    # ------------------------------------------------------------------
    # Step 8 — P3 Cloud Mapping (JKA-order algorithm)
    # ------------------------------------------------------------------

    def _step8_build_p3(self) -> None:
        for group in self.project.cloud_groups:
            if group.source_type == "modbus":
                for reg in group.registers:
                    if reg is None:
                        raise GenerationError(
                            f"Cloud group '{group.cluster_name}' has unassigned Modbus register slot(s). "
                            "Assign a register to every slot or reduce the Keys × Equipment Names count."
                        )
                    self.p3_mpi.append(reg.param_id)
            elif group.source_type == "nvs":
                for nvs in group.nvs_slots:
                    if nvs is None:
                        raise GenerationError(
                            f"Cloud group '{group.cluster_name}' has unassigned NVS slot(s). "
                            "Assign an NVS slot to every position or reduce the Keys × Equipment Names count."
                        )
                    self.p3_lbi.append(nvs.lbi_slot)

        nmd = len(self.p3_mpi) + len(self.p3_lbi)
        self.p3_mdi = list(range(1, nmd + 1))

    # ------------------------------------------------------------------
    # Step 9 — JKA/JKC generation
    # ------------------------------------------------------------------

    def _step9_build_jka_jkc(self) -> None:
        # Built inline during assembly
        pass

    # ------------------------------------------------------------------
    # Step 10 — P1 counts
    # ------------------------------------------------------------------

    def _step10_compute_p1(self) -> None:
        # Built inline during assembly
        pass

    # ------------------------------------------------------------------
    # Step 11 — NTC/MST
    # ------------------------------------------------------------------

    def _step11_build_ntc_mst(self) -> None:
        # Built inline during assembly
        pass

    # ------------------------------------------------------------------
    # Final assembly
    # ------------------------------------------------------------------

    def _assemble_output(self) -> None:
        # --- Modbus_Config.json ---
        self.modbus_config = OrderedDict([
            ("B1", OrderedDict([
                ("NOS", len(self.b3_si)),
                ("NOP", len(self.b5_id)),
                ("NPT", len(self.b4_sa)),
                ("NOR", sum(self.b4_nrt)),
            ])),
            ("B2", OrderedDict([
                ("BR", self.project.baud_rate),
                ("DF", self.project.data_format),
            ])),
            ("B3", OrderedDict([
                ("SI", self.b3_si),
                ("SP", self.b3_sp),
            ])),
            ("B4", OrderedDict([
                ("SA", self.b4_sa),
                ("NRT", self.b4_nrt),
                ("FC", self.b4_fc),
                ("SID", self.b4_sid),
            ])),
            ("B5", OrderedDict([
                ("ID", self.b5_id),
                ("PN", self.b5_pn),
                ("STA", self.b5_sta),
                ("LN", self.b5_ln),
                ("FMT", self.b5_fmt),
                ("MLT", self.b5_mlt),
            ])),
            ("B6", OrderedDict([
                ("WP", self.b6_wp),
                ("RP", self.b6_rp),
            ])),
        ])

        # --- ParamMap_Config.json ---
        nlb = len(self.p2_mpi) + len(self.p2_rpci)
        nmd = len(self.p3_mpi) + len(self.p3_lbi)

        # JKA
        jka = []
        for group in self.project.cloud_groups:
            jka.append([group.cluster_name, group.keys, group.equipment_names])

        # NTC
        net = self.project.network
        if net is None:
            ntc = OrderedDict([
                ("IP", ""), ("PT", ""), ("CI", ""),
                ("SN", []), ("MI", []), ("MT", []), ("DI", ""),
            ])
        else:
            ntc = OrderedDict([
                ("IP", net.ip),
                ("PT", net.port),
                ("CI", net.client_id),
                ("SN", net.slave_numbers),
                ("MI", net.machine_ids),
                ("MT", net.machine_types),
                ("DI", net.device_id),
            ])

        self.parammap_config = OrderedDict([
            ("P1", OrderedDict([
                ("NLB", nlb),
                ("NLBIN", nlb),
                ("NMD", nmd),
            ])),
            ("P2", OrderedDict([
                ("LBI", self.p2_lbi),
                ("MPI", self.p2_mpi),
                ("RPCI", self.p2_rpci),
            ])),
            ("P3", OrderedDict([
                ("MDI", self.p3_mdi),
                ("MPI", self.p3_mpi),
                ("LBI", self.p3_lbi),
            ])),
            ("JKY", OrderedDict([
                ("JKA", jka),
            ])),
            ("JKC", OrderedDict([
                ("JKH", "properties"),
                ("EKS", "DKEY"),
            ])),
            ("NTC", ntc),
            ("MST", OrderedDict([
                ("PRF", self.project.profile),
            ])),
        ])

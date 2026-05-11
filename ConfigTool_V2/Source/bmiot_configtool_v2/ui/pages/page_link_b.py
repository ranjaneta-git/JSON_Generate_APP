"""Page 4 — Link B Assignment.

Each write register can have an optional 'Link B' feedback register.
When the firmware writes to FC5/FC6, it waits for the Link B read to confirm
the hardware responded. Link B can be on a different slave within the same device.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QAbstractItemView, QHeaderView,
)

from .base_page import BasePage
from ...engine.constants import FC_NAMES


class LinkBPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 4: Link B (Write Feedback)",
            "When the gateway writes a value (e.g., start a compressor), it can read back a status "
            "register to confirm the device actually responded. This is optional but recommended.",
        )
        self._updating = False
        self._write_regs = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        # Empty state (no writes)
        self.no_writes_msg = self._make_info_box(
            "No write registers found (FC5 or FC6).\n\n"
            "This step is only needed if you have write commands. "
            "If all your registers are read-only (FC1/FC2/FC3/FC4), you can skip this step."
        )
        layout.addWidget(self.no_writes_msg)

        layout.addWidget(self._make_info_box(
            "For each write register below, optionally choose a read register that the firmware "
            "will check after writing. Example: after writing a 'Start' command (FC6), "
            "read back 'Run_Status' (FC3) to confirm the motor started."
        ))

        grp = QGroupBox("Write Registers → Feedback Read Register")
        grp_layout = QVBoxLayout(grp)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Write Register", "Slave", "Address", "Link B Feedback Register"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        grp_layout.addWidget(self.table)

        layout.addWidget(grp)

        # Next step
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: LBI Slots  →", 4))
        layout.addLayout(bottom)

    def refresh(self):
        self._updating = True
        self.table.setRowCount(0)
        self._write_regs = []

        has_writes = any(
            r.fc in (5, 6)
            for r in self.project.all_registers()
        )
        self.no_writes_msg.setVisible(not has_writes)

        for dev in self.project.devices:
            # Collect all read regs in this device
            dev_read_regs = [
                r for sl in dev.slaves for r in sl.registers if r.fc in (1, 2, 3, 4)
            ]

            for sl in dev.slaves:
                for reg in sl.registers:
                    if reg.fc not in (5, 6):
                        continue

                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self._write_regs.append(reg)

                    self.table.setItem(row, 0, QTableWidgetItem(reg.name))
                    self.table.setItem(row, 1, QTableWidgetItem(str(sl.modbus_id)))
                    self.table.setItem(row, 2, QTableWidgetItem(str(reg.address)))

                    combo = QComboBox()
                    combo.addItem("— None (no feedback) —", None)
                    for rr in dev_read_regs:
                        lbl = f"{rr.name}  [S{rr.slave_id} FC{rr.fc} @{rr.address}]"
                        combo.addItem(lbl, rr)

                    # Set current selection
                    if reg.link_b_register is not None:
                        for i in range(combo.count()):
                            if combo.itemData(i) is reg.link_b_register:
                                combo.setCurrentIndex(i)
                                break

                    combo.currentIndexChanged.connect(
                        lambda _, r=reg, cb=combo: self._on_link_b_changed(r, cb)
                    )
                    self.table.setCellWidget(row, 3, combo)

        self._updating = False

    def _on_link_b_changed(self, reg, combo: QComboBox):
        if self._updating:
            return
        reg.link_b_register = combo.currentData()
        self.mark_changed()

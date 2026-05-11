"""Page 5 — LBI Slot Marking.

The user marks which read registers Lua needs runtime access to (LBI slots).
Write registers and their Link B feedback registers are always auto-assigned LBI slots
and cannot be unchecked.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QGroupBox, QHeaderView, QAbstractItemView, QCheckBox,
    QHBoxLayout,
)
from PySide6.QtCore import Qt

from .base_page import BasePage


class LbiPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 5: LBI Slots (Lua Access)",
            "The Lua control script on the gateway can only access registers that have LBI slots. "
            "Write registers are automatically included. Check any additional read registers that "
            "your Lua script needs to monitor.",
        )
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        # Summary
        self.summary_label = QLabel()
        self.summary_label.setObjectName("page_subtitle")
        layout.addWidget(self.summary_label)

        grp = QGroupBox("Register LBI Slot Assignment")
        grp_layout = QVBoxLayout(grp)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Register Name", "Device", "Slave", "Address", "FC", "Needs LBI Slot"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        grp_layout.addWidget(self.table)

        layout.addWidget(grp)

        layout.addWidget(self._make_info_box(
            "• Rows marked 'Write (auto)' and 'Link B (auto)' are always included — you cannot uncheck them.\n"
            "• Check additional read registers if your Lua control script needs to read them.\n"
            "• Unchecked read registers can still appear in cloud telemetry (Step 6).\n"
            "• If you don't use Lua scripting, you can leave all read registers unchecked."
        ))

        # Next step
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: Cloud Groups (Telemetry)  →", 5))
        layout.addLayout(bottom)

    def refresh(self):
        self._updating = True
        self.table.setRowCount(0)

        # Collect all Link B feedback registers (auto-LBI)
        link_b_regs = set()
        for reg in self.project.all_registers():
            if reg.link_b_register is not None:
                link_b_regs.add(id(reg.link_b_register))

        row = 0
        for dev in self.project.devices:
            for sl in dev.slaves:
                for reg in sl.registers:
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(reg.name))
                    self.table.setItem(row, 1, QTableWidgetItem(dev.name))
                    self.table.setItem(row, 2, QTableWidgetItem(str(sl.modbus_id)))
                    self.table.setItem(row, 3, QTableWidgetItem(str(reg.address)))
                    self.table.setItem(row, 4, QTableWidgetItem(f"FC{reg.fc}"))

                    # Determine if auto or user-controlled
                    is_write = reg.fc in (5, 6)
                    is_link_b = id(reg) in link_b_regs
                    auto = is_write or is_link_b

                    cb = QCheckBox()
                    cb.setChecked(auto or reg.needs_lbi_slot)
                    cb.setEnabled(not auto)

                    if auto:
                        reason = "Write (auto)" if is_write else "Link B (auto)"
                        cb.setToolTip(reason)

                    cb.stateChanged.connect(
                        lambda state, r=reg: self._on_check_changed(r, state)
                    )

                    container = QHBoxLayout()
                    container.addWidget(cb)
                    container.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    container.setContentsMargins(0, 0, 0, 0)
                    from PySide6.QtWidgets import QWidget
                    w = QWidget()
                    w.setLayout(container)
                    self.table.setCellWidget(row, 5, w)
                    row += 1

        self._updating = False
        self._update_summary()

    def _on_check_changed(self, reg, state):
        if self._updating:
            return
        reg.needs_lbi_slot = (state == Qt.CheckState.Checked.value)
        self._update_summary()
        self.mark_changed()

    def _update_summary(self):
        link_b_regs = set()
        for reg in self.project.all_registers():
            if reg.link_b_register is not None:
                link_b_regs.add(id(reg.link_b_register))

        write_count = sum(1 for r in self.project.all_registers() if r.fc in (5, 6))
        link_b_count = len(link_b_regs)
        manual_count = sum(
            1 for r in self.project.all_registers()
            if r.fc not in (5, 6) and id(r) not in link_b_regs and r.needs_lbi_slot
        )
        total = write_count + link_b_count + manual_count
        nvs_count = len(self.project.nvs_slots)
        nlb = total + nvs_count
        self.summary_label.setText(
            f"Modbus LBI slots: {write_count} write  +  {link_b_count} Link-B  +  "
            f"{manual_count} manual  =  {total}   |   NVS LBI slots: {nvs_count}   |   "
            f"Total NLB = {nlb}"
        )

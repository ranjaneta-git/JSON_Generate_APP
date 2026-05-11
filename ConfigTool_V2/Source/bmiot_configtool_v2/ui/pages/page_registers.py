"""Page 3 — Register Entry."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QComboBox, QLabel, QGroupBox,
    QMessageBox, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt

from .base_page import BasePage
from ...engine.constants import FC_NAMES, FMT_TABLE
from ...engine.models import Register

FC_ITEMS = [(fc, f"FC{fc}: {name}") for fc, name in FC_NAMES.items()]
FMT_ITEMS = [(fid, f"FMT{fid}: {desc}") for fid, (desc, _) in FMT_TABLE.items()]

COL_NAME = 0
COL_ADDR = 1
COL_FC   = 2
COL_FMT  = 3
COL_MLT  = 4
NUM_COLS = 5


class RegistersPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 3: Registers",
            "Define the Modbus registers for each slave device. "
            "These are the data points the gateway will read from or write to your equipment.",
        )
        self._updating = False
        self._current_slave = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        # Prerequisite hint (shown when no slaves)
        self.no_slave_hint = self._make_workflow_hint(
            "You need to add at least one Device with a Slave in Step 2 before adding registers.\n"
            "Go to Step 2 → Add Device → Add Slave, then come back here."
        )
        layout.addWidget(self.no_slave_hint)

        # Slave selector
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Select which slave to edit:"))
        self.slave_combo = QComboBox()
        self.slave_combo.setMinimumWidth(300)
        self.slave_combo.setToolTip("Choose a slave to add/edit its registers")
        self.slave_combo.currentIndexChanged.connect(self._on_slave_selected)
        sel_row.addWidget(self.slave_combo)
        sel_row.addStretch()
        self.sel_widget = QLabel()  # container placeholder
        layout.addLayout(sel_row)

        # Register info box
        layout.addWidget(self._make_info_box(
            "Each row is a Modbus register.  Fill in:\n"
            "  • Name — a descriptive label (e.g., Run_Status, Freq_Cmd, Temp_Supply)\n"
            "  • Address — the Modbus register address from the device manual (e.g., 0, 100, 8192)\n"
            "  • FC — Function Code: FC3 (Read Holding) is most common; FC6 (Write Register) for commands\n"
            "  • FMT — Data format: FMT3 (UINT16) is most common; FMT1 (Float32) for temperatures\n"
            "  • Multiplier — scaling factor (1.0 = no scaling; 0.1 = divide by 10)"
        ))

        grp = QGroupBox("Registers for Selected Slave")
        grp_layout = QVBoxLayout(grp)

        self.table = QTableWidget(0, NUM_COLS)
        self.table.setHorizontalHeaderLabels([
            "Register Name", "Address", "Function Code", "Data Format", "Multiplier"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_ADDR, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_FC,   QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(COL_FMT,  QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(COL_MLT,  QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(COL_FMT, 220)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._on_item_changed)
        grp_layout.addWidget(self.table)

        # Empty state for table
        self.table_empty = QLabel(
            "No registers yet for this slave.\n\n"
            "Click '+ Add Register' below to add your first register.\n"
            "You'll need the register address and function code from the device manual."
        )
        self.table_empty.setObjectName("empty_state")
        self.table_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_empty.setWordWrap(True)
        grp_layout.addWidget(self.table_empty)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Register")
        add_btn.setObjectName("btn_primary")
        add_btn.setToolTip("Add a new Modbus register to this slave")
        add_btn.clicked.connect(self._add_row)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        grp_layout.addLayout(btn_row)

        layout.addWidget(grp)

        # Next step
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: Link B Feedback  →", 3))
        layout.addLayout(bottom)

    # ------------------------------------------------------------------

    def refresh(self):
        self._updating = True
        prev_text = self.slave_combo.currentText()
        self.slave_combo.clear()
        items = self.project.slave_display_items()

        has_slaves = bool(items)
        self.no_slave_hint.setVisible(not has_slaves)
        self.slave_combo.setVisible(has_slaves)

        for label, sl in items:
            self.slave_combo.addItem(label, sl)
        idx = self.slave_combo.findText(prev_text)
        if idx >= 0:
            self.slave_combo.setCurrentIndex(idx)
        elif self.slave_combo.count() > 0:
            self.slave_combo.setCurrentIndex(0)
        self._updating = False
        self._load_table()

    def _on_slave_selected(self):
        if not self._updating:
            self._load_table()

    def _load_table(self):
        self._current_slave = self.slave_combo.currentData()
        self._updating = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        if self._current_slave:
            for reg in self._current_slave.registers:
                self._append_row(reg)
        has_regs = self._current_slave and bool(self._current_slave.registers)
        self.table.setVisible(bool(has_regs))
        self.table_empty.setVisible(not has_regs)
        self.table.blockSignals(False)
        self._updating = False

    def _append_row(self, reg: Register | None = None):
        sl = self._current_slave
        if sl is None:
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        name = reg.name if reg else f"Reg_{row + 1}"
        addr = reg.address if reg else 0
        fc   = reg.fc if reg else 3
        fmt  = reg.fmt if reg else 3
        mlt  = reg.mlt if reg else 1.0

        name_item = QTableWidgetItem(name)
        name_item.setToolTip("Descriptive name (e.g., Run_Status, Freq_Cmd)")
        self.table.setItem(row, COL_NAME, name_item)

        addr_item = QTableWidgetItem(str(addr))
        addr_item.setToolTip("Modbus register address (from device manual)")
        self.table.setItem(row, COL_ADDR, addr_item)

        fc_combo = QComboBox()
        for fc_id, fc_label in FC_ITEMS:
            fc_combo.addItem(fc_label, fc_id)
        fc_combo.setCurrentIndex(next(
            (i for i, (fid, _) in enumerate(FC_ITEMS) if fid == fc), 2))
        fc_combo.setToolTip("FC3=Read Holding (most common)  FC6=Write Register")
        fc_combo.currentIndexChanged.connect(lambda _, r=row: self._on_combo_changed(r))
        self.table.setCellWidget(row, COL_FC, fc_combo)

        fmt_combo = QComboBox()
        for fmt_id, fmt_label in FMT_ITEMS:
            fmt_combo.addItem(fmt_label, fmt_id)
        fmt_combo.setCurrentIndex(next(
            (i for i, (fid, _) in enumerate(FMT_ITEMS) if fid == fmt), 2))
        fmt_combo.setToolTip("FMT3=UINT16 (most common)  FMT1=Float32 (for temperatures)")
        fmt_combo.currentIndexChanged.connect(lambda _, r=row: self._on_combo_changed(r))
        self.table.setCellWidget(row, COL_FMT, fmt_combo)

        mlt_item = QTableWidgetItem(str(mlt))
        mlt_item.setToolTip("Scaling factor. 1.0 = raw value, 0.1 = divide by 10")
        self.table.setItem(row, COL_MLT, mlt_item)

    def _add_row(self):
        sl = self._current_slave
        if sl is None:
            QMessageBox.information(self, "No Slave Selected",
                "Please add a Device and Slave in Step 2 first, "
                "then select it from the dropdown above.")
            return
        existing = [r.address for r in sl.registers]
        new_addr = (max(existing) + 1) if existing else 0
        reg = Register(name=f"Reg_{len(sl.registers) + 1}",
                       address=new_addr, fc=3, fmt=3, mlt=1.0,
                       slave_id=sl.modbus_id)
        sl.registers.append(reg)
        self._load_table()
        self.mark_changed()

    def _delete_selected(self):
        sl = self._current_slave
        if sl is None:
            return
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return

        # Confirmation dialog
        count = len(rows)
        if QMessageBox.question(
            self, "Delete Registers",
            f"Delete {count} selected register(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        # Collect doomed registers for reference cleanup
        doomed_regs: set[int] = set()
        for row in rows:
            if 0 <= row < len(sl.registers):
                doomed_regs.add(id(sl.registers[row]))

        # Clean up Link B references pointing to deleted registers
        for reg in self.project.all_registers():
            if reg.link_b_register is not None and id(reg.link_b_register) in doomed_regs:
                reg.link_b_register = None

        # Clean up Cloud Group register assignments
        for cg in self.project.cloud_groups:
            if cg.source_type == "modbus":
                cg.registers = [
                    (None if r is not None and id(r) in doomed_regs else r)
                    for r in cg.registers
                ]

        # Actually delete
        for row in rows:
            if 0 <= row < len(sl.registers):
                sl.registers.pop(row)
        self._load_table()
        self.mark_changed()

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._updating:
            return
        sl = self._current_slave
        if sl is None:
            return
        row = item.row()
        if row < 0 or row >= len(sl.registers):
            return
        reg = sl.registers[row]
        col = item.column()
        if col == COL_NAME:
            reg.name = item.text().strip() or reg.name
        elif col == COL_ADDR:
            try:
                reg.address = int(item.text(), 0)
            except ValueError:
                pass
        elif col == COL_MLT:
            try:
                v = float(item.text())
                if v > 0:
                    reg.mlt = v
            except ValueError:
                pass
        self.mark_changed()

    def _on_combo_changed(self, row: int):
        if self._updating:
            return
        sl = self._current_slave
        if sl is None or row >= len(sl.registers):
            return
        reg = sl.registers[row]
        fc_w = self.table.cellWidget(row, COL_FC)
        fmt_w = self.table.cellWidget(row, COL_FMT)
        if fc_w:
            reg.fc = fc_w.currentData()
        if fmt_w:
            reg.fmt = fmt_w.currentData()
        self.mark_changed()

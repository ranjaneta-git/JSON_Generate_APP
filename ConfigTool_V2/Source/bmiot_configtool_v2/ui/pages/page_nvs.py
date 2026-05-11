"""Page 7 — NVS Configuration."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QGroupBox, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt

from .base_page import BasePage
from ...engine.constants import MAX_NVS_KEY_LEN
from ...engine.models import NvsSlot


class NvsPage(BasePage):
    def __init__(self, main_window):
        super().__init__(
            main_window,
            "Step 7: NVS Setpoints (Optional)",
            "NVS slots let the cloud push persistent setpoint values to the gateway "
            "(e.g., target temperature, timer duration). These survive device reboots.",
        )
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        for w in self._make_header():
            layout.addWidget(w)

        grp = QGroupBox("NVS Slots")
        grp_layout = QVBoxLayout(grp)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["#", f"NVS Key Name  (max {MAX_NVS_KEY_LEN} chars)"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(self._on_item_changed)
        grp_layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add NVS Slot")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._add_slot)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("btn_danger")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        grp_layout.addLayout(btn_row)

        layout.addWidget(grp)

        layout.addWidget(self._make_info_box(
            "This step is optional. Only add NVS slots if your system needs cloud-writable setpoints.\n\n"
            "Examples of NVS keys: Temp_SP, Timer_Dur, Mode_Sel\n"
            f"Key names must be unique and ≤ {MAX_NVS_KEY_LEN} characters."
        ))

        # Next step
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(self._make_next_button("Next: Network / MQTT  →", 7))
        layout.addLayout(bottom)

    def refresh(self):
        self._updating = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for i, nvs in enumerate(self.project.nvs_slots):
            self._append_row(i + 1, nvs.key_name)
        self.table.blockSignals(False)
        self._updating = False

    def _append_row(self, num: int, key_name: str):
        row = self.table.rowCount()
        self.table.insertRow(row)

        num_item = QTableWidgetItem(str(num))
        num_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.table.setItem(row, 0, num_item)

        key_item = QTableWidgetItem(key_name)
        self.table.setItem(row, 1, key_item)

    def _add_slot(self):
        nvs = NvsSlot(key_name=f"nvs_key_{len(self.project.nvs_slots) + 1}")
        self.project.nvs_slots.append(nvs)
        self._append_row(len(self.project.nvs_slots), nvs.key_name)
        self.mark_changed()

    def _delete_selected(self):
        rows = sorted(
            {idx.row() for idx in self.table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            if 0 <= row < len(self.project.nvs_slots):
                self.project.nvs_slots.pop(row)
        self.refresh()
        self.mark_changed()

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._updating:
            return
        row = item.row()
        if item.column() != 1 or row >= len(self.project.nvs_slots):
            return
        key = item.text().strip()
        if len(key) > MAX_NVS_KEY_LEN:
            item.setBackground(Qt.GlobalColor.red)
            item.setToolTip(f"Key too long (max {MAX_NVS_KEY_LEN} chars)")
        else:
            item.setBackground(Qt.GlobalColor.white)
            item.setToolTip("")
            self.project.nvs_slots[row].key_name = key
        self.mark_changed()
